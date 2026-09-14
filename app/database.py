from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
import enum
import os

DATABASE_URL = "sqlite:///./smart_invoice.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class SubscriptionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REJECTED = "rejected"

class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    DUE = "due"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="user", uselist=False)
    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user", foreign_keys="Payment.user_id")

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    store_name = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    district = Column(String(100), nullable=False)
    upazila = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    alt_phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)
    logo = Column(String(255), nullable=True)
    bin_number = Column(String(50), nullable=True)
    vat_number = Column(String(50), nullable=True)
    tin_number = Column(String(50), nullable=True)
    trade_license = Column(String(50), nullable=True)
    footer_note = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="store")
    category = relationship("Category")
    items = relationship("StoreItem", back_populates="store")
    customers = relationship("Customer", back_populates="store")
    invoices = relationship("Invoice", back_populates="store")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    name_bn = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    
    items = relationship("CategoryItem", back_populates="category")

class CategoryItem(Base):
    __tablename__ = "category_items"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String(150), nullable=False)
    name_bn = Column(String(150), nullable=False)
    type = Column(String(20), default="service")  # product or service
    default_price = Column(Float, default=0.0)
    unit = Column(String(50), default="টি")
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    
    category = relationship("Category", back_populates="items")

class StoreItem(Base):
    __tablename__ = "store_items"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(150), nullable=False)
    name_bn = Column(String(150), nullable=True)
    type = Column(String(20), default="service")
    price = Column(Float, default=0.0)
    unit = Column(String(50), default="টি")
    description = Column(Text, nullable=True)
    stock = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="items")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(Date, default=date.today)
    due_date = Column(Date, nullable=True)
    subtotal = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    extra_charge = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    due_amount = Column(Float, default=0.0)
    status = Column(String(20), default=InvoiceStatus.DRAFT.value)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    store_item_id = Column(Integer, ForeignKey("store_items.id"), nullable=True)
    item_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="টি")
    unit_price = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    invoice = relationship("Invoice", back_populates="items")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, default=50.0)
    start_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(String(20), default=SubscriptionStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    method = Column(String(50), default="bkash")
    payment_number = Column(String(20), nullable=True)
    transaction_id = Column(String(100), nullable=False)
    amount = Column(Float, default=50.0)
    screenshot = Column(String(255), nullable=True)
    status = Column(String(20), default=PaymentStatus.PENDING.value)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    payment_date = Column(Date, nullable=True)
    
    user = relationship("User", back_populates="payments", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    subscription = relationship("Subscription", back_populates="payments")

def init_db():
    Base.metadata.create_all(bind=engine)
