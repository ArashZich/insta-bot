import time
import random
import uuid
import json
from datetime import datetime
from loguru import logger
import os
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
    logger.remove()
    logger.add(
        "data/bot.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
    )
    logger.add(
        lambda msg: print(msg),
        colorize=True,
        format="{time:HH:mm:ss} | <level>{level}</level> | {message}",
        level="INFO",
    )
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
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path, data):
    """ذخیره داده در فایل JSON"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
