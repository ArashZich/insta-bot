import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re

from app.bot.utils import load_json_file, random_delay, should_take_break, take_random_break
from app.config import COMMENTS_FILE


class CommentManager:
    def __init__(self, session_manager, interaction_manager):
        self.session_manager = session_manager
        self.interaction_manager = interaction_manager
        self.client = session_manager.client
        self.logger = session_manager.logger
        self.comments = load_json_file(COMMENTS_FILE)

        # دسته‌بندی کامنت‌ها بر اساس کلیدواژه‌ها
        self.categorized_comments = self._categorize_comments()

    def _categorize_comments(self):
        """دسته‌بندی کامنت‌ها برای استفاده هوشمندانه‌تر"""
        categories = {
            "general": [],
            "question": [],
            "positive": [],
            "compliment": [],
            "emoji": []
        }

        # الگوهای تشخیص دسته‌ها
        patterns = {
            "question": r'\?$',
            "emoji": r'[\U0001F300-\U0001F6FF\U0001F700-\U0001F77F\U0001F900-\U0001F9FF\u2600-\u26FF]',
        }

        positive_words = [
            "عالی", "خوب", "زیبا", "قشنگ", "جالب", "دوست داشتنی",
            "محشر", "فوق العاده", "بی نظیر", "شگفت انگیز"
        ]

        compliment_words = [
            "تبریک", "احسنت", "آفرین", "دمت گرم", "لایک", "بهترین",
            "کارت درسته", "خسته نباشی"
        ]

        for comment in self.comments:
            # بررسی سوالی بودن
            if re.search(patterns["question"], comment):
                categories["question"].append(comment)
            # بررسی ایموجی داشتن
            elif re.search(patterns["emoji"], comment):
                categories["emoji"].append(comment)
            # بررسی تمجید
            elif any(word in comment for word in compliment_words):
                categories["compliment"].append(comment)
            # بررسی مثبت بودن
            elif any(word in comment for word in positive_words):
                categories["positive"].append(comment)
            # کامنت‌های عمومی
            else:
                categories["general"].append(comment)

        # اطمینان از وجود کامنت در هر دسته
        for category, comments in categories.items():
            if not comments:
                categories[category] = self.comments

        return categories

    def get_relevant_comment(self, caption=None, username=None):
        """انتخاب کامنت مناسب بر اساس محتوای پست"""
        if not caption:
            return random.choice(self.comments)

        # بررسی الگوهای مختلف در کپشن
        has_question = "?" in caption
        has_emoji = bool(re.search(
            r'[\U0001F300-\U0001F6FF\U0001F700-\U0001F77F\U0001F900-\U0001F9FF\u2600-\u26FF]', caption))

        # کلمات مثبت و تمجیدآمیز در فارسی
        positive_words = ["عالی", "خوب", "زیبا", "قشنگ", "جالب", "دوست داشتنی"]
        compliment_words = ["تبریک", "احسنت",
                            "آفرین", "دمت گرم", "لایک", "بهترین"]

        is_positive = any(word in caption for word in positive_words)
        is_compliment = any(word in caption for word in compliment_words)

        # انتخاب دسته‌ی مناسب بر اساس ویژگی‌های کپشن
        if has_question:
            category = "question"
        elif is_compliment:
            category = "compliment"
        elif is_positive:
            category = "positive"
        elif has_emoji:
            category = "emoji"
        else:
            category = "general"

        # انتخاب تصادفی از دسته‌ی مناسب
        comments = self.categorized_comments[category]
        return random.choice(comments)

    def auto_comment_on_hashtag(self, hashtag, count=1):
        """کامنت گذاری خودکار روی پست‌های مرتبط با هشتگ"""
        try:
            self.logger.info(f"کامنت گذاری روی #{hashtag}")

            # جستجوی پست‌های مرتبط
            medias = self.interaction_manager.search_hashtag(hashtag)

            if not medias:
                self.logger.info(f"هیچ پستی با هشتگ #{hashtag} یافت نشد")
                return 0

            # محدود کردن تعداد و انتخاب تصادفی
            if len(medias) > count:
                medias = random.sample(medias, count)

            comment_count = 0

            # کامنت‌های بسیار ساده برای کاهش خطر
            simple_comments = ["👌", "👍", "عالی", "خیلی خوب", "قشنگه", "جالبه"]

            for media in medias:
                # استراحت طولانی‌تر قبل از کامنت
                time.sleep(random.randint(20, 40))

                try:
                    username = media.user.username
                    user_id = media.user.pk

                    # انتخاب کامنت ساده و کوتاه
                    comment_text = random.choice(simple_comments)

                    # ارسال کامنت - با فرض اینکه حتی در صورت شکست، باید ادامه دهیم
                    comment_result = self.interaction_manager.comment_media(
                        media_id=media.id,
                        shortcode=media.code,
                        username=username,
                        text=comment_text
                    )

                    # حتی اگر comment_media مقدار False برگرداند، ما کار را ادامه می‌دهیم
                    # فقط برای لاگ گذاری استفاده می‌کنیم
                    if comment_result:
                        comment_count += 1

                    # استراحت طولانی بعد از هر تلاش کامنت
                    time.sleep(random.randint(60, 120))

                except Exception as e:
                    self.logger.error(f"خطا در کامنت روی پست {media.id}: {e}")
                    # استراحت کوتاه و ادامه با پست بعدی
                    time.sleep(30)
                    continue

            self.logger.info(f"✅ {comment_count} کامنت با موفقیت ارسال شد")
            return comment_count
        except Exception as e:
            self.logger.error(f"❌ خطا در کامنت گذاری خودکار: {e}")
            return 0

    def auto_comment_on_user_posts(self, username, count=3):
        """کامنت گذاری خودکار روی پست‌های یک کاربر"""
        try:
            self.logger.info(f"کامنت گذاری روی پست‌های {username}")

            # دریافت پست‌های کاربر
            user_id = self.client.user_id_from_username(username)
            medias = self.client.user_medias(user_id, count)

            if not medias:
                self.logger.info(f"هیچ پستی از کاربر {username} یافت نشد")
                return 0

            comment_count = 0

            for media in medias:
                # دریافت اطلاعات کامل پست برای کپشن
                try:
                    caption = media.caption_text if hasattr(
                        media, 'caption_text') else ""

                    # انتخاب کامنت مناسب
                    comment_text = self.get_relevant_comment(caption, username)

                    # ارسال کامنت
                    if self.interaction_manager.comment_media(
                        media_id=media.id,
                        shortcode=media.code,
                        username=username,
                        text=comment_text
                    ):
                        comment_count += 1

                    # لایک کردن پست (احتمال 80%)
                    if random.random() < 0.8:
                        self.interaction_manager.like_media(
                            media_id=media.id,
                            shortcode=media.code,
                            username=username
                        )

                    if should_take_break():
                        take_random_break(self.logger)
                except Exception as e:
                    self.logger.error(f"خطا در کامنت روی پست {media.id}: {e}")
                    continue

            self.logger.info(
                f"✅ {comment_count} کامنت با موفقیت روی پست‌های {username} ارسال شد")
            return comment_count
        except Exception as e:
            self.logger.error(
                f"❌ خطا در کامنت گذاری خودکار روی پست‌های کاربر: {e}")
            return 0
