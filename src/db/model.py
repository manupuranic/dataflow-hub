from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Numeric, ForeignKey, UniqueConstraint, ARRAY, Date, text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

def default():
    return None  # placeholder for server-side defaults (handled by Supabase)

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    name = Column(Text)
    address = Column(Text)
    mobile = Column(Text, unique=True)
    company_name = Column(Text)
    gstin = Column(Text)
    email = Column(Text)
    loyalty_member = Column(Boolean, default=False)
    total_spent = Column(Numeric, default=0)
    total_visits = Column(Integer, default=0)
    first_purchase = Column(DateTime)
    last_purchase = Column(DateTime)
    ai_segment = Column(Text)
    preferred_products = Column(ARRAY(Text))
    notes = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    loyalty_points = Column(Numeric)


class Brand(Base):
    __tablename__ = 'brands'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    name = Column(Text, nullable=False, unique=True)
    
    products = relationship("Product", back_populates="brand", lazy="noload")

class HSNCode(Base):
    __tablename__ = 'hsn_codes'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    code = Column(Text, nullable=False, unique=True)
    description = Column(Text)

class ItemName(Base):
    __tablename__ = 'item_names'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    original_name = Column(Text, nullable=False, unique=True)
    corrected_name = Column(Text)
    created_at = Column(DateTime, server_default=text('now()')) 
    
    products = relationship("Product", back_populates="item_name", lazy="noload")

class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    name = Column(Text, nullable=False, unique=True)
    gstin = Column(Text)
    pan_no = Column(Text)
    state = Column(Text)
    country = Column(Text)
    address = Column(Text)
    mobile = Column(Text)
    email = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))
    
    purchases = relationship("Purchase", back_populates="supplier", lazy="noload")
    

class Product(Base):
    __tablename__ = 'products'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    item_name_id = Column(UUID(as_uuid=True), ForeignKey('item_names.id'))
    barcode = Column(Text)
    hsn_code = Column(Text)
    size = Column(Text)
    full_desc = Column(Text)
    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id'))
    expiry_date = Column(Date)
    gst_percent = Column(Numeric)
    cess_percent = Column(Numeric)
    purchase_price = Column(Numeric)
    mrp = Column(Numeric)
    rate = Column(Numeric)
    min_stock = Column(Integer)
    current_stock = Column(Numeric)
    images = Column(Text)
    category = Column(Text)
    ai_description = Column(Text)
    ai_tags = Column(ARRAY(Text))
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'))
    
    purchase_items = relationship("PurchaseItem", back_populates="product", cascade="all, delete-orphan", lazy="selectin")
    invoice_items = relationship("InvoiceItem", back_populates="product", cascade="all, delete-orphan", lazy="selectin")
    product_suppliers = relationship("ProductSupplier", backref="product", cascade="all, delete-orphan", lazy="selectin")

    brand = relationship("Brand", back_populates="products", lazy="joined")
    item_name = relationship("ItemName", back_populates="products", lazy="joined")
    
class ProductLookupView(Base):
    __tablename__ = 'product_lookup_view'
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    item_name_id = Column(UUID(as_uuid=True), ForeignKey('item_names.id'))
    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id'))
    barcode = Column(Text)
    mrp = Column(Numeric)
    expiry_date = Column(Date)

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    bill_no = Column(Text, unique=True, nullable=False)
    bill_type = Column(Text)
    sale_type = Column(Text)
    gst_type = Column(Text)
    sale_to = Column(Text)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    operator = Column(Text)
    invoice_date = Column(DateTime)
    
    qty = Column(Numeric)
    total_mrp = Column(Numeric)
    total_rate = Column(Numeric)
    cust_disc_percent = Column(Numeric)
    cust_discount = Column(Numeric)
    bill_disc_percent = Column(Numeric)
    bill_discount = Column(Numeric)
    extra_disc_percent = Column(Numeric)
    extra_discount = Column(Numeric)
    membercard_discount = Column(Numeric)
    total_discount = Column(Numeric)
    
    gst_0 = Column(Numeric)
    gst_3 = Column(Numeric)
    gst_5 = Column(Numeric)
    gst_12 = Column(Numeric)
    gst_18 = Column(Numeric)
    gst_28 = Column(Numeric)

    taxable_amount = Column(Numeric)
    taxable_amt_0 = Column(Numeric)
    taxable_amt_3 = Column(Numeric)
    taxable_amt_5 = Column(Numeric)
    taxable_amt_12 = Column(Numeric)
    taxable_amt_18 = Column(Numeric)
    taxable_amt_28 = Column(Numeric)

    igst_3 = Column(Numeric)
    igst_5 = Column(Numeric)
    igst_12 = Column(Numeric)
    igst_18 = Column(Numeric)
    igst_28 = Column(Numeric)

    cgst_1_5 = Column(Numeric)
    cgst_2_5 = Column(Numeric)
    cgst_6 = Column(Numeric)
    cgst_9 = Column(Numeric)
    cgst_14 = Column(Numeric)

    sgst_1_5 = Column(Numeric)
    sgst_2_5 = Column(Numeric)
    sgst_6 = Column(Numeric)
    sgst_9 = Column(Numeric)
    sgst_14 = Column(Numeric)

    total_igst = Column(Numeric)
    total_cgst = Column(Numeric)
    total_sgst = Column(Numeric)
    net_tax = Column(Numeric)
    gross_sale = Column(Numeric)
    round_off = Column(Numeric)
    net_total = Column(Numeric)

    other_charges = Column(Numeric)
    credit_amt = Column(Numeric)
    cn_adjust = Column(Numeric)
    cn_amount = Column(Numeric)

    payment_cash = Column(Numeric)
    payment_card = Column(Numeric)
    payment_google_pay = Column(Numeric)
    payment_phonepe = Column(Numeric)
    payment_paytm = Column(Numeric)
    actual_cash = Column(Numeric)
    cash_return = Column(Numeric)

    created_at = Column(DateTime)
    
    customer = relationship("Customer", backref="invoices", lazy="joined")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="noload")

