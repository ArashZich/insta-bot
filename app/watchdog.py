import time
import requests
import subprocess
import logging
import socket
from datetime import datetime

# راه‌اندازی لاگر
logging.basicConfig(
    filename="data/watchdog.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# تنظیمات
API_URL = "http://app:8000/health"  # آدرس سرویس در شبکه Docker
CHECK_INTERVAL = 60  # کاهش به 1 دقیقه
MAX_FAILURES = 3
INITIAL_DELAY = 120  # تاخیر اولیه 2 دقیقه برای راه‌اندازی کامل سرویس‌ها


def check_service_basic():
    """بررسی اولیه دسترسی به سرویس با TCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('app', 8000))
        sock.close()

        if result == 0:
            logging.info("پورت سرویس در دسترس است")
            return True
        else:
            logging.warning(f"پورت سرویس در دسترس نیست، کد خطا: {result}")
            return False
    except Exception as e:
        logging.error(f"خطا در بررسی اولیه سرویس: {e}")
        return False


def check_service():
    """بررسی دسترسی به سرویس"""
    try:
        # ابتدا بررسی اولیه
        if not check_service_basic():
            return False

        # سپس بررسی API
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            logging.info("سرویس در دسترس است")
            try:
                data = response.json()
                logging.info(f"وضعیت سرویس: {data.get('status', 'نامشخص')}")
            except:
                pass
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
        logging.info("انتظار 60 ثانیه برای راه‌اندازی کامل...")
        time.sleep(60)
        return True
    except Exception as e:
        logging.error(f"خطا در راه‌اندازی مجدد سرویس: {e}")
        return False


def main():
    """حلقه اصلی بررسی و راه‌اندازی مجدد"""
    failures = 0

    logging.info("شروع مانیتورینگ سرویس")
    logging.info(f"تاخیر اولیه {INITIAL_DELAY} ثانیه...")
    time.sleep(INITIAL_DELAY)  # تاخیر اولیه برای راه‌اندازی سرویس‌ها

    while True:
        try:
            if not check_service():
                failures += 1
                logging.warning(
                    f"تعداد خطاهای متوالی: {failures}/{MAX_FAILURES}")

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
        except Exception as e:
            logging.error(f"خطا در چرخه اصلی واچ‌داگ: {e}")
            time.sleep(60)  # استراحت کوتاه در صورت خطا


if __name__ == "__main__":
    main()
