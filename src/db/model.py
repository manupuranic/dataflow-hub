# models.py
from __future__ import annotations

from enum import Enum
from datetime import datetime

from sqlalchemy import (
    Column, Text, DateTime, Boolean, Integer, Numeric, ForeignKey, UniqueConstraint,
    Date, Time, CheckConstraint, PrimaryKeyConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# -------------------------
# PostgreSQL ENUMs
# -------------------------
class MovementType(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    RETURN_PURCHASE = "RETURN_PURCHASE"
    RETURN_SALE = "RETURN_SALE"
    ADJUST = "ADJUST"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    CONVERT_IN = "CONVERT_IN"
    CONVERT_OUT = "CONVERT_OUT"

class AllocationMethod(str, Enum):
    ITEM_MASTER_EXACT = "ITEM_MASTER_EXACT"
    PURCHASE_EXACT = "PURCHASE_EXACT"
    MRP_FEFO = "MRP_FEFO"
    FEFO = "FEFO"
    FIFO = "FIFO"
    NAME_FUZZY = "NAME_FUZZY"
    OPENING_BALANCE = "OPENING_BALANCE"
    MANUAL = "MANUAL"

class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    UPI = "UPI"
    PHONEPE = "PHONEPE"
    GPAY = "GPAY"
    PAYTM = "PAYTM"
    OTHER = "OTHER"

MovementTypeEnum = ENUM(MovementType, name="movement_type_enum", create_type=True)
AllocationMethodEnum = ENUM(AllocationMethod, name="allocation_method_enum", create_type=True)
PaymentMethodEnum = ENUM(PaymentMethod, name="payment_method_enum", create_type=True)

# Helper for UUID default
UUID_PK = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text("gen_random_uuid()"))


# -------------------------
# Lookups / Actors
# -------------------------
class Brand(Base):
    __tablename__ = "brands"
    id = UUID_PK
    name = Column(Text, nullable=False, unique=True)

    products = relationship("Product", back_populates="brand", lazy="noload")


class Category(Base):
    __tablename__ = "categories"
    id = UUID_PK
    name = Column(Text, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))

    parent = relationship("Category", remote_side=[id], backref="children", lazy="noload")


class Supplier(Base):
    __tablename__ = "suppliers"
    id = UUID_PK
    name = Column(Text, nullable=False, unique=True)
    gstin = Column(Text)
    pan_no = Column(Text)
    state = Column(Text)
    country = Column(Text)
    address = Column(Text)
    mobile = Column(Text)
    email = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    purchases = relationship("Purchase", back_populates="supplier", lazy="noload")


class User(Base):
    __tablename__ = "users"
    id = UUID_PK
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True)
    is_active = Column(Boolean, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    invoices = relationship("Invoice", back_populates="operator", lazy="noload")
    invoice_items = relationship("InvoiceItem", back_populates="operator", lazy="noload")
    conversions = relationship("Conversion", back_populates="operator", lazy="noload")


class Customer(Base):
    __tablename__ = "customers"
    id = UUID_PK
    name = Column(Text)
    address = Column(Text)
    mobile = Column(Text, unique=True)
    company_name = Column(Text)
    gstin = Column(Text)
    email = Column(Text)
    loyalty_member = Column(Boolean, server_default=text("false"))
    total_spent = Column(Numeric, server_default=text("0"))
    total_visits = Column(Integer, server_default=text("0"))
    first_purchase = Column(DateTime)  # no tz per your schema
    last_purchase = Column(DateTime)   # no tz per your schema
    ai_segment = Column(Text)
    preferred_products = Column(JSONB)  # use JSONB instead of untyped ARRAY for flexibility
    notes = Column(Text)
    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"))
    loyalty_points = Column(Numeric)

    invoices = relationship("Invoice", back_populates="customer", lazy="noload")


# -------------------------
# Product Master (SKU), Barcodes, Lots
# -------------------------
class Product(Base):
    __tablename__ = "products"
    id = UUID_PK
    name = Column(Text, nullable=False)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"))
    hsn_code = Column(Text)
    gst_percent = Column(Integer, nullable=False)
    cess_percent = Column(Integer, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    size = Column(Text)
    is_active = Column(Boolean, server_default=text("true"))
    ai = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))

    brand = relationship("Brand", back_populates="products", lazy="joined")
    category = relationship("Category", lazy="joined")

    barcodes = relationship("ProductBarcode", back_populates="sku", cascade="all, delete-orphan", lazy="selectin")
    lots = relationship("ProductLot", back_populates="sku", cascade="all, delete-orphan", lazy="noload")

    purchase_items = relationship("PurchaseItem", back_populates="sku", lazy="noload")
    invoice_items = relationship("InvoiceItem", back_populates="sku", lazy="noload")

    bom_as_finished = relationship("BomRecipe", foreign_keys="BomRecipe.finished_sku_id",
                                   back_populates="finished_sku", lazy="noload")
    bom_as_component = relationship("BomRecipe", foreign_keys="BomRecipe.component_sku_id",
                                    back_populates="component_sku", lazy="noload")


