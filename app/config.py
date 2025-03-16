import os
import random
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# تنظیمات اینستاگرام
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# تنظیمات دیتابیس
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@db:5432/instagram_bot")

# تنظیمات رفتار انسانی ساده
# تاخیر بین عملیات‌ها (ثانیه)
MIN_ACTION_DELAY = 15
MAX_ACTION_DELAY = 40

# تاخیر طولانی تصادفی برای استراحت (دقیقه)
MIN_BREAK_TIME = 8
MAX_BREAK_TIME = 20

# احتمال استراحت طولانی بین عملیات‌ها (0 تا 1)
LONG_BREAK_PROBABILITY = 0.08

# تعداد عملیات پیش از استراحت اجباری
MIN_ACTIONS_BEFORE_BREAK = 5
MAX_ACTIONS_BEFORE_BREAK = 15

# محدودیت‌های تعامل روزانه
DAILY_LIKE_LIMIT = 150
DAILY_COMMENT_LIMIT = 20
DAILY_FOLLOW_LIMIT = 50
DAILY_UNFOLLOW_LIMIT = 40
DAILY_DM_LIMIT = 15

# مسیر فایل‌های دیتا
COMMENTS_FILE = "data/comments.json"
HASHTAGS_FILE = "data/hashtags.json"

# تنظیمات اولویت‌بندی فعالیت‌ها (0 تا 100)
ACTIVITY_WEIGHTS = {
    "like": 70,           # لایک کردن
    "comment": 50,        # کامنت گذاشتن (کاهش یافته به دلیل خطاها)
    "follow": 40,         # فالو کردن
    "unfollow": 30,       # آنفالو کردن
    "view_story": 70,     # دیدن استوری
    "dm": 30              # ارسال پیام مستقیم (کاهش یافته)
}
