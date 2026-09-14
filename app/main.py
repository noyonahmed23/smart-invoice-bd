from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
from typing import Optional, List
import os
import shutil
import uuid
from pathlib import Path

from .database import (
    get_db, init_db, User, Store, Category, CategoryItem, StoreItem,
    Customer, Invoice, InvoiceItem, Subscription, Payment,
    UserRole, SubscriptionStatus, InvoiceStatus, PaymentStatus
)
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_user, require_admin
)
from .seed import run_seed

app = FastAPI(title="Smart Invoice Generator", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Helper functions
def get_active_subscription(db: Session, user_id: int):
    return db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == SubscriptionStatus.ACTIVE.value,
        Subscription.expiry_date >= date.today()
    ).order_by(Subscription.expiry_date.desc()).first()

def days_remaining(sub: Subscription) -> int:
    if not sub or not sub.expiry_date:
        return 0
    delta = sub.expiry_date - date.today()
    return max(0, delta.days)

def generate_invoice_number(db: Session, store_id: int) -> str:
    year = date.today().year
    count = db.query(Invoice).filter(
        Invoice.store_id == store_id,
        Invoice.invoice_number.like(f"INV-{year}-%")
    ).count()
    return f"INV-{year}-{str(count + 1).zfill(6)}"

def save_upload(file: UploadFile, prefix: str = "file") -> Optional[str]:
    if not file or not file.filename:
        return None
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "gif", "webp", "pdf"]:
        return None
    filename = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/static/uploads/{filename}"

# ============== AUTH ROUTES ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        if user.role == UserRole.ADMIN.value:
            return RedirectResponse("/admin", status_code=302)
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    categories = db.query(Category).filter(Category.active == True).all()
    return templates.TemplateResponse("register.html", {"request": request, "categories": categories})

@app.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(None),
    password: str = Form(...),
    store_name: str = Form(...),
    address: str = Form(...),
    district: str = Form(...),
    upazila: str = Form(...),
    category_id: int = Form(...),
    phone: str = Form(None),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Validation
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে",
            "categories": db.query(Category).filter(Category.active == True).all()
        })
    
    existing = db.query(User).filter(User.mobile == mobile).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "এই মোবাইল নম্বর ইতিমধ্যে নিবন্ধিত",
            "categories": db.query(Category).filter(Category.active == True).all()
        })
    
    logo_path = save_upload(logo, "logo") if logo and logo.filename else None
    
    user = User(
        name=name,
        mobile=mobile,
        email=email or None,
        password_hash=get_password_hash(password),
        role=UserRole.USER.value
    )
    db.add(user)
    db.flush()
    
    store = Store(
        user_id=user.id,
        store_name=store_name,
        address=address,
        district=district,
        upazila=upazila,
        phone=phone or mobile,
        logo=logo_path,
        category_id=category_id
    )
    db.add(store)
    db.flush()
    
    # Load default items from category
    cat_items = db.query(CategoryItem).filter(
        CategoryItem.category_id == category_id,
        CategoryItem.active == True
    ).all()
    for ci in cat_items:
        si = StoreItem(
            store_id=store.id,
            category_id=category_id,
            name=ci.name,
            name_bn=ci.name_bn,
            type=ci.type,
            price=ci.default_price,
            unit=ci.unit,
            description=ci.description
        )
        db.add(si)
    
    # Create pending subscription
    sub = Subscription(user_id=user.id, amount=50.0, status=SubscriptionStatus.PENDING.value)
    db.add(sub)
    
    db.commit()
    
    # Auto login
    token = create_access_token({"sub": user.id})
    response = RedirectResponse("/subscription", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=60*60*24*7)
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        if user.role == UserRole.ADMIN.value:
            return RedirectResponse("/admin", status_code=302)
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    mobile: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.mobile == mobile).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "মোবাইল নম্বর বা পাসওয়ার্ড ভুল"
        })
    
    token = create_access_token({"sub": user.id})
    if user.role == UserRole.ADMIN.value:
        response = RedirectResponse("/admin", status_code=302)
    else:
        response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=60*60*24*7)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# ============== USER DASHBOARD ==============

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if user.role == UserRole.ADMIN.value:
        return RedirectResponse("/admin", status_code=302)
    
    store = db.query(Store).filter(Store.user_id == user.id).first()
    sub = get_active_subscription(db, user.id)
    days = days_remaining(sub) if sub else 0
    
    # Stats
    total_invoices = db.query(Invoice).filter(Invoice.store_id == store.id).count() if store else 0
    today = date.today()
    today_invoices = db.query(Invoice).filter(
        Invoice.store_id == store.id, Invoice.invoice_date == today
    ).count() if store else 0
    
    month_start = today.replace(day=1)
    month_sales = db.query(func.sum(Invoice.grand_total)).filter(
        Invoice.store_id == store.id,
        Invoice.invoice_date >= month_start,
        Invoice.status != InvoiceStatus.CANCELLED.value
    ).scalar() or 0 if store else 0
    
    total_due = db.query(func.sum(Invoice.due_amount)).filter(
        Invoice.store_id == store.id,
        Invoice.due_amount > 0
    ).scalar() or 0 if store else 0
    
    total_paid = db.query(func.sum(Invoice.paid_amount)).filter(
        Invoice.store_id == store.id
    ).scalar() or 0 if store else 0
    
    draft_count = db.query(Invoice).filter(
        Invoice.store_id == store.id, Invoice.status == InvoiceStatus.DRAFT.value
    ).count() if store else 0
    
    recent = db.query(Invoice).filter(Invoice.store_id == store.id).order_by(Invoice.created_at.desc()).limit(5).all() if store else []
    
    pending_payment = db.query(Payment).filter(
        Payment.user_id == user.id, Payment.status == PaymentStatus.PENDING.value
    ).first()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "store": store,
        "sub": sub,
        "days_remaining": days,
        "total_invoices": total_invoices,
        "today_invoices": today_invoices,
        "month_sales": month_sales,
        "total_due": total_due,
        "total_paid": total_paid,
        "draft_count": draft_count,
        "recent": recent,
        "pending_payment": pending_payment
    })

