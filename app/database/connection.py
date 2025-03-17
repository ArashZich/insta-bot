# app/database/connection.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
import logging
from loguru import logger
import time

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)

# تلاش برای ایجاد موتور دیتابیس با تلاش‌های مجدد
max_retries = 5
retry_interval = 3

for attempt in range(max_retries):
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # بررسی اتصال قبل از استفاده
            pool_recycle=3600,   # بازیافت اتصال‌ها هر یک ساعت
            # زمان انتظار بیشتر برای اتصال
            connect_args={"connect_timeout": 15}
        )
        # تست اتصال
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info(f"اتصال به دیتابیس برقرار شد: {DATABASE_URL}")
        break
    except Exception as e:
        logger.error(
            f"خطا در اتصال به دیتابیس (تلاش {attempt+1}/{max_retries}): {e}")
        if attempt < max_retries - 1:  # اگر هنوز تلاش‌های بیشتری باقی مانده
            time.sleep(retry_interval)  # صبر قبل از تلاش مجدد
        else:
            logger.critical("نمی‌توان به دیتابیس متصل شد پس از چندین تلاش!")
            # ایجاد یک موتور دامی برای جلوگیری از خطاهای فاتال
            engine = create_engine("sqlite:///:memory:")
            logger.warning(
                "از دیتابیس حافظه موقت استفاده می‌شود - این فقط برای جلوگیری از خطاهای فاتال است!")

# ایجاد کلاس جلسه دیتابیس
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """ایجاد یک نشست دیتابیس با مدیریت خطا"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"خطا در استفاده از دیتابیس: {e}")
        db.rollback()  # بازگشت تراکنش در صورت بروز خطا
        raise
    finally:
        db.close()
