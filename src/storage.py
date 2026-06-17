import json
import os
from datetime import date, datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "journal.json")

def _load():
    if not os.path.exists(DATA_FILE):
        return {"entries": [], "next_id": 1, "last_hud_messages": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {}
        if "entries" not in data:
            data["entries"] = []
        if "next_id" not in data:
            data["next_id"] = 1
        if "last_hud_messages" not in data:
            data["last_hud_messages"] = {}
        return data

def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_entry(text: str, entry_date: str = None, entry_time: str = None) -> dict:
    data = _load()
    now = datetime.now()
    entry = {
        "id": data["next_id"],
        "date": entry_date or now.strftime("%Y-%m-%d"),
        "time": entry_time or now.strftime("%H:%M:%S"),
        "text": text.strip(),
        "created_at": now.isoformat()
    }
    data["entries"].append(entry)
    data["next_id"] += 1
    _save(data)
    return entry

def get_by_date(date_str: str) -> list:
    data = _load()
    return [e for e in data["entries"] if e["date"] == date_str]

def get_today() -> list:
    return get_by_date(date.today().isoformat())

def get_yesterday() -> list:
    from datetime import timedelta
    d = (date.today() - timedelta(days=1)).isoformat()
    return get_by_date(d)

def search(keyword: str) -> list:
    data = _load()
    kw = keyword.lower()
    return [e for e in data["entries"] if kw in e["text"].lower()]

def get_all_entries() -> list:
    data = _load()
    return data["entries"]

def get_all_dates() -> list:
    data = _load()
    dates = {}
    for e in data["entries"]:
        dates[e["date"]] = dates.get(e["date"], 0) + 1
    return sorted(dates.items(), reverse=True)

def get_stats() -> dict:
    data = _load()
    entries = data["entries"]
    if not entries:
        return {"total": 0, "days": 0, "first_date": None, "last_date": None}
    dates = sorted(set(e["date"] for e in entries))
    return {
        "total": len(entries),
        "days": len(dates),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None
    }

def get_entry_count() -> int:
    return _load()["next_id"] - 1

def delete_entry(entry_id: int) -> bool:
    data = _load()
    for i, e in enumerate(data["entries"]):
        if e["id"] == entry_id:
            data["entries"].pop(i)
            _save(data)
            return True
    return False

def clear_all():
    data = {"entries": [], "next_id": 1, "last_hud_messages": {}}
    _save(data)

def get_last_hud_message(channel_id: int) -> int | None:
    data = _load()
    return data.get("last_hud_messages", {}).get(str(channel_id))

def set_last_hud_message(channel_id: int, message_id: int):
    data = _load()
    if "last_hud_messages" not in data:
        data["last_hud_messages"] = {}
    data["last_hud_messages"][str(channel_id)] = message_id
    _save(data)
