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
MIN_ACTION_DELAY = 2
MAX_ACTION_DELAY = 15

# تاخیر طولانی تصادفی برای استراحت (دقیقه)
MIN_BREAK_TIME = 5
MAX_BREAK_TIME = 25

# احتمال استراحت طولانی بین عملیات‌ها (0 تا 1)
LONG_BREAK_PROBABILITY = 0.05

# تعداد عملیات پیش از استراحت اجباری
MIN_ACTIONS_BEFORE_BREAK = 10
MAX_ACTIONS_BEFORE_BREAK = 25

# مسیر فایل‌های دیتا
COMMENTS_FILE = "data/comments.json"
HASHTAGS_FILE = "data/hashtags.json"
