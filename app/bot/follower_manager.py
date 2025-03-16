from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

from app.database.connection import get_db
from app.database.models import Interaction
from app.bot.utils import random_delay, should_take_break, take_random_break


class FollowerManager:
    def __init__(self, session_manager, interaction_manager):
        self.session_manager = session_manager
        self.interaction_manager = interaction_manager
        self.client = session_manager.client
        self.logger = session_manager.logger
        self.session_id = session_manager.session_id
        self.db = next(get_db())

    def get_followers_to_unfollow(self, days_limit=7, limit=50):
        """یافتن کاربرانی که فالو کرده‌ایم اما ما را بازگشت نکرده‌اند"""
        try:
            self.logger.info("یافتن کاربران برای آنفالو...")

            # یافتن تمام کاربرانی که فالو کرده‌ایم
            date_limit = datetime.now() - timedelta(days=days_limit)
            followed_users = self.db.query(Interaction).filter(
                Interaction.interaction_type == "follow",
                Interaction.success == True,
                Interaction.created_at <= date_limit
            ).limit(limit).all()

            if not followed_users:
                self.logger.info("هیچ کاربری برای بررسی آنفالو یافت نشد")
                return []

            self.logger.info(
                f"بررسی {len(followed_users)} کاربر برای آنفالو...")

            users_to_unfollow = []
            user_info = {}

            for follow in followed_users:
                if not follow.target_user_id:
                    continue

                # بررسی آیا این کاربر ما را فالو کرده‌است
                random_delay()

                try:
                    # دریافت اطلاعات کاربر
                    if follow.target_user_id not in user_info:
                        user = self.client.user_info(follow.target_user_id)
                        user_info[follow.target_user_id] = user
                    else:
                        user = user_info[follow.target_user_id]

                    # بررسی وضعیت فالو
                    friendship = self.client.user_friendship(
                        follow.target_user_id)

                    # اگر ما را فالو نکرده، اضافه به لیست آنفالو
                    if not friendship.followed_by:
                        users_to_unfollow.append({
                            "user_id": follow.target_user_id,
                            "username": follow.target_user_username or user.username,
                            "followed_at": follow.created_at
                        })

                        if should_take_break():
                            take_random_break(self.logger)
                except Exception as e:
                    self.logger.error(
                        f"خطا در بررسی کاربر {follow.target_user_id}: {e}")
                    continue

            self.logger.info(
                f"✅ {len(users_to_unfollow)} کاربر برای آنفالو یافت شد")
            return users_to_unfollow
        except Exception as e:
            self.logger.error(f"❌ خطا در یافتن کاربران برای آنفالو: {e}")
            return []

    def auto_unfollow(self, days_limit=7, limit=10):
        """آنفالو خودکار کاربرانی که ما را فالو نکرده‌اند"""
        users_to_unfollow = self.get_followers_to_unfollow(days_limit, limit)

        if not users_to_unfollow:
            return 0

        unfollow_count = 0

        for user in users_to_unfollow:
            if self.interaction_manager.unfollow_user(
                user_id=user["user_id"],
                username=user["username"]
            ):
                unfollow_count += 1

            if should_take_break():
                take_random_break(self.logger)

        self.logger.info(f"✅ {unfollow_count} کاربر با موفقیت آنفالو شدند")
        return unfollow_count

    def get_new_followers(self, days_limit=1):
        """یافتن فالوورهای جدید که هنوز فالوبک نشده‌اند"""
        try:
            self.logger.info("یافتن فالوورهای جدید برای فالوبک...")

            # دریافت لیست فالوورهای فعلی
            current_user_id = self.client.user_id
            followers = self.client.user_followers(current_user_id)

            if not followers:
                self.logger.info("هیچ فالووری یافت نشد")
                return []

            # دریافت لیست کاربرانی که قبلاً فالو کرده‌ایم
            date_limit = datetime.now() - timedelta(days=days_limit)
            followed_users = self.db.query(Interaction).filter(
                Interaction.interaction_type == "follow",
                Interaction.success == True
            ).all()

            followed_ids = set()
            for follow in followed_users:
                if follow.target_user_id:
                    followed_ids.add(follow.target_user_id)

            # یافتن فالوورهایی که هنوز فالو نکرده‌ایم
            new_followers = []

            for user_id, user in followers.items():
                if user_id not in followed_ids:
                    new_followers.append({
                        "user_id": user_id,
                        "username": user.username
                    })

            self.logger.info(
                f"✅ {len(new_followers)} فالوور جدید برای فالوبک یافت شد")
            return new_followers
        except Exception as e:
            self.logger.error(f"❌ خطا در یافتن فالوورهای جدید: {e}")
            return []

    def auto_follow_back(self, limit=10):
        """فالوبک خودکار فالوورهای جدید"""
        new_followers = self.get_new_followers()

        if not new_followers:
            return 0

        # محدود کردن تعداد فالوبک‌ها
        if len(new_followers) > limit:
            new_followers = random.sample(new_followers, limit)

        follow_count = 0

        for user in new_followers:
            if self.interaction_manager.follow_user(
                user_id=user["user_id"],
                username=user["username"]
            ):
                follow_count += 1

            if should_take_break():
                take_random_break(self.logger)

        self.logger.info(f"✅ {follow_count} کاربر با موفقیت فالوبک شدند")
        return follow_count