# ============== SUBSCRIPTION & PAYMENT ==============

@app.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    sub = get_active_subscription(db, user.id)
    all_subs = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.created_at.desc()).all()
    payments = db.query(Payment).filter(Payment.user_id == user.id).order_by(Payment.submitted_at.desc()).all()
    pending = db.query(Payment).filter(Payment.user_id == user.id, Payment.status == PaymentStatus.PENDING.value).first()
    
    return templates.TemplateResponse("subscription.html", {
        "request": request,
        "user": user,
        "sub": sub,
        "days_remaining": days_remaining(sub) if sub else 0,
        "all_subs": all_subs,
        "payments": payments,
        "pending": pending
    })

@app.post("/payment/submit")
async def submit_payment(
    request: Request,
    method: str = Form("bkash"),
    payment_number: str = Form(...),
    transaction_id: str = Form(...),
    amount: float = Form(50.0),
    payment_date: str = Form(...),
    screenshot: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    # Check existing pending
    existing = db.query(Payment).filter(
        Payment.user_id == user.id,
        Payment.status == PaymentStatus.PENDING.value
    ).first()
    if existing:
        return RedirectResponse("/subscription?error=already_pending", status_code=302)
    
    # Check duplicate txn
    dup = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
    if dup:
        return RedirectResponse("/subscription?error=duplicate_txn", status_code=302)
    
    ss_path = save_upload(screenshot, "payment") if screenshot and screenshot.filename else None
    
    # Ensure subscription exists
    sub = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status.in_([SubscriptionStatus.PENDING.value, SubscriptionStatus.EXPIRED.value, SubscriptionStatus.REJECTED.value])
    ).order_by(Subscription.created_at.desc()).first()
    
    if not sub:
        sub = Subscription(user_id=user.id, amount=50.0, status=SubscriptionStatus.PENDING.value)
        db.add(sub)
        db.flush()
    
    payment = Payment(
        user_id=user.id,
        subscription_id=sub.id,
        method=method,
        payment_number=payment_number,
        transaction_id=transaction_id,
        amount=amount,
        screenshot=ss_path,
        status=PaymentStatus.PENDING.value,
        payment_date=datetime.strptime(payment_date, "%Y-%m-%d").date() if payment_date else date.today()
    )
    db.add(payment)
    db.commit()
    
    return RedirectResponse("/subscription?success=submitted", status_code=302)

# ============== STORE SETTINGS ==============