class InvoiceItem(Base):
    __tablename__ = 'invoice_items'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    qty = Column(Integer)
    mrp = Column(Numeric)
    total_mrp = Column(Numeric)
    rate = Column(Numeric)
    total_rate = Column(Numeric)

    disc1_percent = Column(Numeric)
    disc1_amount = Column(Numeric)
    other_discount = Column(Numeric)
    total_discount = Column(Numeric)
    taxable_amount = Column(Numeric)

    igst_percent = Column(Numeric)
    igst_amount = Column(Numeric)
    cgst_percent = Column(Numeric)
    cgst_amount = Column(Numeric)
    sgst_percent = Column(Numeric)
    sgst_amount = Column(Numeric)
    cess_percent = Column(Numeric)
    cess_amount = Column(Numeric)

    gross_amount = Column(Numeric)
    round_off = Column(Numeric)
    net_total = Column(Numeric)

    current_stock = Column(Integer)
    operator = Column(Text)
    created_at = Column(DateTime)
    
    invoice = relationship("Invoice", back_populates="items", lazy="joined")
    product = relationship("Product", back_populates="invoice_items", lazy="joined")

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    invoice_no = Column(String, index=True)
    invoice_date = Column(Date, index=True)
    invoice_time = Column(Time)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), index=True)
    tax_type = Column(String)

    total_qty = Column(Integer)
    taxable_value = Column(Numeric(10, 2))
    gst_0 = Column(Numeric(10, 2))
    gst_3 = Column(Numeric(10, 2))
    gst_5 = Column(Numeric(10, 2))
    gst_12 = Column(Numeric(10, 2))
    gst_18 = Column(Numeric(10, 2))
    gst_28 = Column(Numeric(10, 2))
    total_tax = Column(Numeric(10, 2))
    round_off = Column(Numeric(10, 2))
    settled_amount = Column(Numeric(10, 2))
    due_amount = Column(Numeric(10, 2))

    created_at = Column(DateTime, server_default=text('now()'))

    supplier = relationship("Supplier", back_populates="purchases", lazy="joined")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan", lazy="noload")

class PurchaseItem(Base):
    __tablename__ = 'purchase_items'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    purchase_id = Column(UUID(as_uuid=True), ForeignKey('purchases.id'))
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    tax_type = Column(Text)
    qty = Column(Numeric)
    free_qty = Column(Numeric)
    purchase_price = Column(Numeric)
    mrp = Column(Numeric)
    gst_percent = Column(Integer)
    rate = Column(Numeric)
    profit_percent = Column(Numeric)
    taxable_value = Column(Numeric)
    total_amount = Column(Numeric)
    created_at = Column(DateTime, server_default=text('now()'))
    
    purchase = relationship("Purchase", back_populates="items", lazy="joined")
    product = relationship("Product", back_populates="purchase_items", lazy="joined")

class ProductSupplier(Base):
    __tablename__ = 'product_suppliers'
    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('gen_random_uuid()'))
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    preferred_supplier = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=text('now()'))
    
