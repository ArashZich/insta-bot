import time
import random
import uuid
import json
from datetime import datetime
from loguru import logger
import os
import sys
from pathlib import Path
from app.config import (
    MIN_ACTION_DELAY,
    MAX_ACTION_DELAY,
    MIN_BREAK_TIME,
    MAX_BREAK_TIME,
    LONG_BREAK_PROBABILITY,
    MIN_ACTIONS_BEFORE_BREAK,
    MAX_ACTIONS_BEFORE_BREAK
)


def setup_logger():
    """تنظیم لاگر"""
    # حذف همه هندلرهای فعلی
    logger.remove()

    # مطمئن شوید پوشه data وجود دارد
    Path("data").mkdir(exist_ok=True)

    # افزودن هندلر فایل با سطح DEBUG
    logger.add(
        "data/bot.log",
        rotation="500 MB",  # افزایش سایز فایل لاگ
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        backtrace=True,  # نمایش traceback کامل
        diagnose=True,   # اطلاعات تشخیصی بیشتر
    )

    # افزودن هندلر کنسول با سطح INFO
    logger.add(
        sys.stdout,
        colorize=True,
        format="{time:HH:mm:ss} | <level>{level}</level> | {message}",
        level="INFO",
        backtrace=True,
        diagnose=True,
    )

    # آزمایش لاگر
    logger.info("Logger initialized successfully")

    return logger


def generate_session_id():
    """ایجاد شناسه منحصر به فرد برای هر جلسه"""
    return str(uuid.uuid4())


def random_delay():
    """ایجاد تاخیر تصادفی بین عملیات‌ها"""
    delay = random.uniform(MIN_ACTION_DELAY, MAX_ACTION_DELAY)
    time.sleep(delay)
    return delay


def should_take_break():
    """تصمیم‌گیری برای استراحت طولانی تصادفی"""
    return random.random() < LONG_BREAK_PROBABILITY


def take_random_break(logger=None):
    """اعمال استراحت تصادفی طولانی"""
    break_time = random.randint(MIN_BREAK_TIME * 60, MAX_BREAK_TIME * 60)
    if logger:
        logger.info(f"در حال استراحت به مدت {break_time // 60} دقیقه...")
    time.sleep(break_time)
    return break_time


def get_actions_before_break():
    """تعیین تعداد عملیات قبل از استراحت اجباری"""
    return random.randint(MIN_ACTIONS_BEFORE_BREAK, MAX_ACTIONS_BEFORE_BREAK)


def load_json_file(file_path):
    """خواندن فایل JSON"""
    # اطمینان از وجود فایل
    if not os.path.exists(file_path):
        # ایجاد پوشه والد در صورت نیاز
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # ایجاد فایل خالی
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"خطا در خواندن فایل JSON: {file_path}")
        return []


def save_json_file(file_path, data):
    """ذخیره داده در فایل JSON"""
    # اطمینان از وجود پوشه والد
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