@app.get("/store", response_class=HTMLResponse)
async def store_settings(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    categories = db.query(Category).filter(Category.active == True).all()
    return templates.TemplateResponse("store.html", {
        "request": request, "user": user, "store": store, "categories": categories
    })

@app.post("/store")
async def update_store(
    request: Request,
    store_name: str = Form(...),
    address: str = Form(...),
    district: str = Form(...),
    upazila: str = Form(...),
    phone: str = Form(...),
    alt_phone: str = Form(None),
    email: str = Form(None),
    website: str = Form(None),
    bin_number: str = Form(None),
    vat_number: str = Form(None),
    tin_number: str = Form(None),
    trade_license: str = Form(None),
    footer_note: str = Form(None),
    category_id: int = Form(None),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    if not store:
        raise HTTPException(404, "দোকান পাওয়া যায়নি")
    
    store.store_name = store_name
    store.address = address
    store.district = district
    store.upazila = upazila
    store.phone = phone
    store.alt_phone = alt_phone
    store.email = email
    store.website = website
    store.bin_number = bin_number
    store.vat_number = vat_number
    store.tin_number = tin_number
    store.trade_license = trade_license
    store.footer_note = footer_note
    if category_id:
        store.category_id = category_id
    
    if logo and logo.filename:
        logo_path = save_upload(logo, "logo")
        if logo_path:
            store.logo = logo_path
    
    db.commit()
    return RedirectResponse("/store?success=updated", status_code=302)

# ============== PRODUCTS & SERVICES ==============

@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    if not store:
        return RedirectResponse("/store", status_code=302)
    
    items = db.query(StoreItem).filter(StoreItem.store_id == store.id).order_by(StoreItem.name).all()
    categories = db.query(Category).filter(Category.active == True).all()
    
    return templates.TemplateResponse("products.html", {
        "request": request, "user": user, "store": store, "items": items, "categories": categories
    })

@app.post("/products/add")
async def add_product(
    request: Request,
    name: str = Form(...),
    type: str = Form("service"),
    price: float = Form(0),
    unit: str = Form("টি"),
    description: str = Form(None),
    category_id: int = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    item = StoreItem(
        store_id=store.id,
        category_id=category_id,
        name=name,
        name_bn=name,
        type=type,
        price=price,
        unit=unit,
        description=description
    )
    db.add(item)
    db.commit()
    return RedirectResponse("/products?success=added", status_code=302)

@app.post("/products/edit/{item_id}")
async def edit_product(
    item_id: int,
    name: str = Form(...),
    type: str = Form("service"),
    price: float = Form(0),
    unit: str = Form("টি"),
    description: str = Form(None),
    active: str = Form("true"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    item = db.query(StoreItem).filter(StoreItem.id == item_id, StoreItem.store_id == store.id).first()
    if not item:
        raise HTTPException(404)
    item.name = name
    item.name_bn = name
    item.type = type
    item.price = price
    item.unit = unit
    item.description = description
    item.active = active == "true"
    db.commit()
    return RedirectResponse("/products?success=updated", status_code=302)

@app.post("/products/delete/{item_id}")
async def delete_product(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    item = db.query(StoreItem).filter(StoreItem.id == item_id, StoreItem.store_id == store.id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/products?success=deleted", status_code=302)

# ============== CUSTOMERS ==============

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    customers = db.query(Customer).filter(Customer.store_id == store.id).order_by(Customer.name).all() if store else []
    return templates.TemplateResponse("customers.html", {
        "request": request, "user": user, "store": store, "customers": customers
    })

@app.post("/customers/add")
async def add_customer(
    name: str = Form(...),
    mobile: str = Form(None),
    address: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    c = Customer(store_id=store.id, name=name, mobile=mobile, address=address)
    db.add(c)
    db.commit()
    return RedirectResponse("/customers?success=added", status_code=302)

# ============== INVOICE CREATE ==============

@app.get("/invoice/create", response_class=HTMLResponse)
async def create_invoice_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    sub = get_active_subscription(db, user.id)
    if not sub:
        return RedirectResponse("/subscription?error=no_sub", status_code=302)
    
    items = db.query(StoreItem).filter(StoreItem.store_id == store.id, StoreItem.active == True).all()
    customers = db.query(Customer).filter(Customer.store_id == store.id).all()
    
    return templates.TemplateResponse("invoice_create.html", {
        "request": request, "user": user, "store": store, "items": items, "customers": customers
    })

@app.post("/invoice/create")
async def create_invoice(
    request: Request,
    customer_name: str = Form(...),
    customer_mobile: str = Form(None),
    customer_address: str = Form(None),
    customer_id: int = Form(None),
    invoice_date: str = Form(...),
    due_date: str = Form(None),
    discount: float = Form(0),
    tax: float = Form(0),
    extra_charge: float = Form(0),
    paid_amount: float = Form(0),
    notes: str = Form(None),
    status: str = Form("running"),
    item_ids: List[str] = Form([]),
    item_names: List[str] = Form([]),
    quantities: List[float] = Form([]),
    units: List[str] = Form([]),
    unit_prices: List[float] = Form([]),
    item_discounts: List[float] = Form([]),
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    sub = get_active_subscription(db, user.id)
    if not sub:
        return RedirectResponse("/subscription?error=no_sub", status_code=302)
    
    # Customer
    if customer_id:
        customer = db.query(Customer).filter(Customer.id == customer_id, Customer.store_id == store.id).first()
    else:
        customer = Customer(
            store_id=store.id,
            name=customer_name,
            mobile=customer_mobile,
            address=customer_address
        )
        db.add(customer)
        db.flush()
    
    inv_number = generate_invoice_number(db, store.id)
    
    # Calculate
    subtotal = 0.0
    inv_items = []
    for i in range(len(item_names)):
        qty = quantities[i] if i < len(quantities) else 1
        price = unit_prices[i] if i < len(unit_prices) else 0
        disc = item_discounts[i] if i < len(item_discounts) else 0
        total = (qty * price) - disc
        subtotal += total
        inv_items.append({
            "store_item_id": int(item_ids[i]) if i < len(item_ids) and item_ids[i] else None,
            "item_name": item_names[i],
            "quantity": qty,
            "unit": units[i] if i < len(units) else "টি",
            "unit_price": price,
            "discount": disc,
            "total": total
        })
    
    grand = subtotal - discount + tax + extra_charge
    due = grand - paid_amount
    
    if due <= 0:
        inv_status = InvoiceStatus.PAID.value
    elif paid_amount > 0:
        inv_status = InvoiceStatus.PARTIALLY_PAID.value
    else:
        inv_status = status if status in [s.value for s in InvoiceStatus] else InvoiceStatus.RUNNING.value
    
    invoice = Invoice(
        store_id=store.id,
        customer_id=customer.id,
        invoice_number=inv_number,
        invoice_date=datetime.strptime(invoice_date, "%Y-%m-%d").date(),
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        extra_charge=extra_charge,
        grand_total=grand,
        paid_amount=paid_amount,
        due_amount=max(0, due),
        status=inv_status,
        notes=notes
    )
    db.add(invoice)
    db.flush()
    
    for it in inv_items:
        ii = InvoiceItem(
            invoice_id=invoice.id,
            store_item_id=it["store_item_id"],
            item_name=it["item_name"],
            quantity=it["quantity"],
            unit=it["unit"],
            unit_price=it["unit_price"],
            discount=it["discount"],
            total=it["total"]
        )
        db.add(ii)
    
    db.commit()
    return RedirectResponse(f"/invoice/{invoice.id}?success=created", status_code=302)

# ============== INVOICE LIST & VIEW ==============

@app.get("/invoices", response_class=HTMLResponse)
async def invoices_page(
    request: Request,
    q: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user)
):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    query = db.query(Invoice).filter(Invoice.store_id == store.id)
    
    if q:
        query = query.join(Customer).filter(
            or_(
                Invoice.invoice_number.contains(q),
                Customer.name.contains(q),
                Customer.mobile.contains(q)
            )
        )
    if status:
        query = query.filter(Invoice.status == status)
    if date_from:
        query = query.filter(Invoice.invoice_date >= datetime.strptime(date_from, "%Y-%m-%d").date())
    if date_to:
        query = query.filter(Invoice.invoice_date <= datetime.strptime(date_to, "%Y-%m-%d").date())
    
    invoices = query.order_by(Invoice.created_at.desc()).limit(100).all()
    
    return templates.TemplateResponse("invoices.html", {
        "request": request, "user": user, "store": store, "invoices": invoices,
        "q": q, "status": status, "date_from": date_from, "date_to": date_to
    })

@app.get("/invoice/{invoice_id}", response_class=HTMLResponse)
async def view_invoice(invoice_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.store_id == store.id).first()
    if not invoice:
        raise HTTPException(404, "ইনভয়েস পাওয়া যায়নি")
    
    return templates.TemplateResponse("invoice_view.html", {
        "request": request, "user": user, "store": store, "invoice": invoice
    })

@app.get("/invoice/{invoice_id}/print", response_class=HTMLResponse)
async def print_invoice(invoice_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = db.query(Store).filter(Store.user_id == user.id).first()
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.store_id == store.id).first()
    if not invoice:
        raise HTTPException(404)
    return templates.TemplateResponse("invoice_print.html", {
        "request": request, "store": store, "invoice": invoice
    })

# ============== ADMIN PANEL ==============

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_users = db.query(User).filter(User.role == UserRole.USER.value).count()
    active_subs = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.ACTIVE.value,
        Subscription.expiry_date >= date.today()
    ).count()
    pending_payments = db.query(Payment).filter(Payment.status == PaymentStatus.PENDING.value).count()
    expired_subs = db.query(Subscription).filter(
        or_(
            Subscription.status == SubscriptionStatus.EXPIRED.value,
            and_(Subscription.status == SubscriptionStatus.ACTIVE.value, Subscription.expiry_date < date.today())
        )
    ).count()
    total_invoices = db.query(Invoice).count()
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.APPROVED.value).scalar() or 0
    today_regs = db.query(User).filter(
        User.role == UserRole.USER.value,
        func.date(User.created_at) == date.today()
    ).count()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "admin": admin,
        "total_users": total_users,
        "active_subs": active_subs,
        "pending_payments": pending_payments,
        "expired_subs": expired_subs,
        "total_invoices": total_invoices,
        "total_revenue": total_revenue,
        "today_regs": today_regs
    })

@app.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    payments = db.query(Payment).order_by(Payment.submitted_at.desc()).all()
    return templates.TemplateResponse("admin/payments.html", {
        "request": request, "admin": admin, "payments": payments
    })

@app.post("/admin/payment/{payment_id}/approve")
async def approve_payment(payment_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment or payment.status != PaymentStatus.PENDING.value:
        raise HTTPException(400, "অবৈধ পেমেন্ট")
    
    payment.status = PaymentStatus.APPROVED.value
    payment.approved_at = datetime.utcnow()
    payment.approved_by = admin.id
    
    sub = payment.subscription
    if sub:
        sub.status = SubscriptionStatus.ACTIVE.value
        sub.start_date = date.today()
        sub.expiry_date = date.today() + timedelta(days=30)
        sub.amount = payment.amount
    
    db.commit()
    return RedirectResponse("/admin/payments?success=approved", status_code=302)

@app.post("/admin/payment/{payment_id}/reject")
async def reject_payment(payment_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment or payment.status != PaymentStatus.PENDING.value:
        raise HTTPException(400)
    
    payment.status = PaymentStatus.REJECTED.value
    payment.approved_at = datetime.utcnow()
    payment.approved_by = admin.id
    
    if payment.subscription:
        payment.subscription.status = SubscriptionStatus.REJECTED.value
    
    db.commit()
    return RedirectResponse("/admin/payments?success=rejected", status_code=302)

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).filter(User.role == UserRole.USER.value).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse("admin/users.html", {
        "request": request, "admin": admin, "users": users
    })

@app.get("/admin/user/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404)
    store = db.query(Store).filter(Store.user_id == u.id).first()
    subs = db.query(Subscription).filter(Subscription.user_id == u.id).all()
    payments = db.query(Payment).filter(Payment.user_id == u.id).all()
    invoices = db.query(Invoice).filter(Invoice.store_id == store.id).all() if store else []
    items = db.query(StoreItem).filter(StoreItem.store_id == store.id).all() if store else []
    
    return templates.TemplateResponse("admin/user_detail.html", {
        "request": request, "admin": admin, "u": u, "store": store,
        "subs": subs, "payments": payments, "invoices": invoices, "items": items
    })

@app.get("/admin/invoices", response_class=HTMLResponse)
async def admin_invoices(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin/invoices.html", {
        "request": request, "admin": admin, "invoices": invoices
    })

@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    categories = db.query(Category).all()
    return templates.TemplateResponse("admin/categories.html", {
        "request": request, "admin": admin, "categories": categories
    })

# Startup
@app.on_event("startup")
async def startup():
    run_seed()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
