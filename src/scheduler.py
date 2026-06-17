import json
import os
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reminders.json")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})

job_map = {}

def _load_reminders():
    if not os.path.exists(SCHEDULE_FILE):
        return {"reminders": [], "next_id": 1}
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_reminders(data):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def send_reminder(bot, target_id, text, rid=None):
    msg = f"⏰ **Reminder**\n\n{text}"
    try:
        # Try to send to channel
        channel = bot.get_channel(target_id)
        if not channel:
            try:
                channel = await bot.fetch_channel(target_id)
            except Exception:
                channel = None
        
        if channel:
            await channel.send(msg)
        else:
            # Try to send DM to user
            user = bot.get_user(target_id)
            if not user:
                try:
                    user = await bot.fetch_user(target_id)
                except Exception:
                    user = None
            if user:
                await user.send(msg)
    except Exception as e:
        logger.error(f"Failed to send reminder to {target_id}: {e}")

    if rid is not None:
        try:
            data = _load_reminders()
            for r in data["reminders"]:
                if r["id"] == rid and not r["repeat"]:
                    r["active"] = False
                    _save_reminders(data)
                    logger.info(f"One-time reminder #{rid} completed and deactivated.")
                    break
        except Exception as e:
            logger.error(f"Failed to deactivate one-time reminder #{rid}: {e}")

def add_reminder(bot, target_id: int, text: str, remind_at: datetime, repeat: str = None) -> dict:
    data = _load_reminders()
    rid = data["next_id"]
    entry = {
        "id": rid,
        "chat_id": target_id, # Keep key 'chat_id' for back-compatibility with schema
        "text": text,
        "remind_at": remind_at.isoformat(),
        "repeat": repeat,
        "created_at": datetime.now().isoformat(),
        "active": True,
    }
    data["reminders"].append(entry)
    data["next_id"] += 1
    _save_reminders(data)

    job_id = f"reminder_{rid}"
    if repeat == "daily":
        trigger = CronTrigger(hour=remind_at.hour, minute=remind_at.minute)
    elif repeat == "weekly":
        trigger = CronTrigger(day_of_week=remind_at.weekday(), hour=remind_at.hour, minute=remind_at.minute)
    elif repeat:
        parts = repeat.lower().replace("every ", "").split()
        if len(parts) >= 2 and parts[1] in ("minute", "minutes", "hour", "hours"):
            val = int(parts[0])
            unit = parts[1]
            if "hour" in unit:
                trigger = IntervalTrigger(hours=val)
            else:
                trigger = IntervalTrigger(minutes=val)
        else:
            trigger = DateTrigger(run_date=remind_at)
    else:
        trigger = DateTrigger(run_date=remind_at)

    scheduler.add_job(
        send_reminder,
        trigger=trigger,
        args=[bot, target_id, text, rid],
        id=job_id,
        replace_existing=True,
    )
    job_map[rid] = job_id
    return entry

def remove_reminder(rid: int) -> bool:
    data = _load_reminders()
    for r in data["reminders"]:
        if r["id"] == rid:
            r["active"] = False
            _save_reminders(data)
            job_id = job_map.pop(rid, None)
            if job_id:
                scheduler.remove_job(job_id)
            return True
    return False

def get_reminders(target_id: int = None) -> list:
    data = _load_reminders()
    reminders = [r for r in data["reminders"] if r["active"]]
    if target_id:
        reminders = [r for r in reminders if r["chat_id"] == target_id]
    return reminders

def restore_reminders(bot):
    data = _load_reminders()
    for r in data["reminders"]:
        if not r["active"]:
            continue
        rid = r["id"]
        remind_at = datetime.fromisoformat(r["remind_at"])
        now = datetime.now()
        if remind_at <= now and not r["repeat"]:
            continue
        repeat = r["repeat"]
        job_id = f"reminder_{rid}"
        if repeat == "daily":
            trigger = CronTrigger(hour=remind_at.hour, minute=remind_at.minute)
        elif repeat == "weekly":
            trigger = CronTrigger(day_of_week=remind_at.weekday(), hour=remind_at.hour, minute=remind_at.minute)
        elif repeat:
            parts = repeat.lower().replace("every ", "").split()
            if len(parts) >= 2 and parts[1] in ("minute", "minutes", "hour", "hours"):
                val = int(parts[0])
                unit = parts[1]
                if "hour" in unit:
                    trigger = IntervalTrigger(hours=val)
                else:
                    trigger = IntervalTrigger(minutes=val)
            else:
                continue
        else:
            if remind_at <= now:
                continue
            trigger = DateTrigger(run_date=remind_at)

        scheduler.add_job(
            send_reminder,
            trigger=trigger,
            args=[bot, r["chat_id"], r["text"], rid],
            id=job_id,
            replace_existing=True,
        )
        job_map[rid] = job_id
