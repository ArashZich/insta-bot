import time
import asyncio
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database.connection import get_db, engine
from app.database.models import Base
from app.bot.session_manager import SessionManager
from app.bot.interaction_manager import InteractionManager
from app.bot.follower_manager import FollowerManager
from app.bot.comment_manager import CommentManager
from app.api.router import router as api_router

# ایجاد جداول دیتابیس اگر وجود ندارند
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Instagram Bot API")

# افزودن روترهای API
app.include_router(api_router, prefix="/api")

# نمونه‌های کلاس‌های اصلی
session_manager = None
interaction_manager = None
follower_manager = None
comment_manager = None

# تابع اجرای بات در پس‌زمینه


async def run_bot():
    global session_manager, interaction_manager, follower_manager, comment_manager

    # ایجاد نمونه‌های کلاس اصلی اگر وجود ندارند
    if not session_manager:
        session_manager = SessionManager()

    # لاگین به اینستاگرام
    if not session_manager.login():
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

    session_manager.logger.info("بات با موفقیت راه‌اندازی شد")

# مسیرهای API اصلی


@app.get("/")
def read_root():
    return {"message": "Instagram Bot API is running"}


@app.post("/start")
async def start_bot(background_tasks: BackgroundTasks):
    """راه‌اندازی بات"""
    global session_manager

    if session_manager and session_manager.logged_in:
        return {"message": "بات در حال اجرا است"}

    background_tasks.add_task(run_bot)
    return {"message": "بات در حال راه‌اندازی است"}


@app.post("/stop")
def stop_bot():
    """توقف بات"""
    global session_manager

    if not session_manager or not session_manager.logged_in:
        return {"message": "بات در حال اجرا نیست"}

    # ثبت پایان سشن در دیتابیس
    session_manager.record_session_end()
    session_manager.logged_in = False

    return {"message": "بات متوقف شد"}


@app.get("/status")
def get_status():
    """دریافت وضعیت بات"""
    global session_manager

    if not session_manager:
        return {
            "status": "stopped",
            "message": "بات راه‌اندازی نشده است"
        }

    return {
        "status": "running" if session_manager.logged_in else "stopped",
        "session_id": session_manager.session_id,
        "last_operation": session_manager.last_operation,
        "last_error": session_manager.last_error
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
