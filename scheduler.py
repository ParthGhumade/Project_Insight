from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

tz = timezone("Asia/Kolkata")
scheduler = AsyncIOScheduler(timezone=tz)
