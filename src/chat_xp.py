import json
import os
from datetime import datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_xp.json")

COOLDOWN_SECONDS = 60
XP_PER_MESSAGE = 5
MAX_XP_PER_DAY = 200

LEVEL_TABLE = [
    (0, "E-Rank", "⬜"),
    (100, "D-Rank", "🟫"),
    (300, "C-Rank", "🟩"),
    (600, "B-Rank", "🟦"),
    (1000, "A-Rank", "🟪"),
    (1500, "S-Rank", "🟥"),
    (2500, "National Level", "⬛"),
]

_last_message = {}


def _load():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"users": {}}


def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def try_add_xp(user_id: int) -> dict | None:
    now = datetime.now()
    uid = str(user_id)

    # Global cooldown
    if user_id in _last_message:
        diff = (now - _last_message[user_id]).total_seconds()
        if diff < COOLDOWN_SECONDS:
            return None

    data = _load()
    if uid not in data["users"]:
        data["users"][uid] = {"xp": 0, "messages": 0, "daily": {}}

    user = data["users"][uid]

    # Daily XP cap
    today = now.strftime("%Y-%m-%d")
    today_xp = user.get("daily", {}).get(today, 0)
    if today_xp >= MAX_XP_PER_DAY:
        return None

    old_xp = user["xp"]
    user["xp"] += XP_PER_MESSAGE
    user["messages"] = user.get("messages", 0) + 1
    user["daily"][today] = today_xp + XP_PER_MESSAGE

    # Clean old daily keys (keep last 7 days)
    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    user["daily"] = {k: v for k, v in user["daily"].items() if k >= cutoff}

    _save(data)
    _last_message[user_id] = now

    old_level = get_level(old_xp)
    new_level = get_level(user["xp"])
    promoted = old_level["level"] < new_level["level"]

    return {
        "xp": user["xp"],
        "messages": user["messages"],
        "today_xp": today_xp + XP_PER_MESSAGE,
        "level": new_level,
        "promoted": promoted,
        "old_level": old_level,
    }


def get_level(xp: int) -> dict:
    current = LEVEL_TABLE[0]
    for lvl in LEVEL_TABLE:
        if xp >= lvl[0]:
            current = lvl
        else:
            break
    # Find next level
    next_level = None
    for lvl in LEVEL_TABLE:
        if lvl[0] > xp:
            next_level = lvl
            break
    return {
        "level": current,
        "next": next_level,
        "xp": xp,
    }


def get_user_data(user_id: int) -> dict:
    data = _load()
    uid = str(user_id)
    if uid not in data["users"]:
        return {"xp": 0, "messages": 0, "daily": {}}
    return data["users"][uid]


def get_leaderboard(limit: int = 10) -> list:
    data = _load()
    users = []
    for uid, udata in data["users"].items():
        users.append({
            "user_id": int(uid),
            "xp": udata["xp"],
            "messages": udata.get("messages", 0),
        })
    users.sort(key=lambda x: x["xp"], reverse=True)
    return users[:limit]
