import time
import asyncio
import uvicorn
import traceback
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from pathlib import Path
import logging

from app.database.init_db import initialize_database
from app.database.connection import get_db, engine
from app.database.models import Base
from app.bot.session_manager import SessionManager
from app.bot.interaction_manager import InteractionManager
from app.bot.follower_manager import FollowerManager
from app.bot.comment_manager import CommentManager
from app.api.router import router as api_router
from app.api.stats import router as stats_router
from app.api.interactions import router as interactions_router
from app.bot.automated_bot import AutomatedBot


# اطمینان از وجود دیتابیس و آماده‌سازی آن
print("در حال بررسی و آماده‌سازی دیتابیس...")
try:
    from app.database.init_db import initialize_database

    for attempt in range(3):  # سه بار تلاش
        if initialize_database():
            print("✅ دیتابیس با موفقیت آماده شد.")
            break
        elif attempt < 2:  # اگر هنوز تلاش‌های بیشتری باقی مانده
            print(
                f"⚠️ خطا در آماده‌سازی دیتابیس. تلاش مجدد ({attempt+2}/3)...")
            time.sleep(5)  # کمی صبر قبل از تلاش بعدی
        else:
            print("❌ خطا در آماده‌سازی دیتابیس پس از سه بار تلاش.")
            # ادامه اجرا - ممکن است دیتابیس بعداً در دسترس قرار گیرد
except Exception as e:
    print(f"❌ خطا در فرآیند آماده‌سازی دیتابیس: {e}")
    traceback.print_exc()
    import sys
    sys.exit(1)


# اطمینان از وجود پوشه data
Path("data").mkdir(exist_ok=True)

