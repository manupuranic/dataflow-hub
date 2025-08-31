import psycopg2
from psycopg2.extras import DictCursor

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine.url import URL
from sqlalchemy import or_, and_
from db.model import *

class DB:
    def __init__(self, env):
        self.user = env.get('user')
        self.password = env.get('password')
        self.host = env.get('host')
        self.port = env.get('port')
        self.dbname = env.get('dbname')

        self.url = URL.create(
            drivername="postgresql+psycopg2",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.dbname,
        )

        self.engine = create_engine(self.url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Keep one session per instance (optional singleton)
        self._session = self.SessionLocal()

    def getConn(self):
        try:
            conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                cursor_factory=DictCursor
            )
            return conn
        except Exception as e:
            print(f"[DB ERROR] Connection failed: {e}")
            raise

    def getModels(self, modelname: str = None):
        if not modelname:
            raise ValueError("Model name must be provided.")
        
        model_map = {
            'brands': Brand,
            'hsn_codes': HSNCode,
            'item_names': ItemName,
            'suppliers': Supplier,
            'products': Product,
            "invoices": Invoice,
            "invoice_items": InvoiceItem,
            "purchases": Purchase,
            "purchase_items": PurchaseItem,
            "product_suppliers": ProductSupplier,
            'customers': Customer,
            'product_lookup_view': ProductLookupView,
        }

        model = model_map.get(modelname)
        if not model:
            raise ValueError(f"Model '{modelname}' not found.")
        
        return model
    
    def apply_query_filters(self, queryset, model, query: dict):
        operator_map = {
            "eq": lambda col, val: col == val,
            "ne": lambda col, val: col != val,
            "lt": lambda col, val: col < val,
            "lte": lambda col, val: col <= val,
            "gt": lambda col, val: col > val,
            "gte": lambda col, val: col >= val,
            "like": lambda col, val: col.like(val),
            "ilike": lambda col, val: col.ilike(val),
            "in": lambda col, val: col.in_(val if isinstance(val, list) else [val]),
        }

        filters = query.get("filters", [])
        condition_type = query.get("condition", "and").lower()
        limit = query.get("limit")

        conditions = []

        for f in filters:
            field = f.get("field")
            op = f.get("operator", "eq")
            val = f.get("value")

            if not hasattr(model, field):
                raise ValueError(f"'{field}' is not a valid column in model '{model.__name__}'")

            column = getattr(model, field)

            if op not in operator_map:
                raise ValueError(f"Unsupported operator '{op}'")

            conditions.append(operator_map[op](column, val))

        if conditions:
            queryset = queryset.filter(or_(*conditions) if condition_type == "or" else and_(*conditions))

        # Apply sorting
        sort = query.get("sort", {})
        if isinstance(sort, dict):
            for field, direction in sort.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid sort field '{field}' for model '{model.__name__}'")
                col = getattr(model, field)
                queryset = queryset.order_by(col.desc() if direction == -1 else col.asc())

        if limit:
            queryset = queryset.limit(limit)

        return queryset


    def listOne(self, modelname: str, query: dict, includes: list = None):
        try:
            model = self.getModels(modelname)
            q = self._session.query(model)

            # Dynamically include relationships
            if includes:
                for rel in includes:
                    q = q.options(joinedload(getattr(model, rel)))

            q = self.apply_query_filters(q, model, query)
            return q.first()
        except Exception as e:
            self._session.rollback()
            print(f"[DB ERROR] listOne failed for model '{modelname}': {e}")
            raise

    def listRecords(self, modelname: str, query: dict, includes: list = None):
        try:
            model = self.getModels(modelname)
            q = self._session.query(model)
            
            # Dynamically include relationships
            if includes:
                for rel in includes:
                    q = q.options(joinedload(getattr(model, rel)))
            
            q = self.apply_query_filters(q, model, query)
            return q.all()
        except Exception as e:
            self._session.rollback()
            print(f"[DB ERROR] listRecords failed for model '{modelname}': {e}")
            raise

    def upsertRecord(self, modelname: str, data: dict, conflict_columns: list, update_columns: list = None):
        model = self.getModels(modelname)
        stmt = insert(model).values(**data)

        if update_columns is None:
            update_columns = [col for col in data.keys() if col not in conflict_columns]

        update_dict = {col: getattr(stmt.excluded, col) for col in update_columns}

        if update_dict:
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_=update_dict
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict_columns)

        try:
            self._session.execute(stmt)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            print(f"[DB ERROR] Upsert failed: {e}")
            raise
    
    def bulkUpsertRecords(self, modelname: str, data_list: list[dict], conflict_columns: list, update_columns: list = None):
        if not data_list:
            return

        # Deduplicate rows based on conflict_columns
        def deduplicate_data(data_list, conflict_columns):
            seen = set()
            deduped = []
            for row in data_list:
                key = tuple(row.get(col) for col in conflict_columns)
                if key not in seen:
                    seen.add(key)
                    deduped.append(row)
            return deduped

        data_list = deduplicate_data(data_list, conflict_columns)

        model = self.getModels(modelname)

        if update_columns is None:
            update_columns = [col for col in data_list[0].keys() if col not in conflict_columns]

        stmt = insert(model).values(data_list)
        update_dict = {col: getattr(stmt.excluded, col) for col in update_columns}

        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_dict
        )

        try:
            self._session.execute(stmt)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            print(f"[DB ERROR] Bulk upsert failed: {e}")
            raise

    def updateRecord(self, modelname: str, data: dict, query: dict):
        model = self.getModels(modelname)
        q = self._session.query(model)
        q = self.apply_query_filters(q, model, query)
        updated_count = q.update(data, synchronize_session=False)
        self._session.commit()
        return updated_count
    
    def deleteRecord(self, modelname: str, query: dict):
        model = self.getModels(modelname)
        q = self._session.query(model)
        q = self.apply_query_filters(q, model, query)
        deleted_count = q.delete(synchronize_session=False)
        self._session.commit()
        return deleted_count