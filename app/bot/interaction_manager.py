import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from instagrapi.exceptions import ClientError

from app.database.connection import get_db
from app.database.models import Interaction, DailyStats
from app.bot.utils import (
    random_delay, should_take_break, take_random_break,
    get_actions_before_break, load_json_file
)
from app.config import COMMENTS_FILE, HASHTAGS_FILE


class InteractionManager:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.client = session_manager.client
        self.logger = session_manager.logger
        self.session_id = session_manager.session_id
        self.db = next(get_db())
        self.comments = load_json_file(COMMENTS_FILE)
        self.hashtags = load_json_file(HASHTAGS_FILE)
        self.actions_count = 0
        self.actions_before_break = get_actions_before_break()

        # آمار امروز
        self.today_stats = self._get_or_create_daily_stats()

    def _get_or_create_daily_stats(self):
        """دریافت یا ساخت رکورد آمار روزانه با مدیریت خطا"""
        try:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            try:
                stats = self.db.query(DailyStats).filter(
                    DailyStats.date == today).first()
            except Exception as query_error:
                self.logger.error(f"خطا در جستجوی آمار روزانه: {query_error}")
                # تلاش برای ریست جلسه دیتابیس
                self.db = next(get_db())
                stats = None

            if not stats:
                try:
                    stats = DailyStats(
                        date=today,
                        likes_count=0,
                        comments_count=0,
                        follows_count=0,
                        unfollows_count=0,
                        story_views_count=0,
                        dms_count=0,
                        total_interactions=0,
                        success_rate=100.0
                    )
                    self.db.add(stats)
                    self.db.commit()
                    self.db.refresh(stats)
                    self.logger.info(
                        f"رکورد آمار روزانه جدید ایجاد شد: {today.strftime('%Y-%m-%d')}")
                except Exception as create_error:
                    self.logger.error(
                        f"خطا در ایجاد آمار روزانه: {create_error}")
                    self.db.rollback()
                    # ایجاد یک آبجکت موقت بدون ذخیره در دیتابیس
                    stats = DailyStats(
                        date=today,
                        likes_count=0,
                        comments_count=0,
                        follows_count=0,
                        unfollows_count=0,
                        story_views_count=0,
                        dms_count=0,
                        total_interactions=0,
                        success_rate=100.0
                    )
                    self.logger.warning(
                        "از آبجکت آمار موقت استفاده می‌شود (بدون ذخیره در دیتابیس)")

            return stats
        except Exception as e:
            self.logger.error(f"خطا در دریافت/ساخت آمار روزانه: {e}")
            # بازگرداندن یک آبجکت موقت
            return DailyStats(
                date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                likes_count=0,
                comments_count=0,
                follows_count=0,
                unfollows_count=0,
                story_views_count=0,
                dms_count=0,
                total_interactions=0,
                success_rate=100.0
            )

    # بخش _record_interaction در فایل app/bot/interaction_manager.py
    def _record_interaction(self, interaction_type, target_user_id=None, target_user_username=None,
                            target_media_id=None, target_media_shortcode=None, content=None, success=True, error=None):
        """ثبت یک تعامل در دیتابیس با مدیریت خطای بهبود یافته"""
        try:
            # ابتدا بررسی کنیم که دیتابیس و جداول وجود دارند
            try:
                # یک کوئری ساده برای بررسی وجود جدول
                interaction_count = self.db.query(Interaction).count()
                self.logger.debug(
                    f"تعداد کل تعاملات قبلی: {interaction_count}")
            except Exception as check_error:
                self.logger.error(f"خطا در بررسی دیتابیس: {check_error}")
                # ادامه اجرا - ممکن است جلوتر مشکل حل شود

            # ایجاد رکورد جدید
            interaction = Interaction(
                session_id=self.session_id,
                interaction_type=interaction_type,
                target_user_id=target_user_id,
                target_user_username=target_user_username,
                target_media_id=target_media_id,
                target_media_shortcode=target_media_shortcode,
                content=content,
                success=success,
                error=error
            )

            try:
                self.db.add(interaction)
                self.db.commit()

                # به‌روزرسانی آمار روزانه
                if success:
                    if not hasattr(self, 'today_stats') or self.today_stats is None:
                        # اگر today_stats وجود ندارد، آن را دوباره ایجاد کنیم
                        self.today_stats = self._get_or_create_daily_stats()

                    if interaction_type == "like":
                        self.today_stats.likes_count += 1
                    elif interaction_type == "comment":
                        self.today_stats.comments_count += 1
                    elif interaction_type == "follow":
                        self.today_stats.follows_count += 1
                    elif interaction_type == "unfollow":
                        self.today_stats.unfollows_count += 1
                    elif interaction_type == "view_story":
                        self.today_stats.story_views_count += 1
                    elif interaction_type == "dm":
                        self.today_stats.dms_count += 1

                    self.today_stats.total_interactions += 1
                    try:
                        self.db.commit()
                    except Exception as stats_error:
                        self.logger.error(
                            f"خطا در به‌روزرسانی آمار روزانه: {stats_error}")
                        self.db.rollback()
                        # ادامه کار بدون توقف
            except Exception as db_error:
                self.logger.error(f"خطا در ثبت تعامل در دیتابیس: {db_error}")
                self.db.rollback()
                # ادامه کار بدون توقف

            # افزایش شمارنده اقدامات
            self.actions_count += 1

            # بررسی نیاز به استراحت
            if self.actions_count >= self.actions_before_break:
                take_random_break(self.logger)
                self.actions_count = 0
                self.actions_before_break = get_actions_before_break()
            elif should_take_break():
                self.logger.info("استراحت تصادفی...")
                take_random_break(self.logger)

            return True
        except Exception as e:
            self.logger.error(f"خطا در ثبت تعامل: {e}")
            return False

    def like_media(self, media_id, shortcode=None, username=None):
        """لایک کردن یک پست"""
        try:
            self.logger.info(
                f"لایک کردن پست {shortcode or media_id} از {username or 'کاربر ناشناس'}")
            random_delay()

            try:
                result = self.client.media_like(media_id)
                success = result is True
            except Exception as e:
                if "challenge_required" in str(e):
                    self.logger.error(
                        f"❌ خطا در لایک کردن: challenge_required")
                    self.session_manager.handle_challenge(e)
                    success = False
                else:
                    raise e

            if success:
                self.logger.info(f"✅ لایک موفق: {shortcode or media_id}")
            else:
                self.logger.warning(f"⚠️ لایک ناموفق: {shortcode or media_id}")

            self._record_interaction(
                interaction_type="like",
                target_user_id=username,
                target_user_username=username,
                target_media_id=media_id,
                target_media_shortcode=shortcode,
                success=success
            )

            return success
        except Exception as e:
            self.logger.error(f"❌ خطا در لایک کردن: {e}")
            self._record_interaction(
                interaction_type="like",
                target_user_id=username,
                target_user_username=username,
                target_media_id=media_id,
                target_media_shortcode=shortcode,
                success=False,
                error=str(e)
            )
            return False

    def comment_media(self, media_id, shortcode=None, username=None, text=None):
        """ارسال کامنت روی یک پست"""
        try:
            # اگر متن کامنت تعیین نشده باشد، انتخاب تصادفی
            if not text and self.comments:
                text = random.choice(self.comments)

            if not text:
                self.logger.warning("هیچ متن کامنتی برای ارسال وجود ندارد")
                return False

            self.logger.info(
                f"کامنت گذاشتن روی پست {shortcode or media_id} از {username or 'کاربر ناشناس'}")

            # تاخیر طولانی‌تر قبل از کامنت گذاشتن
            random_delay()

            # بررسی محدودیت روزانه کامنت
            # کاهش محدودیت روزانه کامنت به 10
            if hasattr(self, 'today_stats') and self.today_stats.comments_count >= 10:
                self.logger.warning("محدودیت روزانه کامنت رسیده است")
                return False

            # کوتاه‌سازی متن کامنت - کامنت‌های کوتاه‌تر احتمال کمتری برای خطای challenge دارند
            if len(text) > 30:
                text = text[:30]

            success = False
            error_msg = None

            try:
                # تلاش برای ارسال کامنت
                result = self.client.media_comment(media_id, text)
                success = result is not None
            except Exception as e:
                error_msg = str(e).lower()
                if "challenge_required" in error_msg:
                    self.logger.error(
                        f"❌ خطا در کامنت گذاشتن: challenge_required")
                    # فقط لاگ می‌کنیم و ادامه می‌دهیم - بدون فراخوانی handle_challenge
                    success = False
                elif "spam" in error_msg:
                    self.logger.error(f"❌ خطای اسپم در کامنت گذاشتن: {e}")
                    # استراحت کوتاه بدون فراخوانی handle_challenge
                    time.sleep(10)
                    success = False
                else:
                    self.logger.error(f"❌ خطای عمومی در کامنت گذاشتن: {e}")
                    success = False

            if success:
                self.logger.info(f"✅ کامنت موفق: {shortcode or media_id}")
            else:
                self.logger.warning(
                    f"⚠️ کامنت ناموفق: {shortcode or media_id}")

            # ثبت تعامل بدون توجه به موفقیت یا عدم موفقیت
            self._record_interaction(
                interaction_type="comment",
                target_user_id=username,
                target_user_username=username,
                target_media_id=media_id,
                target_media_shortcode=shortcode,
                content=text,
                success=success,
                error=error_msg
            )

            # حتی در صورت خطا، میخواهیم فرآیند کلی ادامه پیدا کند
            return True  # بازگرداندن True حتی در صورت شکست کامنت گذاری

        except Exception as e:
            self.logger.error(f"❌ خطا در کامنت گذاشتن: {e}")
            self._record_interaction(
                interaction_type="comment",
                target_user_id=username,
                target_user_username=username,
                target_media_id=media_id,
                target_media_shortcode=shortcode,
                content=text,
                success=False,
                error=str(e)
            )
            return False

    def follow_user(self, user_id=None, username=None):
        """فالو کردن یک کاربر"""
        try:
            # اگر نام کاربری داریم اما آیدی نداریم
            if not user_id and username:
                user_info = self.client.user_info_by_username(username)
                user_id = user_info.pk

            if not user_id:
                self.logger.warning(
                    "برای فالو کردن باید آیدی یا نام کاربری مشخص باشد")
                return False

            self.logger.info(f"فالو کردن کاربر {username or user_id}")
            random_delay()

            try:
                result = self.client.user_follow(user_id)
                success = result is True
            except Exception as e:
                if "challenge_required" in str(e):
                    self.logger.error(
                        f"❌ خطا در فالو کردن: challenge_required")
                    self.session_manager.handle_challenge(e)
                    success = False
                else:
                    raise e

            if success:
                self.logger.info(f"✅ فالو موفق: {username or user_id}")
            else:
                self.logger.warning(f"⚠️ فالو ناموفق: {username or user_id}")

            self._record_interaction(
                interaction_type="follow",
                target_user_id=user_id,
                target_user_username=username,
                success=success
            )

            return success
        except Exception as e:
            self.logger.error(f"❌ خطا در فالو کردن: {e}")
            self._record_interaction(
                interaction_type="follow",
                target_user_id=user_id,
                target_user_username=username,
                success=False,
                error=str(e)
            )
            return False

    def unfollow_user(self, user_id=None, username=None):
        """آنفالو کردن یک کاربر"""
        try:
            # اگر نام کاربری داریم اما آیدی نداریم
            if not user_id and username:
                user_info = self.client.user_info_by_username(username)
                user_id = user_info.pk

            if not user_id:
                self.logger.warning(
                    "برای آنفالو کردن باید آیدی یا نام کاربری مشخص باشد")
                return False

            self.logger.info(f"آنفالو کردن کاربر {username or user_id}")
            random_delay()

            result = self.client.user_unfollow(user_id)
            success = result is True

            if success:
                self.logger.info(f"✅ آنفالو موفق: {username or user_id}")
            else:
                self.logger.warning(f"⚠️ آنفالو ناموفق: {username or user_id}")

            self._record_interaction(
                interaction_type="unfollow",
                target_user_id=user_id,
                target_user_username=username,
                success=success
            )

            return success
        except Exception as e:
            self.logger.error(f"❌ خطا در آنفالو کردن: {e}")
            self._record_interaction(
                interaction_type="unfollow",
                target_user_id=user_id,
                target_user_username=username,
                success=False,
                error=str(e)
            )
            return False

    def view_story(self, user_id=None, username=None):
        """مشاهده استوری یک کاربر"""
        try:
            # اگر نام کاربری داریم اما آیدی نداریم
            if not user_id and username:
                user_info = self.client.user_info_by_username(username)
                user_id = user_info.pk

            if not user_id:
                self.logger.warning(
                    "برای مشاهده استوری باید آیدی یا نام کاربری مشخص باشد")
                return False

            self.logger.info(f"مشاهده استوری کاربر {username or user_id}")
            random_delay()

            stories = self.client.user_stories(user_id)

            if not stories:
                self.logger.info(f"کاربر {username or user_id} استوری ندارد")
                return False

            # مشاهده اولین استوری
            story = stories[0]
            result = self.client.story_seen([story.pk])
            success = result is not None

            if success:
                self.logger.info(
                    f"✅ مشاهده استوری موفق: {username or user_id}")
            else:
                self.logger.warning(
                    f"⚠️ مشاهده استوری ناموفق: {username or user_id}")

            self._record_interaction(
                interaction_type="view_story",
                target_user_id=user_id,
                target_user_username=username,
                target_media_id=story.pk,
                success=success
            )

            return success
        except Exception as e:
            self.logger.error(f"❌ خطا در مشاهده استوری: {e}")
            self._record_interaction(
                interaction_type="view_story",
                target_user_id=user_id,
                target_user_username=username,
                success=False,
                error=str(e)
            )
            return False

    def send_dm(self, user_id=None, username=None, text=None):
        """ارسال پیام مستقیم به یک کاربر"""
        try:
            # اگر نام کاربری داریم اما آیدی نداریم
            if not user_id and username:
                user_info = self.client.user_info_by_username(username)
                user_id = user_info.pk

            if not user_id:
                self.logger.warning(
                    "برای ارسال پیام باید آیدی یا نام کاربری مشخص باشد")
                return False

            if not text:
                self.logger.warning("متن پیام مشخص نشده است")
                return False

            self.logger.info(f"ارسال پیام به کاربر {username or user_id}")
            random_delay()

            try:
                result = self.client.direct_send(text, [user_id])
                success = result is not None
            except Exception as e:
                if "challenge_required" in str(e):
                    self.logger.error(
                        f"❌ خطا در ارسال پیام: challenge_required")
                    self.session_manager.handle_challenge(e)
                    success = False
                else:
                    raise e

            if success:
                self.logger.info(f"✅ ارسال پیام موفق: {username or user_id}")
            else:
                self.logger.warning(
                    f"⚠️ ارسال پیام ناموفق: {username or user_id}")

            self._record_interaction(
                interaction_type="dm",
                target_user_id=user_id,
                target_user_username=username,
                content=text,
                success=success
            )

            return success
        except Exception as e:
            self.logger.error(f"❌ خطا در ارسال پیام: {e}")
            self._record_interaction(
                interaction_type="dm",
                target_user_id=user_id,
                target_user_username=username,
                content=text,
                success=False,
                error=str(e)
            )
            return False

    def search_hashtag(self, hashtag):
        """جستجوی پست‌ها با هشتگ"""
        try:
            self.logger.info(f"جستجوی هشتگ #{hashtag}")
            random_delay()

            medias = self.client.hashtag_medias_recent(hashtag, amount=10)

            if not medias:
                self.logger.info(f"هیچ پستی با هشتگ #{hashtag} یافت نشد")
                return []

            self.logger.info(f"✅ {len(medias)} پست با هشتگ #{hashtag} یافت شد")
            return medias
        except Exception as e:
            self.logger.error(f"❌ خطا در جستجوی هشتگ: {e}")
            return []

    def get_user_followers(self, user_id=None, username=None, amount=10):
        """دریافت فالوورهای یک کاربر"""
        try:
            # اگر نام کاربری داریم اما آیدی نداریم
            if not user_id and username:
                user_info = self.client.user_info_by_username(username)
                user_id = user_info.pk

            if not user_id:
                self.logger.warning(
                    "برای دریافت فالوورها باید آیدی یا نام کاربری مشخص باشد")
                return []

            self.logger.info(f"دریافت فالوورهای کاربر {username or user_id}")
            random_delay()

            followers = self.client.user_followers(user_id, amount=amount)

            if not followers:
                self.logger.info(f"کاربر {username or user_id} فالووری ندارد")
                return []

            self.logger.info(
                f"✅ {len(followers)} فالوور برای {username or user_id} یافت شد")
            return followers
        except Exception as e:
            self.logger.error(f"❌ خطا در دریافت فالوورها: {e}")
            return []

    def get_user_following(self, user_id=None, username=None, amount=10):
        """دریافت فالویینگ‌های یک کاربر"""
        try:
            # اگر نام کاربری داریم اما آیدی نداریم
            if not user_id and username:
                user_info = self.client.user_info_by_username(username)
                user_id = user_info.pk

            if not user_id:
                self.logger.warning(
                    "برای دریافت فالویینگ‌ها باید آیدی یا نام کاربری مشخص باشد")
                return []

            self.logger.info(
                f"دریافت فالویینگ‌های کاربر {username or user_id}")
            random_delay()

            following = self.client.user_following(user_id, amount=amount)

            if not following:
                self.logger.info(
                    f"کاربر {username or user_id} کسی را فالو نکرده است")
                return []

            self.logger.info(
                f"✅ {len(following)} فالویینگ برای {username or user_id} یافت شد")
            return following
        except Exception as e:
            self.logger.error(f"❌ خطا در دریافت فالویینگ‌ها: {e}")
            return []
