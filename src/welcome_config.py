import json
import os
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "welcome_config.json")

def _load():
    if not os.path.exists(CONFIG_FILE):
        return {"guilds": {}}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"guilds": {}}

def _save(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def set_welcome_channel(guild_id: int, channel_id: int) -> bool:
    data = _load()
    guild_str = str(guild_id)
    if guild_str not in data["guilds"]:
        data["guilds"][guild_str] = {}
    data["guilds"][guild_str]["welcome_channel"] = channel_id
    _save(data)
    return True

def get_welcome_channel(guild_id: int) -> int | None:
    data = _load()
    return data["guilds"].get(str(guild_id), {}).get("welcome_channel")

def set_goodbye_channel(guild_id: int, channel_id: int) -> bool:
    data = _load()
    guild_str = str(guild_id)
    if guild_str not in data["guilds"]:
        data["guilds"][guild_str] = {}
    data["guilds"][guild_str]["goodbye_channel"] = channel_id
    _save(data)
    return True

def get_goodbye_channel(guild_id: int) -> int | None:
    data = _load()
    return data["guilds"].get(str(guild_id), {}).get("goodbye_channel")

def set_welcome_message(guild_id: int, message: str) -> bool:
    data = _load()
    guild_str = str(guild_id)
    if guild_str not in data["guilds"]:
        data["guilds"][guild_str] = {}
    data["guilds"][guild_str]["welcome_message"] = message
    _save(data)
    return True

def get_welcome_message(guild_id: int) -> str | None:
    data = _load()
    return data["guilds"].get(str(guild_id), {}).get("welcome_message")

def set_goodbye_message(guild_id: int, message: str) -> bool:
    data = _load()
    guild_str = str(guild_id)
    if guild_str not in data["guilds"]:
        data["guilds"][guild_str] = {}
    data["guilds"][guild_str]["goodbye_message"] = message
    _save(data)
    return True

def get_goodbye_message(guild_id: int) -> str | None:
    data = _load()
    return data["guilds"].get(str(guild_id), {}).get("goodbye_message")

def get_guild_config(guild_id: int) -> dict:
    data = _load()
    return data["guilds"].get(str(guild_id), {})

def reset_welcome_config(guild_id: int) -> bool:
    data = _load()
    if str(guild_id) in data["guilds"]:
        del data["guilds"][str(guild_id)]
        _save(data)
    return True