# تنظیم لاگر اصلی
logging.basicConfig(
    filename="data/fastapi.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

app = FastAPI(
    title="Instagram Bot API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# نمونه‌های کلاس‌های اصلی با مقادیر اولیه None
session_manager = None
interaction_manager = None
follower_manager = None
comment_manager = None
automated_bot = None

# میدلور برای مدیریت خطاها


@app.middleware("http")
async def handle_exceptions(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        if session_manager and session_manager.logger:
            session_manager.logger.error(f"خطای HTTP: {e}")
        logging.error(f"خطای HTTP: {e}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "خطای داخلی سرور. لطفا بعدا تلاش کنید."}
        )

# میدلور برای محدودیت نرخ درخواست‌ها (Rate Limiting)


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    # محدودیت ساده برای جلوگیری از فشار زیاد به سرور
    if request.url.path in ["/start", "/stop", "/auto-mode/on", "/auto-mode/off"]:
        time.sleep(1)  # تاخیر کوچک برای عملیات‌های مدیریتی
    return await call_next(request)

# افزودن endpoint سلامتی برای بررسی وضعیت


@app.get("/health")
def health_check():
    """بررسی وضعیت سلامت سرویس"""
    global session_manager

    db_status = "online"
    try:
        # بررسی اتصال به دیتابیس
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "offline"
        logging.error(f"خطا در اتصال به دیتابیس: {e}")

    bot_status = "online" if session_manager and session_manager.logged_in else "offline"
    auto_status = "running" if automated_bot and automated_bot.running else "stopped"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "bot": bot_status,
        "auto_mode": auto_status,
        "uptime": "available" if session_manager else "unavailable"
    }


# افزودن روترهای API
app.include_router(api_router, prefix="/api")
app.include_router(stats_router, prefix="/api/stats")
app.include_router(interactions_router, prefix="/api/interactions")

# تابع اجرای بات در پس‌زمینه


async def run_bot():
    global session_manager, interaction_manager, follower_manager, comment_manager, automated_bot

    try:
        # ایجاد نمونه‌های کلاس اصلی اگر وجود ندارند
        if not session_manager:
            session_manager = SessionManager()
            logging.info("نمونه SessionManager ایجاد شد")

        # لاگین به اینستاگرام - با منطق بهبود یافته
        login_attempts = 0
        max_attempts = 3

        while login_attempts < max_attempts:
            try:
                login_success = session_manager.login()
                if login_success:
                    session_manager.logger.info(
                        "✅ لاگین موفقیت‌آمیز به اینستاگرام")
                    logging.info("لاگین موفقیت‌آمیز به اینستاگرام")
                    break
                else:
                    login_attempts += 1
                    session_manager.logger.error(
                        f"❌ تلاش {login_attempts}/{max_attempts} لاگین ناموفق بود")
                    logging.error(
                        f"تلاش {login_attempts}/{max_attempts} لاگین ناموفق بود")
                    if login_attempts < max_attempts:
                        # انتظار بیشتر قبل از تلاش مجدد
                        await asyncio.sleep(60)
            except Exception as e:
                login_attempts += 1
                session_manager.logger.error(
                    f"❌ خطا در تلاش {login_attempts}/{max_attempts} لاگین: {e}")
                logging.error(
                    f"خطا در تلاش {login_attempts}/{max_attempts} لاگین: {e}")
                logging.error(traceback.format_exc())
                if login_attempts < max_attempts:
                    await asyncio.sleep(60)  # انتظار بیشتر قبل از تلاش مجدد

        if login_attempts >= max_attempts:
            session_manager.logger.error("❌ تمام تلاش‌های لاگین ناموفق بودند")
            logging.error("تمام تلاش‌های لاگین ناموفق بودند")
            return

        # ثبت شروع سشن در دیتابیس
        session_manager.record_session_start()

        # ایجاد نمونه‌های مدیر تعامل، فالو و کامنت
        if not interaction_manager:
            interaction_manager = InteractionManager(session_manager)
            logging.info("نمونه InteractionManager ایجاد شد")

        if not follower_manager:
            follower_manager = FollowerManager(
                session_manager, interaction_manager)
            logging.info("نمونه FollowerManager ایجاد شد")

        if not comment_manager:
            comment_manager = CommentManager(
                session_manager, interaction_manager)
            logging.info("نمونه CommentManager ایجاد شد")

        # ایجاد و شروع بات خودکار
        if not automated_bot:
            automated_bot = AutomatedBot(
                session_manager, interaction_manager, follower_manager, comment_manager)
            logging.info("نمونه AutomatedBot ایجاد شد")
            await automated_bot.start()
            logging.info("چرخه کاری خودکار بات شروع شد")

        session_manager.logger.info(
            "بات با موفقیت راه‌اندازی شد و در حال کار خودکار است")
        logging.info("بات با موفقیت راه‌اندازی شد و در حال کار خودکار است")
    except Exception as e:
        # ثبت خطای کلی
        if session_manager and session_manager.logger:
            session_manager.logger.error(f"خطای کلی در راه‌اندازی بات: {e}")
            session_manager.logger.error(
                f"Traceback: {traceback.format_exc()}")
        logging.error(f"خطای کلی در راه‌اندازی بات: {e}")
        logging.error(traceback.format_exc())

# مدیریت رهاسازی منابع هنگام خروج


@app.on_event("shutdown")
async def shutdown_event():
    global session_manager, automated_bot

    logging.info("در حال خروج از برنامه...")

    # توقف بات خودکار
    if automated_bot and automated_bot.running:
        try:
            await automated_bot.stop()
            logging.info("بات خودکار متوقف شد")
        except Exception as e:
            logging.error(f"خطا در توقف بات خودکار: {e}")

    # ثبت پایان سشن
    if session_manager and session_manager.logged_in:
        try:
            session_manager.record_session_end()
            logging.info("پایان سشن ثبت شد")
        except Exception as e:
            logging.error(f"خطا در ثبت پایان سشن: {e}")

# مسیرهای API اصلی


@app.get("/")
def read_root():
    return {
        "message": "Instagram Bot API is running",
        "version": "1.1.0",
        "status": "online",
        "docs": "/docs"
    }


@app.post("/start")
async def start_bot(background_tasks: BackgroundTasks):
    """راه‌اندازی بات"""
    global session_manager, automated_bot

    logging.info("درخواست راه‌اندازی بات دریافت شد")

    if session_manager and session_manager.logged_in:
        if automated_bot and automated_bot.running:
            logging.info("بات در حال اجرای خودکار است")
            return {"message": "بات در حال اجرای خودکار است", "status": "running"}
        elif automated_bot:
            await automated_bot.start()
            logging.info("چرخه کاری خودکار بات مجدداً شروع شد")
            return {"message": "چرخه کاری خودکار بات مجدداً شروع شد", "status": "started"}

    background_tasks.add_task(run_bot)
    logging.info("بات در حال راه‌اندازی و شروع کار خودکار است")
    return {"message": "بات در حال راه‌اندازی و شروع کار خودکار است", "status": "starting"}


@app.post("/stop")
async def stop_bot():
    """توقف بات"""
    global session_manager, automated_bot

    logging.info("درخواست توقف بات دریافت شد")

    if not session_manager or not session_manager.logged_in:
        logging.info("بات در حال اجرا نیست")
        return {"message": "بات در حال اجرا نیست", "status": "stopped"}

    # توقف بات خودکار
    if automated_bot and automated_bot.running:
        try:
            await automated_bot.stop()
            logging.info("بات خودکار متوقف شد")
        except Exception as e:
            logging.error(f"خطا در توقف بات خودکار: {e}")
            return {"message": f"خطا در توقف بات: {str(e)}", "status": "error"}

    # ثبت پایان سشن در دیتابیس
    try:
        session_manager.record_session_end()
        session_manager.logged_in = False
        logging.info("بات متوقف شد و پایان سشن ثبت شد")
    except Exception as e:
        logging.error(f"خطا در ثبت پایان سشن: {e}")
        return {"message": f"خطا در ثبت پایان سشن: {str(e)}", "status": "error"}

    return {"message": "بات متوقف شد", "status": "stopped"}


@app.get("/status")
def get_status():
    """دریافت وضعیت بات"""
    global session_manager, automated_bot

    logging.info("درخواست وضعیت بات دریافت شد")

    if not session_manager:
        return {
            "status": "stopped",
            "message": "بات راه‌اندازی نشده است",
            "details": {
                "time": datetime.now().isoformat()
            }
        }

    auto_status = "running" if (
        automated_bot and automated_bot.running) else "stopped"

    # اطلاعات آماری ساده
    stats = {
        "uptime": "نامشخص"
    }

    if hasattr(session_manager, 'logged_in_time'):
        uptime = datetime.now() - session_manager.logged_in_time
        stats["uptime"] = f"{uptime.total_seconds() / 3600:.1f} ساعت"

    return {
        "status": "running" if session_manager.logged_in else "stopped",
        "auto_mode": auto_status,
        "session_id": session_manager.session_id,
        "last_operation": session_manager.last_operation,
        "last_error": session_manager.last_error,
        "details": stats
    }

# تنظیم حالت خودکار بات


@app.post("/auto-mode/{state}")
async def set_auto_mode(state: str):
    """تنظیم حالت خودکار بات"""
    global session_manager, automated_bot

    logging.info(f"درخواست تنظیم حالت خودکار بات به {state} دریافت شد")

    if not session_manager or not session_manager.logged_in:
        logging.warning("بات در حال اجرا نیست")
        return {"message": "بات در حال اجرا نیست", "success": False}

    if not automated_bot:
        logging.warning("بات خودکار هنوز آماده نشده است")
        return {"message": "بات خودکار هنوز آماده نشده است", "success": False}

    if state.lower() == "on":
        if automated_bot.running:
            logging.info("بات از قبل در حالت خودکار است")
            return {"message": "بات از قبل در حالت خودکار است", "success": True}

        try:
            await automated_bot.start()
            logging.info("حالت خودکار بات فعال شد")
            return {"message": "حالت خودکار بات فعال شد", "success": True}
        except Exception as e:
            logging.error(f"خطا در فعال‌سازی حالت خودکار: {e}")
            return {"message": f"خطا در فعال‌سازی حالت خودکار: {str(e)}", "success": False}

    elif state.lower() == "off":
        if not automated_bot.running:
            logging.info("بات از قبل در حالت خودکار نیست")
            return {"message": "بات از قبل در حالت خودکار نیست", "success": True}

        try:
            await automated_bot.stop()
            logging.info("حالت خودکار بات غیرفعال شد")
            return {"message": "حالت خودکار بات غیرفعال شد", "success": True}
        except Exception as e:
            logging.error(f"خطا در غیرفعال‌سازی حالت خودکار: {e}")
            return {"message": f"خطا در غیرفعال‌سازی حالت خودکار: {str(e)}", "success": False}

    logging.warning(f"دستور نامعتبر حالت خودکار: {state}")
    return {"message": "دستور نامعتبر. از 'on' یا 'off' استفاده کنید", "success": False}

# راه‌اندازی مجدد اجباری


@app.post("/force-restart")
async def force_restart(background_tasks: BackgroundTasks):
    """راه‌اندازی مجدد اجباری بات"""
    global session_manager, automated_bot

    logging.info("درخواست راه‌اندازی مجدد اجباری بات دریافت شد")

    # توقف بات فعلی
    if automated_bot and automated_bot.running:
        try:
            await automated_bot.stop()
            logging.info("بات خودکار متوقف شد")
        except Exception as e:
            logging.error(f"خطا در توقف بات خودکار: {e}")

    # ثبت پایان سشن فعلی
    if session_manager and session_manager.logged_in:
        try:
            session_manager.record_session_end()
            logging.info("پایان سشن ثبت شد")
        except Exception as e:
            logging.error(f"خطا در ثبت پایان سشن: {e}")

    # بازنشانی نمونه‌ها
    session_manager = None
    interaction_manager = None
    follower_manager = None
    comment_manager = None
    automated_bot = None

    # شروع مجدد
    background_tasks.add_task(run_bot)
    logging.info("بات در حال راه‌اندازی مجدد است")

    return {"message": "بات در حال راه‌اندازی مجدد اجباری است", "status": "restarting"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000,
                reload=True, timeout_keep_alive=120)
