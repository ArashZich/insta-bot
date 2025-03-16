from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.database.connection import get_db
from app.database.models import Interaction, DailyStats

router = APIRouter()


@router.get("/stats/daily")
def get_daily_stats(days: int = 7, db: Session = Depends(get_db)):
    """دریافت آمار روزانه بات"""
    date_limit = datetime.now() - timedelta(days=days)

    stats = db.query(DailyStats).filter(
        DailyStats.date >= date_limit
    ).order_by(DailyStats.date).all()

    return {
        "days": days,
        "stats": [
            {
                "date": stat.date.strftime("%Y-%m-%d"),
                "likes": stat.likes_count,
                "comments": stat.comments_count,
                "follows": stat.follows_count,
                "unfollows": stat.unfollows_count,
                "story_views": stat.story_views_count,
                "dms": stat.dms_count,
                "total": stat.total_interactions,
                "success_rate": stat.success_rate
            }
            for stat in stats
        ]
    }


@router.get("/stats/weekly")
def get_weekly_stats(weeks: int = 4, db: Session = Depends(get_db)):
    """دریافت آمار هفتگی بات"""
    date_limit = datetime.now() - timedelta(weeks=weeks)

    # دریافت آمار روزانه
    daily_stats = db.query(DailyStats).filter(
        DailyStats.date >= date_limit
    ).order_by(DailyStats.date).all()

    # تبدیل به آمار هفتگی
    weekly_stats = {}

    for stat in daily_stats:
        # تعیین شماره هفته و سال
        year, week, _ = stat.date.isocalendar()
        week_key = f"{year}-W{week:02d}"

        if week_key not in weekly_stats:
            weekly_stats[week_key] = {
                "week": week_key,
                "likes": 0,
                "comments": 0,
                "follows": 0,
                "unfollows": 0,
                "story_views": 0,
                "dms": 0,
                "total": 0,
                "days_count": 0
            }

        # جمع کردن آمار
        weekly_stats[week_key]["likes"] += stat.likes_count
        weekly_stats[week_key]["comments"] += stat.comments_count
        weekly_stats[week_key]["follows"] += stat.follows_count
        weekly_stats[week_key]["unfollows"] += stat.unfollows_count
        weekly_stats[week_key]["story_views"] += stat.story_views_count
        weekly_stats[week_key]["dms"] += stat.dms_count
        weekly_stats[week_key]["total"] += stat.total_interactions
        weekly_stats[week_key]["days_count"] += 1

    # تبدیل به لیست
    result = list(weekly_stats.values())

    # مرتب‌سازی بر اساس هفته
    result.sort(key=lambda x: x["week"])

    return {
        "weeks": weeks,
        "stats": result
    }


@router.get("/stats/monthly")
def get_monthly_stats(months: int = 6, db: Session = Depends(get_db)):
    """دریافت آمار ماهیانه بات"""
    date_limit = datetime.now() - timedelta(days=30 * months)

    # دریافت آمار روزانه
    daily_stats = db.query(DailyStats).filter(
        DailyStats.date >= date_limit
    ).order_by(DailyStats.date).all()

    # تبدیل به آمار ماهیانه
    monthly_stats = {}

    for stat in daily_stats:
        # تعیین ماه و سال
        month_key = f"{stat.date.year}-{stat.date.month:02d}"

        if month_key not in monthly_stats:
            monthly_stats[month_key] = {
                "month": month_key,
                "likes": 0,
                "comments": 0,
                "follows": 0,
                "unfollows": 0,
                "story_views": 0,
                "dms": 0,
                "total": 0,
                "days_count": 0
            }

        # جمع کردن آمار
        monthly_stats[month_key]["likes"] += stat.likes_count
        monthly_stats[month_key]["comments"] += stat.comments_count
        monthly_stats[month_key]["follows"] += stat.follows_count
        monthly_stats[month_key]["unfollows"] += stat.unfollows_count
        monthly_stats[month_key]["story_views"] += stat.story_views_count
        monthly_stats[month_key]["dms"] += stat.dms_count
        monthly_stats[month_key]["total"] += stat.total_interactions
        monthly_stats[month_key]["days_count"] += 1

    # تبدیل به لیست
    result = list(monthly_stats.values())

    # مرتب‌سازی بر اساس ماه
    result.sort(key=lambda x: x["month"])

    return {
        "months": months,
        "stats": result
    }


@router.get("/interactions")
def get_interactions(limit: int = 100, offset: int = 0, type: Optional[str] = None, db: Session = Depends(get_db)):
    """دریافت تاریخچه تعاملات بات"""
    query = db.query(Interaction)

    # فیلتر بر اساس نوع تعامل
    if type:
        query = query.filter(Interaction.interaction_type == type)

    # مرتب‌سازی بر اساس زمان ایجاد (نزولی)
    query = query.order_by(Interaction.created_at.desc())

    # اعمال محدودیت و آفست
    total = query.count()
    interactions = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "interactions": [
            {
                "id": interaction.id,
                "type": interaction.interaction_type,
                "target_username": interaction.target_user_username,
                "target_media": interaction.target_media_shortcode,
                "content": interaction.content,
                "created_at": interaction.created_at.isoformat(),
                "success": interaction.success,
                "error": interaction.error
            }
            for interaction in interactions
        ]
    }


@router.get("/interactions/stats")
def get_interactions_stats(days: int = 30, db: Session = Depends(get_db)):
    """دریافت آمار تعاملات بات"""
    date_limit = datetime.now() - timedelta(days=days)

    # تعداد کل تعاملات
    total_count = db.query(Interaction).filter(
        Interaction.created_at >= date_limit
    ).count()

    # تعداد تعاملات موفق
    success_count = db.query(Interaction).filter(
        Interaction.created_at >= date_limit,
        Interaction.success == True
    ).count()

    # تعداد بر اساس نوع
    types = ["like", "comment", "follow", "unfollow", "view_story", "dm"]
    type_counts = {}

    for interaction_type in types:
        count = db.query(Interaction).filter(
            Interaction.created_at >= date_limit,
            Interaction.interaction_type == interaction_type
        ).count()

        success_count_type = db.query(Interaction).filter(
            Interaction.created_at >= date_limit,
            Interaction.interaction_type == interaction_type,
            Interaction.success == True
        ).count()

        type_counts[interaction_type] = {
            "total": count,
            "success": success_count_type,
            "success_rate": (success_count_type / count * 100) if count > 0 else 0
        }

    return {
        "days": days,
        "total": total_count,
        "success": success_count,
        "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
        "by_type": type_counts
    }
