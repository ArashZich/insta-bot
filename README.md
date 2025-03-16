
# Instagram Bot

بات هوشمند اینستاگرام برای تعامل خودکار و افزایش فالوور

## ویژگی های اصلی

- لایک کردن خودکار پست ها
- کامنت گذاری هوشمند
- فالو و آنفالو خودکار
- مشاهده استوری
- ارسال پیام مستقیم
- تعامل بر اساس هشتگ
- رفتار انسانی با استراحت های تصادفی
- ثبت آمار و گزارش عملکرد
- مدیریت خودکار محدودیت‌های اینستاگرام
- بازیابی خودکار از چالش‌های اینستاگرام
- مکانیزم واچ‌داگ برای اطمینان از پایداری سرویس

## معماری سیستم

```mermaid
flowchart TD
    A[Main App] --> B[Session Manager]
    A --> C[API Endpoints]
    B --> D[Interaction Manager]
    B --> E[Follower Manager]
    B --> F[Comment Manager]
    A --> G[Automated Bot]
    G --> D
    G --> E
    G --> F
    C --> A
    H[Database] <--> A
    I[Watchdog] --> A
```

## راه اندازی

### پیش نیازها

- Docker و Docker Compose
- حساب کاربری اینستاگرام 

### مراحل نصب

1. کلون کردن مخزن:
```bash
git clone https://github.com/yourusername/instagram-bot.git
cd instagram-bot
```

2. ایجاد فایل `.env`:
```
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
```

3. راه اندازی با Docker:
```bash
docker-compose up -d
```

4. بررسی وضعیت:
```bash
docker logs instagram_bot -f
```

## شروع کار خودکار

بات به صورت پیش فرض پس از راه اندازی به حالت خودکار می رود. اما می توانید با API های زیر آن را کنترل کنید:

```bash
# شروع بات و حالت خودکار
curl -X POST http://localhost:8000/start

# بررسی وضعیت
curl http://localhost:8000/status

# بررسی سلامت سرویس
curl http://localhost:8000/health

# توقف بات
curl -X POST http://localhost:8000/stop

# روشن/خاموش کردن حالت خودکار
curl -X POST http://localhost:8000/auto-mode/on
curl -X POST http://localhost:8000/auto-mode/off
```

## چرخه کاری بات

```mermaid
stateDiagram-v2
    [*] --> Login
    Login --> AutomatedMode
    
    AutomatedMode --> ActivityCycle
    ActivityCycle --> HashtagInteraction
    ActivityCycle --> FollowUsers
    ActivityCycle --> UnfollowUsers
    ActivityCycle --> FollowBack
    ActivityCycle --> CommentPosts
    ActivityCycle --> ViewStories
    ActivityCycle --> SendDMs
    
    HashtagInteraction --> RestPeriod
    FollowUsers --> RestPeriod
    UnfollowUsers --> RestPeriod
    FollowBack --> RestPeriod
    CommentPosts --> RestPeriod
    ViewStories --> RestPeriod
    SendDMs --> RestPeriod
    
    RestPeriod --> ActivityCycle
    
    AutomatedMode --> [*]: Stop Bot
    
    state RestPeriod {
        [*] --> ShortBreak
        ShortBreak --> [*]
        ShortBreak --> LongBreak: محدودیت یا خطاها
        LongBreak --> [*]
    }
    
    state ErrorHandling {
        Challenge --> PauseActivity
        PauseActivity --> Relogin
        Relogin --> AutomatedMode: موفق
        Relogin --> Retry: ناموفق
        Retry --> Relogin
    }
```

## مکانیزم پایداری و خودبازیابی

بات از چندین مکانیزم برای افزایش پایداری استفاده می‌کند:

1. **مدیریت خودکار چالش‌ها**: تشخیص و مدیریت چالش‌های اینستاگرام
2. **استراحت هوشمند**: تنظیم خودکار زمان استراحت براساس خطاها و محدودیت‌ها
3. **سیستم واچ‌داگ**: نظارت دائمی بر سلامت سرویس و راه‌اندازی مجدد خودکار در صورت بروز مشکل
4. **محدودیت‌های روزانه**: مدیریت هوشمند محدودیت‌های روزانه برای جلوگیری از بلاک شدن
5. **ذخیره و بازیابی سشن**: حفظ سشن برای کاهش نیاز به لاگین مکرر

## API های موجود

### مدیریت بات

