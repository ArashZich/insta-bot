from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class BotSession(Base):
    """مدل جلسات بات"""
    __tablename__ = "bot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    started_at = Column(DateTime, default=datetime.now)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    user_agent = Column(String, nullable=True)


class Interaction(Base):
    """مدل تعاملات بات"""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    # like, comment, follow, unfollow, view_story, dm
    interaction_type = Column(String, index=True)
    target_user_id = Column(String, index=True, nullable=True)
    target_user_username = Column(String, nullable=True)
    target_media_id = Column(String, index=True, nullable=True)
    target_media_shortcode = Column(String, nullable=True)
    content = Column(Text, nullable=True)  # محتوای کامنت یا دایرکت
    created_at = Column(DateTime, default=datetime.now)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)


class DailyStats(Base):
    """آمار روزانه بات"""
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    follows_count = Column(Integer, default=0)
    unfollows_count = Column(Integer, default=0)
    story_views_count = Column(Integer, default=0)
    dms_count = Column(Integer, default=0)
    total_interactions = Column(Integer, default=0)
    success_rate = Column(Float, default=100.0)
