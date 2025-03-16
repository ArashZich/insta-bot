import time
import random
from typing import List, Dict, Any, Set
from loguru import logger
from datetime import datetime, timedelta

from app.database.connection import get_database, get_mongo_client
from app.bot.instagram_client import InstagramClient
from app.database.repositories import UserRepository, InteractionRepository
from app.database.models import InteractionType
from app.config import FOLLOW_LIMIT_PER_DAY, UNFOLLOW_LIMIT_PER_DAY


class FollowManager:
    """مدیریت عملیات فالو و آنفالو"""

    def __init__(self, instagram_client: InstagramClient = None):
        self.instagram_client = instagram_client or InstagramClient()
        self.logger = logger
        self.user_repository = UserRepository()
        self.interaction_repository = InteractionRepository()

    def check_daily_follow_limit(self) -> bool:
        """بررسی محدودیت روزانه فالو"""
        daily_follows = self.interaction_repository.get_daily_interaction_count(
            InteractionType.FOLLOW)
        return daily_follows < FOLLOW_LIMIT_PER_DAY

    def check_daily_unfollow_limit(self) -> bool:
        """بررسی محدودیت روزانه آنفالو"""
        daily_unfollows = self.interaction_repository.get_daily_interaction_count(
            InteractionType.UNFOLLOW)
        return daily_unfollows < UNFOLLOW_LIMIT_PER_DAY

    def follow_users_by_hashtag(self, hashtag: str, max_follows: int = 5) -> List[Dict[str, Any]]:
        """فالو کردن کاربران براساس هشتگ"""
        if not self.check_daily_follow_limit():
            self.logger.warning("محدودیت روزانه فالو کردن به پایان رسیده است")
            return []

        self.logger.info(f"شروع فالو کردن کاربران با هشتگ #{hashtag}")

        followed_users = []
        tried_users = set()  # کاربرانی که قبلاً بررسی شده‌اند

        # دریافت پست‌های اخیر با هشتگ
        medias = self.instagram_client.search_hashtag(hashtag, count=20)

        for media in medias:
            if len(followed_users) >= max_follows or not self.check_daily_follow_limit():
                break

            user_id = media.user.pk
            username = media.user.username

            # اگر قبلاً این کاربر را بررسی کرده‌ایم، رد می‌شویم
            if user_id in tried_users:
                continue

            tried_users.add(user_id)

            # بررسی اینکه آیا قبلاً کاربر را فالو کرده‌ایم
            existing_user = self.user_repository.get_user_by_instagram_id(
                user_id)
            if existing_user and (existing_user.get("followed_at") is not None and existing_user.get("unfollowed_at") is None):
                self.logger.debug(f"کاربر {username} قبلاً فالو شده است")
                continue

            # دریافت اطلاعات بیشتر درباره کاربر
            user_info = self.instagram_client.get_user_info(user_id)

            # رد کردن کاربران خصوصی یا با تعداد فالوئر زیاد (احتمالاً فالو بک نمی‌کنند)
            if user_info.is_private or user_info.follower_count > 10000:
                self.logger.debug(
                    f"رد کردن کاربر {username}: خصوصی={user_info.is_private}, فالوئر={user_info.follower_count}")
                continue

            # فالو کردن کاربر
            success = self.instagram_client.follow_user(user_id)

            if success:
                # ثبت کاربر در دیتابیس
                user_data = self.user_repository.create_user(
                    instagram_id=str(user_id),
                    username=username,
                    full_name=user_info.full_name,
                    is_private=user_info.is_private,
                    followers_count=user_info.follower_count,
                    following_count=user_info.following_count
                )

                # به‌روزرسانی وضعیت فالو
                self.user_repository.update_follow_status(str(user_id), True)

                # ثبت تعامل
                self.interaction_repository.create_interaction(
                    session_id=self.instagram_client.session_manager.session_id,
                    user_id=str(user_data.get("_id")),
                    instagram_user_id=str(user_id),
                    instagram_username=username,
                    interaction_type=InteractionType.FOLLOW
                )

                followed_users.append(user_data)
                self.logger.info(f"✅ کاربر {username} با موفقیت فالو شد")

                # تأخیر تصادفی برای شبیه‌سازی رفتار انسانی
                time.sleep(random.uniform(15, 45))
            else:
                self.logger.error(f"❌ خطا در فالو کردن کاربر {username}")

        return followed_users

    def follow_users_by_username(self, usernames: List[str]) -> List[Dict[str, Any]]:
        """فالو کردن کاربران براساس نام کاربری"""
        if not self.check_daily_follow_limit():
            self.logger.warning("محدودیت روزانه فالو کردن به پایان رسیده است")
            return []

        self.logger.info(
            f"شروع فالو کردن کاربران از لیست ({len(usernames)} کاربر)")

        followed_users = []

        for username in usernames:
            if not self.check_daily_follow_limit():
                break

            # بررسی اینکه آیا قبلاً کاربر را فالو کرده‌ایم
            existing_user = self.user_repository.get_user_by_username(username)
            if existing_user and (existing_user.get("followed_at") is not None and existing_user.get("unfollowed_at") is None):
                self.logger.debug(f"کاربر {username} قبلاً فالو شده است")
                continue

            # جستجوی کاربر
            search_results = self.instagram_client.search_users(
                username, count=1)

            if not search_results:
                self.logger.warning(f"کاربر {username} یافت نشد")
                continue

            user_id = list(search_results.keys())[0]
            user_info = search_results[user_id]

            # فالو کردن کاربر
            success = self.instagram_client.follow_user(user_id)

            if success:
                # ثبت کاربر در دیتابیس
                user_data = self.user_repository.create_user(
                    instagram_id=str(user_id),
                    username=username,
                    full_name=user_info.full_name,
                    is_private=user_info.is_private,
                    followers_count=user_info.follower_count,
                    following_count=user_info.following_count
                )

                # به‌روزرسانی وضعیت فالو
                self.user_repository.update_follow_status(str(user_id), True)

                # ثبت تعامل
                self.interaction_repository.create_interaction(
                    session_id=self.instagram_client.session_manager.session_id,
                    user_id=str(user_data.get("_id")),
                    instagram_user_id=str(user_id),
                    instagram_username=username,
                    interaction_type=InteractionType.FOLLOW
                )

                followed_users.append(user_data)
                self.logger.info(f"✅ کاربر {username} با موفقیت فالو شد")

                # تأخیر تصادفی برای شبیه‌سازی رفتار انسانی
                time.sleep(random.uniform(20, 50))
            else:
                self.logger.error(f"❌ خطا در فالو کردن کاربر {username}")

        return followed_users

    def unfollow_non_followers(self, max_unfollows: int = 5) -> List[Dict[str, Any]]:
        """آنفالو کردن کاربرانی که فالو بک نکرده‌اند"""
        if not self.check_daily_unfollow_limit():
            self.logger.warning(
                "محدودیت روزانه آنفالو کردن به پایان رسیده است")
            return []

        self.logger.info("شروع آنفالو کردن کاربرانی که فالو بک نکرده‌اند")

        # دریافت کاربرانی که باید آنفالو شوند
        users_to_unfollow = self.user_repository.get_users_to_unfollow(
            max_unfollows)

        unfollowed_users = []

        for user in users_to_unfollow:
            if not self.check_daily_unfollow_limit():
                break

            user_id = user.get("instagram_id")
            username = user.get("username")

            # آنفالو کردن کاربر
            success = self.instagram_client.unfollow_user(user_id)

            if success:
                # به‌روزرسانی وضعیت آنفالو
                self.user_repository.update_follow_status(user_id, False)

                # ثبت تعامل
                self.interaction_repository.create_interaction(
                    session_id=self.instagram_client.session_manager.session_id,
                    user_id=str(user.get("_id")),
                    instagram_user_id=user_id,
                    instagram_username=username,
                    interaction_type=InteractionType.UNFOLLOW
                )

                unfollowed_users.append(user)
                self.logger.info(f"✅ کاربر {username} با موفقیت آنفالو شد")

                # تأخیر تصادفی برای شبیه‌سازی رفتار انسانی
                time.sleep(random.uniform(20, 40))
            else:
                self.logger.error(f"❌ خطا در آنفالو کردن کاربر {username}")

        return unfollowed_users

    def update_following_back_status(self) -> int:
        """به‌روزرسانی وضعیت فالو بک کاربران"""
        self.logger.info("به‌روزرسانی وضعیت فالو بک کاربران")

        # دریافت کاربرانی که فالو کرده‌ایم
        db = get_database()
        followed_users = list(db[get_collection_name("users")].find({
            "followed_at": {"$ne": None},
            "unfollowed_at": None
        }))

        # دریافت لیست فالوئرهای ما
        my_user_id = self.instagram_client.client.user_id
        my_followers = self.instagram_client.get_user_followers(
            my_user_id, amount=50)
        my_followers_ids = set(str(fid) for fid in my_followers.keys())

        updated_count = 0

        for user in followed_users:
            instagram_id = user.get("instagram_id")
            is_following_back = instagram_id in my_followers_ids

            # اگر وضعیت فالو بک تغییر کرده، به‌روزرسانی می‌کنیم
            if user.get("is_following_back") != is_following_back:
                self.user_repository.update_following_back_status(
                    instagram_id, is_following_back)
                updated_count += 1

                action = "شروع به فالو کردن ما" if is_following_back else "دیگر ما را فالو نمی‌کند"
                self.logger.info(f"کاربر {user.get('username')} {action}")

        self.logger.info(f"وضعیت فالو بک {updated_count} کاربر به‌روزرسانی شد")
        return updated_count