class ProductBarcode(Base):
    __tablename__ = "product_barcodes"
    barcode = Column(Text, primary_key=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    is_primary = Column(Boolean, server_default=text("false"))
    valid_from = Column(Date)
    valid_to = Column(Date)

    sku = relationship("Product", back_populates="barcodes", lazy="joined")

    __table_args__ = (Index("idx_product_barcodes_sku", "sku_id"),)


class ProductLot(Base):
    __tablename__ = "product_lots"
    id = UUID_PK
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_code = Column(Text)
    expiry_date = Column(Date)
    mfg_date = Column(Date)
    mrp = Column(Numeric)
    purchase_price = Column(Numeric)  # present in your posted schema
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    sku = relationship("Product", back_populates="lots", lazy="joined")


# -------------------------
# Purchases
# -------------------------
class Purchase(Base):
    __tablename__ = "purchases"
    id = UUID_PK
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, index=True)
    invoice_no = Column(Text)
    invoice_date = Column(Date, nullable=False, index=True)
    invoice_time = Column(Time)
    tax_type = Column(Text)
    total_qty = Column(Integer)
    taxable_value = Column(Numeric, nullable=False)
    gst_0 = Column(Numeric)
    gst_3 = Column(Numeric)
    gst_5 = Column(Numeric)
    gst_12 = Column(Numeric)
    gst_18 = Column(Numeric)
    gst_28 = Column(Numeric)
    total_tax = Column(Numeric)
    round_off = Column(Numeric)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    supplier = relationship("Supplier", back_populates="purchases", lazy="joined")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan", lazy="noload")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = UUID_PK
    purchase_id = Column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"))
    qty = Column(Numeric, nullable=False)
    free_qty = Column(Numeric, nullable=False, server_default=text("0"))
    unit_cost = Column(Numeric, nullable=False)
    mrp = Column(Numeric)
    gst_percent = Column(Integer, nullable=False)
    taxable_value = Column(Numeric)
    tax_amount = Column(Numeric)
    total_amount = Column(Numeric)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    purchase = relationship("Purchase", back_populates="items", lazy="joined")
    sku = relationship("Product", back_populates="purchase_items", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")

    __table_args__ = (
        Index("idx_purchase_items_sku", "sku_id"),
        Index("idx_purchase_items_lot", "lot_id"),
    )


# -------------------------
# Invoices + Items + Payments + Allocations
# -------------------------
class Invoice(Base):
    __tablename__ = "invoices"
    id = UUID_PK
    bill_no = Column(Text, nullable=False, unique=True)
    bill_type = Column(Text)
    sale_type = Column(Text)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    channel = Column(Text)
    gst_type = Column(Text)
    sale_to = Column(Text)

    qty = Column(Numeric, nullable=False)
    total_mrp = Column(Numeric, nullable=False)
    total_rate = Column(Numeric, nullable=False)

    cust_disc_percent = Column(Numeric, nullable=False)
    cust_disc = Column(Numeric, nullable=False)
    bill_disc_percent = Column(Numeric, nullable=False)
    bill_disc = Column(Numeric, nullable=False)
    extra_disc_percent = Column(Numeric, nullable=False)
    extra_disc = Column(Numeric, nullable=False)
    membercard_disc = Column(Numeric, nullable=False)
    total_disc = Column(Numeric, nullable=False)

    gst_0 = Column(Numeric, nullable=False)
    gst_3 = Column(Numeric, nullable=False)
    gst_5 = Column(Numeric, nullable=False)
    gst_12 = Column(Numeric, nullable=False)
    gst_18 = Column(Numeric, nullable=False)
    gst_28 = Column(Numeric, nullable=False)

    taxable_amount = Column(Numeric, nullable=False)
    taxable_amount_0 = Column(Numeric, nullable=False)
    taxable_amount_3 = Column(Numeric, nullable=False)
    taxable_amount_5 = Column(Numeric, nullable=False)
    taxable_amount_12 = Column(Numeric, nullable=False)
    taxable_amount_18 = Column(Numeric, nullable=False)
    taxable_amount_28 = Column(Numeric, nullable=False)

    igst_0 = Column(Numeric, nullable=False, server_default=text("0.00"))
    igst_3 = Column(Numeric, nullable=False, server_default=text("0.00"))
    igst_5 = Column(Numeric, nullable=False, server_default=text("0.00"))
    igst_12 = Column(Numeric, nullable=False, server_default=text("0.00"))
    igst_18 = Column(Numeric, nullable=False, server_default=text("0.00"))
    igst_28 = Column(Numeric, nullable=False, server_default=text("0.00"))

    cgst_0 = Column(Numeric, nullable=False, server_default=text("0.00"))
    cgst_1_5 = Column(Numeric, nullable=False, server_default=text("0.00"))
    cgst_2_5 = Column(Numeric, nullable=False, server_default=text("0.00"))
    cgst_6 = Column(Numeric, nullable=False, server_default=text("0.00"))
    cgst_9 = Column(Numeric, nullable=False, server_default=text("0.00"))
    cgst_14 = Column(Numeric, nullable=False, server_default=text("0.00"))

    sgst_0 = Column(Numeric, nullable=False, server_default=text("0.00"))
    sgst_1_5 = Column(Numeric, nullable=False, server_default=text("0.00"))
    sgst_2_5 = Column(Numeric, nullable=False, server_default=text("0.00"))
    sgst_6 = Column(Numeric, nullable=False, server_default=text("0.00"))
    sgst_9 = Column(Numeric, nullable=False, server_default=text("0.00"))
    sgst_14 = Column(Numeric, nullable=False, server_default=text("0.00"))

    total_igst = Column(Numeric, nullable=False, server_default=text("0.00"))
    total_cgst = Column(Numeric, nullable=False, server_default=text("0.00"))
    total_sgst = Column(Numeric, nullable=False, server_default=text("0.00"))
    net_tax = Column(Numeric, nullable=False, server_default=text("0.00"))
    gross_sale = Column(Numeric, nullable=False, server_default=text("0.00"))

    round_off = Column(Numeric)
    net_total = Column(Numeric, nullable=False)

    other_charges = Column(Numeric)
    credit_amt = Column(Numeric, nullable=False)
    cn_note = Column(Numeric, nullable=False)
    cn_amount = Column(Numeric, nullable=False)

    payment_cash = Column(Numeric, nullable=False)
    payment_card = Column(Numeric, nullable=False)
    payment_google_pay = Column(Numeric, nullable=False)
    payment_phonepe = Column(Numeric, nullable=False)
    payment_paytm = Column(Numeric, nullable=False)
    actual_cash = Column(Numeric, nullable=False)
    cash_return = Column(Numeric, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    customer = relationship("Customer", back_populates="invoices", lazy="joined")
    operator = relationship("User", back_populates="invoices", lazy="joined")

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="noload")
    payments = relationship("InvoicePayment", back_populates="invoice", cascade="all, delete-orphan", lazy="noload")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = UUID_PK
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    qty = Column(Numeric, nullable=False)
    mrp = Column(Numeric)
    total_mrp = Column(Numeric, nullable=False)
    rate = Column(Numeric, nullable=False)
    total_rate = Column(Numeric, nullable=False)
    current_qty = Column(Numeric, nullable=False)
    discount_percent = Column(Numeric, nullable=False)
    discount_amount = Column(Numeric, server_default=text("0"))
    other_discount = Column(Numeric, nullable=False)
    total_discount = Column(Numeric, nullable=False)

    igst_percent = Column(Numeric, nullable=False)
    igst_amount = Column(Numeric, nullable=False)
    sgst_percent = Column(Numeric, nullable=False)
    sgst_amount = Column(Numeric, nullable=False)
    cgst_percent = Column(Numeric, nullable=False)
    cgst_amount = Column(Numeric, nullable=False)
    cess_percent = Column(Numeric, nullable=False)
    cess_amount = Column(Numeric, nullable=False)

    gross_amount = Column(Numeric, nullable=False)
    tax_amount = Column(Numeric, nullable=False)
    taxable_amount = Column(Numeric, nullable=False)
    net_total = Column(Numeric, nullable=False)
    round_off = Column(Numeric, nullable=False)

    unit_cost_at_sale = Column(Numeric)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    invoice = relationship("Invoice", back_populates="items", lazy="joined")
    sku = relationship("Product", back_populates="invoice_items", lazy="joined")
    operator = relationship("User", back_populates="invoice_items", lazy="joined")

    allocations = relationship("InvoiceItemAllocation", back_populates="invoice_item",
                               cascade="all, delete-orphan", lazy="selectin")


class InvoiceItemAllocation(Base):
    __tablename__ = "invoice_item_allocations"
    invoice_item_id = Column(UUID(as_uuid=True), ForeignKey("invoice_items.id", ondelete="CASCADE"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"), nullable=False)
    qty = Column(Numeric, nullable=False)
    allocation_method = Column(AllocationMethodEnum, nullable=False)
    confidence = Column(Numeric, nullable=False)

    invoice_item = relationship("InvoiceItem", back_populates="allocations", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")

    __table_args__ = (
        PrimaryKeyConstraint("invoice_item_id", "lot_id", name="invoice_item_allocations_pkey"),
        CheckConstraint("qty > 0", name="chk_alloc_qty_pos"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="chk_alloc_conf_0_1"),
    )


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"
    id = UUID_PK
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    method = Column(PaymentMethodEnum, nullable=False)
    amount = Column(Numeric, nullable=False)
    ref_note = Column(Text)

    invoice = relationship("Invoice", back_populates="payments", lazy="joined")

    __table_args__ = (CheckConstraint("amount >= 0", name="chk_payment_amount_nonneg"),)


# -------------------------
# Inventory Ledger
# -------------------------
class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"
    id = UUID_PK
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"))
    movement_type = Column(MovementTypeEnum, nullable=False)
    qty = Column(Numeric, nullable=False)           # signed (+in / -out)
    unit_cost = Column(Numeric)
    ref_table = Column(Text)
    ref_id = Column(UUID(as_uuid=True))
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    sku = relationship("Product", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")

    __table_args__ = (
        Index("idx_ledger_sku_time", "sku_id", "occurred_at"),
        Index("idx_ledger_lot_time", "lot_id", "occurred_at"),
    )


# -------------------------
# Conversions (bulk -> packs)
# -------------------------
class Conversion(Base):
    __tablename__ = "conversions"
    id = UUID_PK
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    notes = Column(Text)

    operator = relationship("User", back_populates="conversions", lazy="joined")
    inputs = relationship("ConversionInput", back_populates="conversion", cascade="all, delete-orphan", lazy="noload")
    outputs = relationship("ConversionOutput", back_populates="conversion", cascade="all, delete-orphan", lazy="noload")


class ConversionInput(Base):
    __tablename__ = "conversion_inputs"
    id = UUID_PK
    conversion_id = Column(UUID(as_uuid=True), ForeignKey("conversions.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"))
    qty_in = Column(Numeric, nullable=False)
    unit_cost = Column(Numeric)

    conversion = relationship("Conversion", back_populates="inputs", lazy="joined")
    sku = relationship("Product", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")

    __table_args__ = (CheckConstraint("qty_in > 0", name="chk_conv_in_qty_pos"),)


class ConversionOutput(Base):
    __tablename__ = "conversion_outputs"
    id = UUID_PK
    conversion_id = Column(UUID(as_uuid=True), ForeignKey("conversions.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"))
    qty_out = Column(Numeric, nullable=False)
    unit_cost = Column(Numeric)

    conversion = relationship("Conversion", back_populates="outputs", lazy="joined")
    sku = relationship("Product", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")

    __table_args__ = (CheckConstraint("qty_out > 0", name="chk_conv_out_qty_pos"),)


class BomRecipe(Base):
    __tablename__ = "bom_recipes"
    id = UUID_PK
    finished_sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    component_sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    qty_per_finished = Column(Numeric, nullable=False)

    finished_sku = relationship("Product", foreign_keys=[finished_sku_id], back_populates="bom_as_finished", lazy="joined")
    component_sku = relationship("Product", foreign_keys=[component_sku_id], back_populates="bom_as_component", lazy="joined")

    __table_args__ = (
        CheckConstraint("qty_per_finished > 0", name="chk_bom_qty_pos"),
    )


# -------------------------
# Reconciliation & Crosswalk
# -------------------------
class StockReconciliation(Base):
    __tablename__ = "stock_reconciliation"
    id = UUID_PK
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    vendor_system = Column(Text, nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"))
    expected_qty = Column(Numeric, nullable=False)
    vendor_qty = Column(Numeric, nullable=False)
    diff_qty = Column(Numeric, nullable=False)
    note = Column(Text)

    sku = relationship("Product", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")


class VendorItemXwalk(Base):
    __tablename__ = "vendor_item_xwalk"
    vendor_system = Column(Text, primary_key=True)
    vendor_item_key = Column(Text, primary_key=True)

    vendor_name = Column(Text)
    vendor_barcode = Column(Text)
    vendor_mrp = Column(Numeric)
    vendor_expiry = Column(Date)
    vendor_brand = Column(Text)

    sku_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("product_lots.id"))
    method = Column(AllocationMethodEnum, nullable=False)
    confidence = Column(Numeric, nullable=False)
    source_file = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    sku = relationship("Product", lazy="joined")
    lot = relationship("ProductLot", lazy="joined")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="chk_xwalk_conf_0_1"),
    )


# -------------------------
# Optional: convenience bootstrap
# -------------------------
def create_all(bind):
    """
    Create enums (checkfirst) and tables in the correct order.
    """
    MovementTypeEnum.create(bind, checkfirst=True)
    AllocationMethodEnum.create(bind, checkfirst=True)
    PaymentMethodEnum.create(bind, checkfirst=True)
    Base.metadata.create_all(bind)
