from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.database.connection import get_db
from app.database.models import Interaction

router = APIRouter()


@router.get("/recent")
def get_recent_interactions(limit: int = 50, db: Session = Depends(get_db)):
    """دریافت تعاملات اخیر بات"""
    interactions = db.query(Interaction).order_by(
        Interaction.created_at.desc()
    ).limit(limit).all()

    # تبدیل داده‌ها به فرمت مناسب
    result = []
    for interaction in interactions:
        result.append({
            "id": interaction.id,
            "type": interaction.interaction_type,
            "target_username": interaction.target_user_username,
            "target_media_shortcode": interaction.target_media_shortcode,
            "content": interaction.content,
            "created_at": interaction.created_at.isoformat(),
            "success": interaction.success,
            "error": interaction.error
        })

    return {
        "limit": limit,
        "interactions": result
    }


@router.get("/by-type/{interaction_type}")
def get_interactions_by_type(interaction_type: str, limit: int = 50, db: Session = Depends(get_db)):
    """دریافت تعاملات بر اساس نوع"""
    # بررسی معتبر بودن نوع تعامل
    valid_types = ["like", "comment", "follow", "unfollow", "view_story", "dm"]
    if interaction_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"نوع تعامل نامعتبر. گزینه‌های مجاز: {', '.join(valid_types)}")

    interactions = db.query(Interaction).filter(
        Interaction.interaction_type == interaction_type
    ).order_by(
        Interaction.created_at.desc()
    ).limit(limit).all()

    # تبدیل داده‌ها به فرمت مناسب
    result = []
    for interaction in interactions:
        result.append({
            "id": interaction.id,
            "type": interaction.interaction_type,
            "target_username": interaction.target_user_username,
            "target_media_shortcode": interaction.target_media_shortcode,
            "content": interaction.content,
            "created_at": interaction.created_at.isoformat(),
            "success": interaction.success,
            "error": interaction.error
        })

    return {
        "type": interaction_type,
        "limit": limit,
        "interactions": result
    }


@router.get("/by-username/{username}")
def get_interactions_by_username(username: str, limit: int = 50, db: Session = Depends(get_db)):
    """دریافت تعاملات با یک کاربر خاص"""
    interactions = db.query(Interaction).filter(
        Interaction.target_user_username == username
    ).order_by(
        Interaction.created_at.desc()
    ).limit(limit).all()

    # تبدیل داده‌ها به فرمت مناسب
    result = []
    for interaction in interactions:
        result.append({
            "id": interaction.id,
            "type": interaction.interaction_type,
            "target_username": interaction.target_user_username,
            "target_media_shortcode": interaction.target_media_shortcode,
            "content": interaction.content,
            "created_at": interaction.created_at.isoformat(),
            "success": interaction.success,
            "error": interaction.error
        })

    return {
        "username": username,
        "limit": limit,
        "interactions": result
    }


@router.get("/filter")
def filter_interactions(
    type: Optional[str] = None,
    username: Optional[str] = None,
    success: Optional[bool] = None,
    days: int = 30,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """فیلتر کردن تعاملات بر اساس معیارهای مختلف"""
    # محدوده زمانی
    date_limit = datetime.now() - timedelta(days=days)

    # ساخت کوئری
    query = db.query(Interaction).filter(Interaction.created_at >= date_limit)

    # اعمال فیلترها
    if type:
        query = query.filter(Interaction.interaction_type == type)

    if username:
        query = query.filter(Interaction.target_user_username == username)

    if success is not None:
        query = query.filter(Interaction.success == success)

    # دریافت نتایج
    total = query.count()
    interactions = query.order_by(
        Interaction.created_at.desc()).limit(limit).all()

    # تبدیل داده‌ها به فرمت مناسب
    result = []
    for interaction in interactions:
        result.append({
            "id": interaction.id,
            "type": interaction.interaction_type,
            "target_username": interaction.target_user_username,
            "target_media_shortcode": interaction.target_media_shortcode,
            "content": interaction.content,
            "created_at": interaction.created_at.isoformat(),
            "success": interaction.success,
            "error": interaction.error
        })

    return {
        "filters": {
            "type": type,
            "username": username,
            "success": success,
            "days": days
        },
        "total": total,
        "limit": limit,
        "interactions": result
    }


@router.get("/summary")
def get_interactions_summary(days: int = 30, db: Session = Depends(get_db)):
    """دریافت خلاصه تعاملات بات"""
    # محدوده زمانی
    date_limit = datetime.now() - timedelta(days=days)

    # آمار کلی
    total_count = db.query(Interaction).filter(
        Interaction.created_at >= date_limit).count()
    success_count = db.query(Interaction).filter(
        Interaction.created_at >= date_limit,
        Interaction.success == True
    ).count()

    # آمار به تفکیک نوع تعامل
    interaction_types = ["like", "comment",
                         "follow", "unfollow", "view_story", "dm"]
    type_stats = {}

    for type_name in interaction_types:
        type_count = db.query(Interaction).filter(
            Interaction.created_at >= date_limit,
            Interaction.interaction_type == type_name
        ).count()

        type_success_count = db.query(Interaction).filter(
            Interaction.created_at >= date_limit,
            Interaction.interaction_type == type_name,
            Interaction.success == True
        ).count()

        type_stats[type_name] = {
            "total": type_count,
            "success": type_success_count,
            "success_rate": (type_success_count / type_count * 100) if type_count > 0 else 0
        }

    # آمار روزانه - تعداد کل تعاملات در هر روز
    daily_stats = {}

    for day in range(days):
        day_date = datetime.now() - timedelta(days=day)
        day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_count = db.query(Interaction).filter(
            Interaction.created_at >= day_start,
            Interaction.created_at < day_end
        ).count()

        daily_stats[day_date.strftime("%Y-%m-%d")] = day_count

    # نتیجه نهایی
    return {
        "period": {
            "days": days,
            "start_date": date_limit.strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d")
        },
        "total_interactions": total_count,
        "success_interactions": success_count,
        "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
        "by_type": type_stats,
        "daily": daily_stats
    }


@router.get("/most-interacted")
def get_most_interacted_users(limit: int = 10, days: int = 30, db: Session = Depends(get_db)):
    """دریافت کاربرانی که بیشترین تعامل با آنها انجام شده است"""
    # محدوده زمانی
    date_limit = datetime.now() - timedelta(days=days)

    # دریافت تمام تعاملات
    interactions = db.query(Interaction).filter(
        Interaction.created_at >= date_limit,
        Interaction.target_user_username != None
    ).all()

    # شمارش تعاملات به تفکیک کاربر
    user_interactions = {}

    for interaction in interactions:
        username = interaction.target_user_username

        if username not in user_interactions:
            user_interactions[username] = {
                "username": username,
                "total": 0,
                "like": 0,
                "comment": 0,
                "follow": 0,
                "unfollow": 0,
                "view_story": 0,
                "dm": 0,
                "success": 0
            }

        user_interactions[username]["total"] += 1
        user_interactions[username][interaction.interaction_type] += 1

        if interaction.success:
            user_interactions[username]["success"] += 1

    # تبدیل به لیست و مرتب‌سازی
    users_list = list(user_interactions.values())
    users_list.sort(key=lambda x: x["total"], reverse=True)

    # محدود کردن تعداد نتایج
    result = users_list[:limit]

    return {
        "period_days": days,
        "limit": limit,
        "users": result
    }
