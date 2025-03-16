import time
import asyncio
import uvicorn
import traceback
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pathlib import Path

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

# ایجاد جداول دیتابیس اگر وجود ندارند
Base.metadata.create_all(bind=engine)

# اطمینان از وجود پوشه data
Path("data").mkdir(exist_ok=True)

app = FastAPI(title="Instagram Bot API")

# افزودن روترهای API
app.include_router(api_router, prefix="/api")
app.include_router(stats_router, prefix="/api/stats")
app.include_router(interactions_router, prefix="/api/interactions")

# نمونه‌های کلاس‌های اصلی
session_manager = None
interaction_manager = None
follower_manager = None
comment_manager = None
automated_bot = None

# تابع اجرای بات در پس‌زمینه


async def run_bot():
    global session_manager, interaction_manager, follower_manager, comment_manager, automated_bot

    # ایجاد نمونه‌های کلاس اصلی اگر وجود ندارند
    if not session_manager:
        session_manager = SessionManager()

    # لاگین به اینستاگرام - با منطق بهبود یافته
    login_attempts = 0
    max_attempts = 3

    while login_attempts < max_attempts:
        try:
            login_success = session_manager.login()
            if login_success:
                session_manager.logger.info(
                    "✅ لاگین موفقیت‌آمیز به اینستاگرام")
                break
            else:
                login_attempts += 1
                session_manager.logger.error(
                    f"❌ تلاش {login_attempts}/{max_attempts} لاگین ناموفق بود")
                if login_attempts < max_attempts:
                    await asyncio.sleep(30)  # انتظار قبل از تلاش مجدد
        except Exception as e:
            login_attempts += 1
            session_manager.logger.error(
                f"❌ خطا در تلاش {login_attempts}/{max_attempts} لاگین: {e}")
            session_manager.logger.error(
                f"Traceback: {traceback.format_exc()}")
            if login_attempts < max_attempts:
                await asyncio.sleep(30)  # انتظار قبل از تلاش مجدد

    if login_attempts >= max_attempts:
        session_manager.logger.error("❌ تمام تلاش‌های لاگین ناموفق بودند")
        return

    # ثبت شروع سشن در دیتابیس
    session_manager.record_session_start()

    # ایجاد نمونه‌های مدیر تعامل، فالو و کامنت
    if not interaction_manager:
        interaction_manager = InteractionManager(session_manager)

    if not follower_manager:
        follower_manager = FollowerManager(
            session_manager, interaction_manager)

    if not comment_manager:
        comment_manager = CommentManager(session_manager, interaction_manager)

    # ایجاد و شروع بات خودکار
    if not automated_bot:
        automated_bot = AutomatedBot(
            session_manager, interaction_manager, follower_manager, comment_manager)
        await automated_bot.start()

    session_manager.logger.info(
        "بات با موفقیت راه‌اندازی شد و در حال کار خودکار است")

# مسیرهای API اصلی


@app.get("/")
def read_root():
    return {"message": "Instagram Bot API is running"}


@app.post("/start")
async def start_bot(background_tasks: BackgroundTasks):
    """راه‌اندازی بات"""
    global session_manager, automated_bot

    if session_manager and session_manager.logged_in:
        if automated_bot and automated_bot.running:
            return {"message": "بات در حال اجرای خودکار است"}
        elif automated_bot:
            await automated_bot.start()
            return {"message": "چرخه کاری خودکار بات مجدداً شروع شد"}

    background_tasks.add_task(run_bot)
    return {"message": "بات در حال راه‌اندازی و شروع کار خودکار است"}


@app.post("/stop")
async def stop_bot():
    """توقف بات"""
    global session_manager, automated_bot

    if not session_manager or not session_manager.logged_in:
        return {"message": "بات در حال اجرا نیست"}

    # توقف بات خودکار
    if automated_bot and automated_bot.running:
        await automated_bot.stop()

    # ثبت پایان سشن در دیتابیس
    session_manager.record_session_end()
    session_manager.logged_in = False

    return {"message": "بات متوقف شد"}


@app.get("/status")
def get_status():
    """دریافت وضعیت بات"""
    global session_manager, automated_bot

    if not session_manager:
        return {
            "status": "stopped",
            "message": "بات راه‌اندازی نشده است"
        }

    auto_status = "running" if (
        automated_bot and automated_bot.running) else "stopped"

    return {
        "status": "running" if session_manager.logged_in else "stopped",
        "auto_mode": auto_status,
        "session_id": session_manager.session_id,
        "last_operation": session_manager.last_operation,
        "last_error": session_manager.last_error
    }

# اضافه کردن مسیر جدید برای روشن/خاموش کردن حالت خودکار


@app.post("/auto-mode/{state}")
async def set_auto_mode(state: str):
    """تنظیم حالت خودکار بات"""
    global session_manager, automated_bot

    if not session_manager or not session_manager.logged_in:
        return {"message": "بات در حال اجرا نیست", "success": False}

    if not automated_bot:
        return {"message": "بات خودکار هنوز آماده نشده است", "success": False}

    if state.lower() == "on":
        if automated_bot.running:
            return {"message": "بات از قبل در حالت خودکار است", "success": True}
        await automated_bot.start()
        return {"message": "حالت خودکار بات فعال شد", "success": True}

    elif state.lower() == "off":
        if not automated_bot.running:
            return {"message": "بات از قبل در حالت خودکار نیست", "success": True}
        await automated_bot.stop()
        return {"message": "حالت خودکار بات غیرفعال شد", "success": True}

    return {"message": "دستور نامعتبر. از 'on' یا 'off' استفاده کنید", "success": False}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
