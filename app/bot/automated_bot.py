# app/bot/automated_bot.py

import asyncio
import random
from loguru import logger
from datetime import datetime, time


class AutomatedBot:
    """کلاس مدیریت چرخه کاری خودکار بات"""

    def __init__(self, session_manager, interaction_manager, follower_manager, comment_manager):
        self.session_manager = session_manager
        self.interaction_manager = interaction_manager
        self.follower_manager = follower_manager
        self.comment_manager = comment_manager
        self.logger = session_manager.logger
        self.running = False
        self.task = None
        self.hashtags = self._load_hashtags()
        self.activity_weights = self._load_activity_weights()

    def _load_hashtags(self):
        """بارگذاری لیست هشتگ‌ها"""
        try:
            from app.bot.utils import load_json_file
            from app.config import HASHTAGS_FILE
            return load_json_file(HASHTAGS_FILE)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری هشتگ‌ها: {e}")
            # هشتگ‌های پیش‌فرض
            return ["طبیعت", "عکاسی", "سفر", "هنر", "موسیقی"]

    def _load_activity_weights(self):
        """بارگذاری اولویت‌های فعالیت‌ها"""
        try:
            from app.config import ACTIVITY_WEIGHTS
            return ACTIVITY_WEIGHTS
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری اولویت‌ها: {e}")
            # اولویت‌های پیش‌فرض
            return {
                "like": 60,
                "comment": 80,
                "follow": 40,
                "unfollow": 30,
                "view_story": 70,
                "dm": 50
            }

    async def start(self):
        """شروع چرخه کاری خودکار"""
        if self.running:
            self.logger.info("بات خودکار در حال اجرا است")
            return False

        self.running = True
        self.logger.info("🤖 شروع چرخه کاری خودکار بات")
        self.task = asyncio.create_task(self._automated_cycle())
        return True

    async def stop(self):
        """توقف چرخه کاری خودکار"""
        if not self.running:
            return False

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        self.logger.info("🛑 چرخه کاری خودکار بات متوقف شد")
        return True

    async def _automated_cycle(self):
        """چرخه اصلی کاری بات"""
        self.logger.info("چرخه کاری خودکار بات شروع شد")

        # شمارنده‌ها برای مدیریت بهتر محدودیت‌ها
        daily_actions = {
            "like": 0,
            "comment": 0,
            "follow": 0,
            "unfollow": 0,
            "dm": 0
        }

        error_count = 0  # شمارنده خطاها
        max_consecutive_errors = 5  # حداکثر خطای پشت سر هم

        while self.running:
            try:
                # کاهش شمارنده خطا در صورت عملیات موفق
                error_count = 0

                # بررسی ساعت روز برای تنظیم فعالیت
                current_hour = datetime.now().hour

                # محدودیت‌های روزانه - توقف اگر از حد مجاز گذشته
                if daily_actions["like"] > 150 or daily_actions["follow"] > 50:
                    self.logger.warning(
                        "محدودیت روزانه رسیده، استراحت طولانی...")
                    await asyncio.sleep(3600)  # استراحت 1 ساعته
                    # ریست شمارنده‌ها در نیمه شب
                    if datetime.now().hour == 0:
                        daily_actions = {key: 0 for key in daily_actions}
                    continue

                # ساعات شب (1 صبح تا 7 صبح): فعالیت کمتر
                if 1 <= current_hour < 7:
                    self.logger.info("ساعت استراحت شبانه - فعالیت محدود")
                    await self._night_activities()
                    await asyncio.sleep(1800)  # استراحت 30 دقیقه در شب
                    continue

                # ساعات پربازدید (9 صبح تا 11 شب): فعالیت معمولی
                self.logger.info("شروع یک دور فعالیت جدید")

                # فعالیت‌های اصلی
                activities = [
                    (self._interact_with_hashtags, self.activity_weights.get(
                        'like', 60) + self.activity_weights.get('comment', 50)),
                    (self._follow_from_hashtags,
                     self.activity_weights.get('follow', 40)),
                    (self._auto_unfollow, self.activity_weights.get('unfollow', 30)),
                    (self._auto_follow_back,
                     self.activity_weights.get('follow', 40) // 2),
                    (self._comment_on_popular_posts,
                     self.activity_weights.get('comment', 50) * 1.2),
                    (self._view_stories, self.activity_weights.get('view_story', 70)),
                    (self._send_direct_messages, self.activity_weights.get('dm', 30))
                ]

                # انتخاب 2 تا 3 فعالیت وزن‌دار (کاهش تعداد فعالیت‌ها)
                selected_activities = self._weighted_sample(
                    activities, k=random.randint(2, 3))

                # اجرای فعالیت‌های انتخاب شده
                for activity_func in selected_activities:
                    await activity_func()
                    # افزایش استراحت بین فعالیت‌ها
                    await asyncio.sleep(random.randint(60, 120))

                    # به‌روزرسانی شمارنده‌ها بر اساس نوع فعالیت
                    if activity_func == self._interact_with_hashtags:
                        daily_actions["like"] += 5  # تقریبی
                    elif activity_func == self._follow_from_hashtags:
                        daily_actions["follow"] += 3  # تقریبی
                    elif activity_func == self._auto_unfollow:
                        daily_actions["unfollow"] += 4  # تقریبی
                    elif activity_func == self._comment_on_popular_posts:
                        daily_actions["comment"] += 2  # تقریبی
                    elif activity_func == self._send_direct_messages:
                        daily_actions["dm"] += 2  # تقریبی

                # استراحت بین دورها - زمان بیشتری برای استراحت (8 تا 20 دقیقه)
                wait_time = random.randint(480, 1200)
                self.logger.info(f"🕒 استراحت به مدت {wait_time // 60} دقیقه")
                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                self.logger.info("چرخه کاری خودکار لغو شد")
                break
            except Exception as e:
                self.logger.error(f"خطا در چرخه کاری: {e}")
                error_count += 1

                # اگر خطاهای پشت سر هم زیاد شد، استراحت طولانی‌تر
                if error_count >= max_consecutive_errors:
                    self.logger.error(
                        f"تعداد خطاهای متوالی به {max_consecutive_errors} رسید. استراحت طولانی...")
                    await asyncio.sleep(1800)  # 30 دقیقه استراحت
                    error_count = 0
                else:
                    # زمان استراحت طولانی‌تر بعد از خطا و ادامه چرخه
                    self.logger.info(
                        "استراحت پس از خطا و تلاش مجدد در 5 دقیقه")
                    await asyncio.sleep(300)

                # بازنشانی شمارنده‌ها
                self.actions_count = 0
                from app.bot.utils import get_actions_before_break
                self.actions_before_break = get_actions_before_break()

    def _weighted_sample(self, weighted_items, k=3):
        """انتخاب تصادفی براساس وزن"""
        # استخراج وزن‌ها
        items, weights = zip(*weighted_items)

        # انتخاب براساس وزن
        selected = random.choices(items, weights=weights, k=k)

        return selected

    async def _night_activities(self):
        """فعالیت‌های محدود شبانه"""
        try:
            # فقط آنفالو، فالوبک و مشاهده استوری در شب
            activities = [
                self._auto_unfollow,
                self._auto_follow_back,
                self._view_stories
            ]
            selected = random.choice(activities)
            await selected(limit=2)  # تعداد کمتر در شب
        except Exception as e:
            self.logger.error(f"خطا در فعالیت شبانه: {e}")

    async def _interact_with_hashtags(self, count=6):
        """تعامل با پست‌های هشتگ‌های مختلف"""
        try:
            # انتخاب یک هشتگ تصادفی از لیست
            hashtag = random.choice(self.hashtags)
            self.logger.info(f"🔍 شروع تعامل با هشتگ #{hashtag}")

            # جستجوی هشتگ
            medias = self.interaction_manager.search_hashtag(hashtag)

            if not medias:
                self.logger.info(f"هیچ پستی با هشتگ #{hashtag} یافت نشد")
                return

            # محدود کردن تعداد
            if len(medias) > count:
                medias = random.sample(medias, count)

            likes = 0
            comments = 0

            # تعامل با پست‌ها
            for media in medias:
                # لایک کردن (احتمال 90%)
                if random.random() < 0.9:
                    if self.interaction_manager.like_media(
                        media_id=media.id,
                        shortcode=media.code,
                        username=media.user.username
                    ):
                        likes += 1

                # کامنت گذاشتن (احتمال 40% - افزایش یافته)
                if random.random() < 0.4:
                    caption = media.caption_text if hasattr(
                        media, 'caption_text') else ""
                    comment_text = self.comment_manager.get_relevant_comment(
                        caption, media.user.username)

                    if self.interaction_manager.comment_media(
                        media_id=media.id,
                        shortcode=media.code,
                        username=media.user.username,
                        text=comment_text
                    ):
                        comments += 1

                # استراحت کوتاه بین تعاملات
                await asyncio.sleep(random.randint(5, 15))

            self.logger.info(
                f"✅ تعامل با هشتگ #{hashtag} پایان یافت: {likes} لایک، {comments} کامنت")

        except Exception as e:
            self.logger.error(f"❌ خطا در تعامل با هشتگ: {e}")

    async def _follow_from_hashtags(self, count=3):
        """فالو کردن کاربران از هشتگ‌های مختلف"""
        try:
            # انتخاب یک هشتگ تصادفی از لیست
            hashtag = random.choice(self.hashtags)
            self.logger.info(f"🔍 فالو کردن کاربران از هشتگ #{hashtag}")

            # جستجوی هشتگ
            medias = self.interaction_manager.search_hashtag(hashtag)

            if not medias:
                self.logger.info(f"هیچ پستی با هشتگ #{hashtag} یافت نشد")
                return

            follows = 0

            # فالو کردن کاربران
            for media in medias:
                if follows >= count:
                    break

                # فالو کردن
                if self.interaction_manager.follow_user(
                    user_id=media.user.pk,
                    username=media.user.username
                ):
                    follows += 1

                # استراحت بین فالوها
                await asyncio.sleep(random.randint(15, 30))

            self.logger.info(
                f"✅ فالو کردن از هشتگ #{hashtag} پایان یافت: {follows} فالو")

        except Exception as e:
            self.logger.error(f"❌ خطا در فالو کردن از هشتگ: {e}")

    async def _auto_unfollow(self, limit=4):
        """آنفالو خودکار کاربرانی که فالوبک نکرده‌اند"""
        try:
            self.logger.info("🔄 شروع آنفالو خودکار کاربران")

            result = self.follower_manager.auto_unfollow(
                days_limit=7, limit=limit)

            self.logger.info(f"✅ آنفالو خودکار پایان یافت: {result} کاربر")

        except Exception as e:
            self.logger.error(f"❌ خطا در آنفالو خودکار: {e}")

    async def _auto_follow_back(self, limit=5):
        """فالوبک خودکار فالوورهای جدید"""
        try:
            self.logger.info("🔄 شروع فالوبک خودکار")

            result = self.follower_manager.auto_follow_back(limit=limit)

            self.logger.info(f"✅ فالوبک خودکار پایان یافت: {result} کاربر")

        except Exception as e:
            self.logger.error(f"❌ خطا در فالوبک خودکار: {e}")

    async def _comment_on_popular_posts(self, count=2):
        """کامنت گذاری روی پست‌های محبوب هشتگ‌ها"""
        try:
            # انتخاب یک هشتگ تصادفی از لیست
            hashtag = random.choice(self.hashtags)
            self.logger.info(f"💬 کامنت گذاری روی پست‌های هشتگ #{hashtag}")

            result = self.comment_manager.auto_comment_on_hashtag(
                hashtag, count=count)

            # استراحت طولانی‌تر بعد از کامنت گذاری
            await asyncio.sleep(random.randint(60, 120))

            self.logger.info(f"✅ کامنت گذاری پایان یافت: {result} کامنت")

        except Exception as e:
            self.logger.error(f"❌ خطا در کامنت گذاری: {e}")

    async def _view_stories(self, limit=8):
        """مشاهده استوری‌های کاربران محبوب"""
        try:
            self.logger.info("👁️ شروع مشاهده استوری‌های کاربران")

            # دریافت فالویینگ‌های ما
            current_user_id = self.interaction_manager.client.user_id
            following = self.interaction_manager.get_user_following(
                user_id=current_user_id, amount=30)

            if not following:
                self.logger.info("هیچ کاربری برای مشاهده استوری یافت نشد")
                return

            # انتخاب تعدادی از کاربران به صورت تصادفی
            selected_users = random.sample(
                list(following.items()), min(limit, len(following)))

            views_count = 0

            for user_id, user_info in selected_users:
                if self.interaction_manager.view_story(user_id=user_id, username=user_info.username):
                    views_count += 1

                # استراحت کوتاه بین مشاهده استوری‌ها
                await asyncio.sleep(random.randint(3, 8))

            self.logger.info(
                f"✅ مشاهده استوری‌ها پایان یافت: {views_count} استوری")

        except Exception as e:
            self.logger.error(f"❌ خطا در مشاهده استوری‌ها: {e}")

    async def _send_direct_messages(self, limit=2):
        """ارسال پیام مستقیم به کاربران"""
        try:
            self.logger.info("📩 شروع ارسال پیام مستقیم")

            # جستجوی یک هشتگ برای یافتن کاربران
            hashtag = random.choice(self.hashtags)
            medias = self.interaction_manager.search_hashtag(hashtag)

            if not medias:
                self.logger.info(
                    f"هیچ کاربری برای ارسال پیام از هشتگ #{hashtag} یافت نشد")
                return

            # کاربران منحصر به فرد را انتخاب می‌کنیم
            unique_users = {}
            for media in medias:
                if media.user.pk not in unique_users:
                    unique_users[media.user.pk] = media

            # انتخاب کاربران تصادفی
            if len(unique_users) > limit:
                selected_medias = random.sample(
                    list(unique_users.values()), limit)
            else:
                selected_medias = list(unique_users.values())

            # پیام‌های ساده
            messages = [
                "سلام، پیج خیلی جالبی دارید 👍",
                "محتوای جالبی دارید، با هم در ارتباط باشیم",
                "پست‌های خوبی میذارید، ممنون از اشتراک‌گذاری",
                "سلام، از آشنایی با شما خوشحالم"
            ]

            sent_count = 0

            for media in selected_medias:
                # انتخاب یک پیام تصادفی
                message = random.choice(messages)

                # ارسال پیام
                if self.interaction_manager.send_dm(
                    user_id=media.user.pk,
                    username=media.user.username,
                    text=message
                ):
                    sent_count += 1

                # استراحت طولانی‌تر بین ارسال پیام‌ها
                await asyncio.sleep(random.randint(60, 120))

            self.logger.info(
                f"✅ ارسال پیام مستقیم پایان یافت: {sent_count} پیام")

        except Exception as e:
            self.logger.error(f"❌ خطا در ارسال پیام مستقیم: {e}")
