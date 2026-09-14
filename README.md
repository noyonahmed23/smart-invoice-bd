# স্মার্ট ইনভয়েস জেনারেটর (Smart Invoice Generator)

বাংলাদেশের দোকান ও সার্ভিস ব্যবসার জন্য সম্পূর্ণ বাংলা ইন্টারফেসসহ প্রফেশনাল ইনভয়েস জেনারেশন প্ল্যাটফর্ম।

## বৈশিষ্ট্য

- সম্পূর্ণ বাংলা UI (Noto Sans Bengali ফন্ট)
- ইউজার রেজিস্ট্রেশন / লগইন
- দোকান প্রোফাইল ম্যানেজমেন্ট
- ক্যাটাগরি ভিত্তিক ডিফল্ট পণ্য/সেবা (কম্পিউটার, মোবাইল, ফার্মেসি, মুদি, পোশাক, রেস্টুরেন্ট, প্রিন্টিং)
- পণ্য/সেবা কাস্টমাইজেশন
- মাসিক ৳৫০ সাবস্ক্রিপশন (বিকাশ ম্যানুয়াল পেমেন্ট)
- অ্যাডমিন পেমেন্ট অনুমোদন
- সীমাহীন ইনভয়েস তৈরি
- প্রিন্ট-ফ্রেন্ডলি / PDF ইনভয়েস
- অ্যাডমিন প্যানেল
- রোল-ভিত্তিক সিকিউরিটি

## ইনস্টলেশন ও চালানো (লোকাল)

```bash
cd smart-invoice-bd
pip install -r requirements.txt
python run.py
```

ব্রাউজারে খুলুন: http://localhost:8000

## Render.com এ ডিপ্লয় করার ধাপ

1. এই পুরো ফোল্ডার GitHub এ `smart-invoice-bd` নামে Repository তৈরি করে আপলোড করুন।
2. [render.com](https://render.com) এ গিয়ে GitHub দিয়ে সাইন ইন করুন।
3. **New +** → **Web Service** সিলেক্ট করুন।
4. আপনার `smart-invoice-bd` Repository সিলেক্ট করুন।
5. সেটিংস:
   - **Name**: smart-invoice (যেকোনো নাম)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run.py`
   - **Instance Type**: Free
6. Environment Variables (ঐচ্ছিক):
   - `ADMIN_MOBILE` = আপনার মোবাইল
   - `ADMIN_PASSWORD` = শক্তিশালী পাসওয়ার্ড
   - `SECRET_KEY` = লম্বা র‍্যান্ডম টেক্সট
7. **Create Web Service** ক্লিক করুন।

কিছুক্ষণ পর Render একটি লিংক দেবে (যেমন: https://smart-invoice.onrender.com)

## অ্যাডমিন লগইন

- মোবাইল: `01700000000`
- পাসওয়ার্ড: `Admin@SmartInvoice2026`

পরিবেশ ভেরিয়েবল দিয়ে পরিবর্তন করুন:
```
export ADMIN_MOBILE=01XXXXXXXXX
export ADMIN_PASSWORD=your-secure-password
export SECRET_KEY=your-secret-key
```

## ওয়ার্কফ্লো

1. নিবন্ধন → দোকান তথ্য + ক্যাটাগরি নির্বাচন
2. ডিফল্ট পণ্য/সেবা অটো লোড
3. বিকাশ 01351230609 এ ৳৫০ পাঠিয়ে ট্রানজেকশন আইডি জমা
4. অ্যাডমিন অনুমোদন → ৩০ দিন সক্রিয়
5. ইনভয়েস তৈরি → প্রিন্ট/PDF

## প্রযুক্তি

- FastAPI + SQLAlchemy + SQLite
- Jinja2 Templates + Tailwind CSS
- JWT Cookie Authentication
- bcrypt Password Hashing

## নোট

- প্রোডাকশনে SQLite এর পরিবর্তে PostgreSQL ব্যবহার করুন
- SECRET_KEY এবং অ্যাডমিন পাসওয়ার্ড পরিবর্তন করুন
- আপলোড ফোল্ডার সুরক্ষিত রাখুন
