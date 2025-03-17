from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from loguru import logger
from typing import List, Dict, Any, Optional

from app.database.connection import get_db
from app.database.models import DailyStats

router = APIRouter()


@router.get("/daily")
def get_daily_stats(days: int = 7, db: Session = Depends(get_db)):
    """دریافت آمار روزانه بات در بازه زمانی مشخص با مدیریت خطای بهبود یافته"""
    try:
        date_limit = datetime.now() - timedelta(days=days)

        # بررسی جداول
        try:
            stats = db.query(DailyStats).filter(
                DailyStats.date >= date_limit
            ).order_by(DailyStats.date).all()
        except Exception as db_error:
            logger.error(f"خطا در دسترسی به جدول آمار روزانه: {db_error}")
            # بازگشت داده خالی به جای خطای 500
            return {
                "days": days,
                "stats": [],
                "message": "داده آماری موجود نیست یا خطایی در دسترسی به دیتابیس رخ داده است."
            }

        # تبدیل داده‌ها به فرمت مناسب
        result = []
        for stat in stats:
            result.append({
                "date": stat.date.strftime("%Y-%m-%d"),
                "likes": stat.likes_count,
                "comments": stat.comments_count,
                "follows": stat.follows_count,
                "unfollows": stat.unfollows_count,
                "story_views": stat.story_views_count,
                "dms": stat.dms_count,
                "total": stat.total_interactions,
                "success_rate": stat.success_rate
            })

        return {
            "days": days,
            "stats": result
        }
    except Exception as e:
        logger.error(f"خطا در API آمار روزانه: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # بازگرداندن پاسخ خالی به جای خطا
        return {
            "days": days,
            "stats": [],
            "error": "خطایی در پردازش داده‌های آماری رخ داده است."
        }


@router.get("/summary")
def get_stats_summary(db: Session = Depends(get_db)):
    """دریافت خلاصه آمار بات"""
    # آمار روز جاری
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_stats = db.query(DailyStats).filter(DailyStats.date == today).first()

    # آمار هفته جاری
    week_start = today - timedelta(days=today.weekday())
    week_stats = db.query(DailyStats).filter(
        DailyStats.date >= week_start).all()

    # آمار ماه جاری
    month_start = today.replace(day=1)
    month_stats = db.query(DailyStats).filter(
        DailyStats.date >= month_start).all()

    # جمع کردن آمار هفتگی
    week_totals = {
        "likes": 0,
        "comments": 0,
        "follows": 0,
        "unfollows": 0,
        "story_views": 0,
        "dms": 0,
        "total": 0
    }

    for stat in week_stats:
        week_totals["likes"] += stat.likes_count
        week_totals["comments"] += stat.comments_count
        week_totals["follows"] += stat.follows_count
        week_totals["unfollows"] += stat.unfollows_count
        week_totals["story_views"] += stat.story_views_count
        week_totals["dms"] += stat.dms_count
        week_totals["total"] += stat.total_interactions

    # جمع کردن آمار ماهانه
    month_totals = {
        "likes": 0,
        "comments": 0,
        "follows": 0,
        "unfollows": 0,
        "story_views": 0,
        "dms": 0,
        "total": 0
    }

    for stat in month_stats:
        month_totals["likes"] += stat.likes_count
        month_totals["comments"] += stat.comments_count
        month_totals["follows"] += stat.follows_count
        month_totals["unfollows"] += stat.unfollows_count
        month_totals["story_views"] += stat.story_views_count
        month_totals["dms"] += stat.dms_count
        month_totals["total"] += stat.total_interactions

    # ساخت خلاصه آمار
    return {
        "today": {
            "date": today.strftime("%Y-%m-%d"),
            "stats": today_stats.to_dict() if today_stats else {
                "likes_count": 0,
                "comments_count": 0,
                "follows_count": 0,
                "unfollows_count": 0,
                "story_views_count": 0,
                "dms_count": 0,
                "total_interactions": 0,
                "success_rate": 0
            }
        },
        "this_week": {
            "start_date": week_start.strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d"),
            "stats": week_totals
        },
        "this_month": {
            "start_date": month_start.strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d"),
            "stats": month_totals
        }
    }
