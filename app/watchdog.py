import time
import requests
import subprocess
import logging
from datetime import datetime

# راه‌اندازی لاگر
logging.basicConfig(
    filename="data/watchdog.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# تنظیمات
API_URL = "http://localhost:8000/health"
CHECK_INTERVAL = 300  # 5 دقیقه
MAX_FAILURES = 3


def check_service():
    """بررسی دسترسی به سرویس"""
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            logging.info("سرویس در دسترس است")
            return True
        else:
            logging.warning(
                f"سرویس کد وضعیت غیرعادی برگرداند: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"خطا در دسترسی به سرویس: {e}")
        return False


def restart_service():
    """راه‌اندازی مجدد سرویس"""
    try:
        logging.info("در حال راه‌اندازی مجدد سرویس...")
        # استفاده از Docker برای راه‌اندازی مجدد کانتینر
        subprocess.run(["docker", "restart", "instagram_bot"], check=True)
        logging.info("دستور راه‌اندازی مجدد ارسال شد")

        # زمان انتظار برای راه‌اندازی کامل
        time.sleep(30)
        return True
    except Exception as e:
        logging.error(f"خطا در راه‌اندازی مجدد سرویس: {e}")
        return False


def main():
    """حلقه اصلی بررسی و راه‌اندازی مجدد"""
    failures = 0

    logging.info("شروع مانیتورینگ سرویس")

    while True:
        if not check_service():
            failures += 1
            logging.warning(f"تعداد خطاهای متوالی: {failures}/{MAX_FAILURES}")

            if failures >= MAX_FAILURES:
                logging.error(
                    f"تعداد خطاها از حد مجاز ({MAX_FAILURES}) گذشت. راه‌اندازی مجدد...")
                restart_result = restart_service()

                if restart_result:
                    logging.info("سرویس با موفقیت راه‌اندازی مجدد شد")
                else:
                    logging.error("راه‌اندازی مجدد ناموفق بود")

                # ریست شمارنده
                failures = 0
        else:
            # ریست شمارنده در صورت دسترسی موفق
            failures = 0

        # انتظار تا بررسی بعدی
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
