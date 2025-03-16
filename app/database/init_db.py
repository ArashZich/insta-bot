# app/database/init_db.py

import os
import time
import psycopg2
from loguru import logger


def wait_for_db(max_retries=20, retry_interval=10):
    """انتظار برای آماده شدن دیتابیس"""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")

    # تلاش اتصال به دیتابیس postgres به جای instagram_bot
    parts = db_url.split('/')
    postgres_db_url = '/'.join(parts[:-1] + ['postgres'])

    retries = 0
    while retries < max_retries:
        try:
            logger.info(
                f"تلاش برای اتصال به سرور دیتابیس ({retries + 1}/{max_retries})...")
            # اتصال به دیتابیس پیش‌فرض postgres برای بررسی دسترسی به سرور
            conn = psycopg2.connect(postgres_db_url)
            conn.close()
            logger.info("✅ اتصال به سرور دیتابیس موفقیت‌آمیز بود.")
            return True
        except psycopg2.OperationalError as e:
            logger.warning(
                f"⚠️ سرور دیتابیس هنوز آماده نیست. خطا: {str(e)[:100]}... انتظار {retry_interval} ثانیه...")
            retries += 1
            time.sleep(retry_interval)

    logger.error(
        f"❌ نمی‌توان به سرور دیتابیس متصل شد پس از {max_retries} تلاش.")
    return False


def ensure_database_exists():
    """اطمینان از وجود دیتابیس"""
    db_conn = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/instagram_bot")

    # استخراج نام دیتابیس و اطلاعات اتصال
    db_parts = db_conn.split("/")
    db_name = db_parts[-1]
    # اتصال به دیتابیس پیش‌فرض postgres
    db_server_conn = "/".join(db_parts[:-1]) + "/postgres"

    try:
        logger.info(f"بررسی وجود دیتابیس {db_name}...")

        # اتصال به دیتابیس postgres برای بررسی وجود دیتابیس ما
        conn = psycopg2.connect(db_server_conn)
        conn.autocommit = True
        cursor = conn.cursor()

        # بررسی وجود دیتابیس
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        database_exists = cursor.fetchone() is not None

        if not database_exists:
            logger.info(f"دیتابیس {db_name} یافت نشد. در حال ایجاد...")
            # ایجاد دیتابیس جدید
            cursor.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"✅ دیتابیس {db_name} با موفقیت ایجاد شد.")
        else:
            logger.info(f"✅ دیتابیس {db_name} از قبل وجود دارد.")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ خطا در بررسی/ایجاد دیتابیس: {e}")
        import traceback
        logger.error(f"جزئیات خطا: {traceback.format_exc()}")
        return False


def initialize_database():
    """آماده‌سازی کامل دیتابیس"""
    if wait_for_db():
        return ensure_database_exists()
    return False
