from .database import SessionLocal, Category, CategoryItem, User, init_db, UserRole
from .auth import get_password_hash
from datetime import datetime
import os

def seed_categories(db):
    categories_data = [
        {
            "name": "Computer Shop",
            "name_bn": "কম্পিউটার দোকান ও সার্ভিস সেন্টার",
            "items": [
                ("Computer Repair", "কম্পিউটার সার্ভিস", "service", 300),
                ("Laptop Repair", "ল্যাপটপ সার্ভিস", "service", 400),
                ("Windows Installation", "উইন্ডোজ ইনস্টল", "service", 300),
                ("Software Installation", "সফটওয়্যার ইনস্টল", "service", 200),
                ("Driver Installation", "ড্রাইভার ইনস্টল", "service", 150),
                ("Antivirus Installation", "অ্যান্টিভাইরাস ইনস্টল", "service", 200),
                ("Computer Formatting", "কম্পিউটার ফরম্যাটিং", "service", 350),
                ("Desktop Repair", "ডেস্কটপ সার্ভিস", "service", 350),
                ("Printer Setup", "প্রিন্টার সেটআপ", "service", 200),
                ("Printer Repair", "প্রিন্টার সার্ভিস", "service", 300),
                ("Internet Setup", "ইন্টারনেট সেটআপ", "service", 250),
                ("LAN Setup", "ল্যান সেটআপ", "service", 300),
                ("WiFi Setup", "ওয়াইফাই সেটআপ", "service", 200),
                ("Online Application", "অনলাইন আবেদন", "service", 100),
                ("Online Registration", "অনলাইন রেজিস্ট্রেশন", "service", 100),
                ("CV/Resume Typing", "CV তৈরি", "service", 150),
                ("Document Typing", "ডকুমেন্ট টাইপিং", "service", 50),
                ("Printing", "প্রিন্ট", "service", 5),
                ("Photocopy", "ফটোকপি", "service", 2),
                ("Scanning", "স্ক্যান", "service", 10),
                ("Passport Photo", "পাসপোর্ট ছবি", "service", 50),
                ("Photo Editing", "ছবি এডিট", "service", 30),
                ("Graphic Design", "গ্রাফিক্স ডিজাইন", "service", 200),
                ("Lamination", "লেমিনেশন", "service", 20),
                ("Email Service", "ইমেইল সার্ভিস", "service", 50),
                ("Data Entry", "ডাটা এন্ট্রি", "service", 100),
                ("Other Service", "অন্যান্য সেবা", "service", 0),
            ]
        },
        {
            "name": "Mobile Shop",
            "name_bn": "মোবাইল দোকান",
            "items": [
                ("Mobile Phone", "মোবাইল ফোন", "product", 0),
                ("Mobile Accessories", "মোবাইল এক্সেসরিজ", "product", 0),
                ("Screen Protector", "স্ক্রিন প্রোটেক্টর", "product", 100),
                ("Charger", "চার্জার", "product", 150),
                ("Data Cable", "ডাটা কেবল", "product", 80),
                ("Earphone", "ইয়ারফোন", "product", 120),
                ("Mobile Cover", "মোবাইল কভার", "product", 50),
                ("SIM Related Service", "সিম সংক্রান্ত সেবা", "service", 50),
                ("Software Service", "সফটওয়্যার সার্ভিস", "service", 200),
                ("Mobile Repair", "মোবাইল সার্ভিস", "service", 300),
                ("Display Replacement", "ডিসপ্লে পরিবর্তন", "service", 1500),
                ("Battery Replacement", "ব্যাটারি পরিবর্তন", "service", 800),
                ("Other Service", "অন্যান্য সেবা", "service", 0),
            ]
        },
        {
            "name": "Pharmacy",
            "name_bn": "ফার্মেসি / মেডিসিন শপ",
            "items": [
                ("Medicine", "ওষুধ", "product", 0),
                ("Generic Medicine", "জেনেরিক ওষুধ", "product", 0),
                ("Other Product", "অন্যান্য পণ্য", "product", 0),
            ]
        },
        {
            "name": "Grocery Shop",
            "name_bn": "মুদি দোকান",
            "items": [
                ("Rice", "চাল", "product", 0),
                ("Oil", "তেল", "product", 0),
                ("Sugar", "চিনি", "product", 0),
                ("Flour", "আটা", "product", 0),
                ("Biscuit", "বিস্কুট", "product", 0),
                ("Drinks", "পানীয়", "product", 0),
                ("Household Items", "গৃহস্থালী পণ্য", "product", 0),
                ("Custom Product", "কাস্টম পণ্য", "product", 0),
            ]
        },
        {
            "name": "Clothing Shop",
            "name_bn": "পোশাকের দোকান",
            "items": [
                ("Shirt", "শার্ট", "product", 0),
                ("Pant", "প্যান্ট", "product", 0),
                ("T-Shirt", "টি-শার্ট", "product", 0),
                ("Saree", "শাড়ি", "product", 0),
                ("Panjabi", "পাঞ্জাবি", "product", 0),
                ("Salwar Kameez", "সালোয়ার কামিজ", "product", 0),
                ("Shoes", "জুতা", "product", 0),
                ("Custom Product", "কাস্টম পণ্য", "product", 0),
            ]
        },
        {
            "name": "Restaurant",
            "name_bn": "রেস্টুরেন্ট / খাবারের দোকান",
            "items": [
                ("Food Item", "খাবার", "product", 0),
                ("Drinks", "পানীয়", "product", 0),
                ("Other", "অন্যান্য", "product", 0),
            ]
        },
        {
            "name": "Printing Service",
            "name_bn": "প্রিন্টিং / কম্পিউটার / অনলাইন সার্ভিস সেন্টার",
            "items": [
                ("Printing", "প্রিন্ট", "service", 5),
                ("Color Printing", "কালার প্রিন্ট", "service", 15),
                ("Black & White Printing", "কালো-সাদা প্রিন্ট", "service", 5),
                ("Photocopy", "ফটোকপি", "service", 2),
                ("Scanning", "স্ক্যান", "service", 10),
                ("Online Application", "অনলাইন আবেদন", "service", 100),
                ("Birth Certificate Application", "জন্ম নিবন্ধন আবেদন", "service", 150),
                ("Passport Application", "পাসপোর্ট আবেদন", "service", 200),
                ("Job Application", "চাকরির আবেদন", "service", 100),
                ("University Application", "বিশ্ববিদ্যালয় আবেদন", "service", 150),
                ("Admission Application", "ভর্তি আবেদন", "service", 150),
                ("CV Creation", "CV তৈরি", "service", 150),
                ("Typing", "টাইপিং", "service", 50),
                ("Photo Editing", "ছবি এডিট", "service", 30),
                ("Lamination", "লেমিনেশন", "service", 20),
                ("Other Services", "অন্যান্য সেবা", "service", 0),
            ]
        },
    ]
    
    for cat_data in categories_data:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            cat = Category(name=cat_data["name"], name_bn=cat_data["name_bn"])
            db.add(cat)
            db.flush()
            for item in cat_data["items"]:
                ci = CategoryItem(
                    category_id=cat.id,
                    name=item[0],
                    name_bn=item[1],
                    type=item[2],
                    default_price=item[3],
                    unit="টি" if item[2] == "service" else "পিস"
                )
                db.add(ci)
    db.commit()

def seed_admin(db):
    admin_mobile = os.getenv("ADMIN_MOBILE", "01700000000")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")
    existing = db.query(User).filter(User.mobile == admin_mobile).first()
    if not existing:
        try:
            admin = User(
                name="অ্যাডমিন",
                mobile=admin_mobile,
                email="admin@smartinvoice.bd",
                password_hash=get_password_hash(admin_password),
                role=UserRole.ADMIN.value
            )
            db.add(admin)
            db.commit()
            print(f"Admin created: mobile={admin_mobile}")
        except Exception as e:
            print(f"Admin seed error: {e}")
            db.rollback()
    else:
        print("Admin already exists")

def run_seed():
    init_db()
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_admin(db)
        print("Seed completed successfully")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
