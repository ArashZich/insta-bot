# app/database/init_db.py

import os
import time
import psycopg2
from loguru import logger
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.database.models import Base


def wait_for_db(max_retries=30, retry_interval=5):
    """انتظار برای آماده شدن سرور دیتابیس"""
    # ابتدا به دیتابیس پیش‌فرض postgres متصل می‌شویم
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")

    # تنظیم URL برای اتصال به postgres
    parts = db_url.split('/')
    postgres_db_url = '/'.join(parts[:-1] + ['postgres'])

    logger.info(f"در حال بررسی اتصال به سرور دیتابیس: {postgres_db_url}")

    retries = 0
    while retries < max_retries:
        try:
            logger.info(
                f"تلاش برای اتصال به سرور دیتابیس ({retries + 1}/{max_retries})...")
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


def create_database_if_not_exists():
    """ایجاد دیتابیس اگر وجود نداشته باشد"""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/instagram_bot")

    # استخراج نام دیتابیس و اطلاعات اتصال
    parts = db_url.split('/')
    db_name = parts[-1]
    postgres_url = '/'.join(parts[:-1] + ['postgres'])

    logger.info(f"بررسی وجود دیتابیس {db_name}...")

    try:
        # اتصال به دیتابیس پیش‌فرض postgres
        conn = psycopg2.connect(postgres_url)
        conn.autocommit = True
        cursor = conn.cursor()

        # بررسی وجود دیتابیس
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone() is not None

        if not exists:
            logger.info(f"دیتابیس {db_name} وجود ندارد. در حال ایجاد...")
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


def check_tables(engine):
    """بررسی وجود تمام جداول مورد نیاز"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ["bot_sessions", "interactions", "daily_stats"]

        missing_tables = [
            table for table in required_tables if table not in existing_tables]

        if missing_tables:
            logger.info(f"جداول زیر وجود ندارند: {missing_tables}")
            return False

        logger.info("✅ تمام جداول مورد نیاز وجود دارند.")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در بررسی جداول: {e}")
        return False


def create_tables(engine):
    """ایجاد تمام جداول مورد نیاز"""
    try:
        logger.info("در حال ایجاد جداول...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ جداول با موفقیت ایجاد شدند.")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد جداول: {e}")
        import traceback
        logger.error(f"جزئیات خطا: {traceback.format_exc()}")
        return False


def initialize_database():
    """آماده‌سازی کامل دیتابیس"""
    # بررسی آماده بودن سرور دیتابیس
    if not wait_for_db():
        logger.error(
            "سرور دیتابیس در دسترس نیست. نمی‌توان دیتابیس را آماده کرد.")
        return False

    # ایجاد دیتابیس اگر وجود نداشته باشد
    if not create_database_if_not_exists():
        logger.error("خطا در ایجاد دیتابیس. نمی‌توان ادامه داد.")
        return False

    # اتصال به دیتابیس
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/instagram_bot")
    try:
        engine = create_engine(db_url)

        # بررسی وجود جداول
        if not check_tables(engine):
            logger.info("جداول مورد نیاز وجود ندارند. در حال ایجاد...")
            if not create_tables(engine):
                logger.error("خطا در ایجاد جداول. نمی‌توان ادامه داد.")
                return False

        logger.info("✅ دیتابیس با موفقیت آماده شد.")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در آماده‌سازی دیتابیس: {e}")
        import traceback
        logger.error(f"جزئیات خطا: {traceback.format_exc()}")
        return False