| آدرس | متد | توضیحات |
|------|------|----------|
| `/start` | POST | راه اندازی بات |
| `/stop` | POST | توقف بات |
| `/status` | GET | دریافت وضعیت بات |
| `/health` | GET | بررسی سلامت سرویس |
| `/auto-mode/{state}` | POST | تنظیم حالت خودکار (on/off) |

### آمار و اطلاعات

| آدرس | متد | توضیحات |
|------|------|----------|
| `/api/stats/daily` | GET | آمار روزانه بات |
| `/api/stats/weekly` | GET | آمار هفتگی بات |
| `/api/stats/monthly` | GET | آمار ماهیانه بات |
| `/api/stats/summary` | GET | خلاصه آماری بات |

### مدیریت تعاملات

| آدرس | متد | توضیحات |
|------|------|----------|
| `/api/interactions/recent` | GET | تعاملات اخیر |
| `/api/interactions/by-type/{type}` | GET | تعاملات بر اساس نوع |
| `/api/interactions/by-username/{username}` | GET | تعاملات با یک کاربر خاص |
| `/api/interactions/filter` | GET | فیلتر کردن تعاملات |
| `/api/interactions/summary` | GET | خلاصه تعاملات |
| `/api/interactions/most-interacted` | GET | کاربران با بیشترین تعامل |

## نحوه کارکرد

```mermaid
sequenceDiagram
    participant User
    participant Bot
    participant Instagram
    participant Database
    participant Watchdog
    
    User->>Bot: /start
    Bot->>Instagram: Login
    Instagram-->>Bot: Session
    Bot->>Database: Record Session
    Bot->>Bot: Start Automated Cycle
    
    loop EveryActivityCycle
        Bot->>Bot: Select Activities
        Bot->>Instagram: Interact (Like/Comment)
        Instagram-->>Bot: Results/Challenges
        
        alt Challenge Detected
            Bot->>Bot: Pause & Handle Challenge
            Bot->>Instagram: Relogin
        end
        
        Bot->>Database: Record Interactions
        Bot->>Bot: Smart Break
    end
    
    par Continuous Monitoring
        Watchdog->>Bot: Health Check
        alt Service Down
            Watchdog->>Bot: Restart Service
        end
    end
    
    User->>Bot: /status
    Bot-->>User: Current Status
    
    User->>Bot: /stop
    Bot->>Bot: Stop Cycle
    Bot->>Database: Record End
    Bot-->>User: Stopped
```

## تنظیمات پیشرفته

تنظیمات بات در فایل `app/config.py` قرار دارد:

- `MIN_ACTION_DELAY` و `MAX_ACTION_DELAY`: تاخیر بین عملیات‌ها (ثانیه)
- `MIN_BREAK_TIME` و `MAX_BREAK_TIME`: زمان استراحت (دقیقه)
- `ACTIVITY_WEIGHTS`: اولویت بندی فعالیت‌ها
- `DAILY_LIKE_LIMIT`: محدودیت روزانه لایک
- `DAILY_COMMENT_LIMIT`: محدودیت روزانه کامنت
- `DAILY_FOLLOW_LIMIT`: محدودیت روزانه فالو
- `DAILY_UNFOLLOW_LIMIT`: محدودیت روزانه آنفالو
- `DAILY_DM_LIMIT`: محدودیت روزانه پیام مستقیم

## سفارشی سازی محتوا

- کامنت‌ها: ویرایش فایل `data/comments.json`
- هشتگ‌ها: ویرایش فایل `data/hashtags.json`

## سیستم واچ‌داگ

بات از یک سرویس واچ‌داگ برای نظارت بر سلامت خود استفاده می‌کند. این سرویس:

- به طور مداوم وضعیت سرویس اصلی را بررسی می‌کند
- در صورت عدم پاسخگویی، به طور خودکار سرویس را راه‌اندازی مجدد می‌کند
- لاگ‌های مربوط به نظارت را در `data/watchdog.log` ذخیره می‌کند

این مکانیزم اطمینان می‌دهد که حتی در صورت قفل شدن یا از کار افتادن سرویس، بات به طور خودکار بازیابی شود.

## عیب‌یابی

- **خطای Challenge Required**: این خطا نشانگر محدودیت اینستاگرام است. بات به طور خودکار سعی در مدیریت آن می‌کند.
- **خطای دسترسی به API**: بررسی کنید که واچ‌داگ فعال باشد. در `/health` وضعیت سرویس را چک کنید.
- **مشکلات احراز هویت**: در فایل `.env` نام کاربری و رمز عبور را بررسی کنید و از فایل لاگ `data/bot.log` خطاها را پیگیری کنید.