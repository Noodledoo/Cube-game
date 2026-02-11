"""
FILE: core/config.py
Configuration with proper ability initialization and network settings
Supports both singleplayer and multiplayer save files
"""

import json
import os

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SAVE_FILE = "boss_fight_save.json"
MULTIPLAYER_SAVE_FILE = "boss_fight_multiplayer_save.json"

# Default save data
DEFAULT_SAVE = {
    "max_level": 1,
    "coins": 0,
    "upgrades": {
        "damage": 1,
        "firerate": 1,
        "health": 1,
        "triple": False,
        "rapid": False,
        "shield": False,
        "piercing": False,
        "lifesteal": False,
        "speed": 1,
        "multishot": 1,
        "crit": False,
        "regen": False,
        "ultradamage": 1,
        "megashield": False,
        "timeslow": False,
        "explosive": False,
        "vampire": False,
        "berserker": False,
        "goldenheart": 1,
        "lasernull": False,
        "godmode": False,
        "reflect": False,
        "immortal": False,
        "berserker_sqr": False,
        "nuclearshot": False,
        "infiniteammo": False,
        "titanshield": False,
        "voidwalker": False,
        "parry": False,
        "bulletstorm": False,
        "homingrounds": False,
    },
    "abilities": {
        "teleport": 0,
        "dash": 0,
        "timeshatter": 0,
        "shockwave": 0,
        "chaos_bargain": 0,
        "chronoking": 0,
        "singularity": 0
    },
    "ability_picks_used": 0,
    "settings": {
        "theme": "dark",
        "movement": "mouse",
        "colorblind": False,
        "admin": False
    },
    "network": {
        "last_server": "",
        "player_name": "Player",
        "preferred_port": 5555
    }
}

# Default multiplayer save data (extends base save with MP-specific fields)
DEFAULT_MULTIPLAYER_SAVE = {
    **DEFAULT_SAVE,
    "multiplayer_stats": {
        "games_played": 0,
        "games_won": 0,
        "total_damage_dealt": 0,
        "bosses_killed": 0,
        "deaths": 0,
        "time_played_seconds": 0
    },
    "multiplayer_unlocks": {
        "titles": ["Newcomer"],
        "active_title": "Newcomer"
    }
}

def _load_save_from_file(filepath: str, default_data: dict) -> dict:
    """Internal helper to load save data from a specific file"""
    if not os.path.exists(filepath):
        return json.loads(json.dumps(default_data))
    
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except:
        return json.loads(json.dumps(default_data))

    # Merge with defaults for new fields
    for key in default_data:
        if key not in data:
            data[key] = json.loads(json.dumps(default_data[key]))
    
    # Ensure all upgrades exist
    if "upgrades" not in data:
        data["upgrades"] = json.loads(json.dumps(default_data["upgrades"]))
    else:
        for key in default_data["upgrades"]:
            if key not in data["upgrades"]:
                data["upgrades"][key] = default_data["upgrades"][key]
    
    # Ensure all abilities exist
    if "abilities" not in data:
        data["abilities"] = json.loads(json.dumps(default_data["abilities"]))
    else:
        for key in default_data["abilities"]:
            if key not in data["abilities"]:
                data["abilities"][key] = default_data["abilities"][key]
    
    # Ensure ability_picks_used exists
    if "ability_picks_used" not in data:
        data["ability_picks_used"] = 0
    
    # Ensure settings exist
    if "settings" not in data:
        data["settings"] = json.loads(json.dumps(default_data["settings"]))
    else:
        for key in default_data["settings"]:
            if key not in data.get("settings", {}):
                if "settings" not in data:
                    data["settings"] = {}
                data["settings"][key] = default_data["settings"][key]
    
    # Ensure network settings exist
    if "network" not in data:
        data["network"] = json.loads(json.dumps(default_data["network"]))
    else:
        for key in default_data["network"]:
            if key not in data["network"]:
                data["network"][key] = default_data["network"][key]

    return data

def load_save():
    """Load singleplayer save data from file"""
    return _load_save_from_file(SAVE_FILE, DEFAULT_SAVE)

def load_multiplayer_save():
    """Load multiplayer save data from file"""
    data = _load_save_from_file(MULTIPLAYER_SAVE_FILE, DEFAULT_MULTIPLAYER_SAVE)
    
    # Ensure multiplayer-specific fields exist
    if "multiplayer_stats" not in data:
        data["multiplayer_stats"] = json.loads(json.dumps(DEFAULT_MULTIPLAYER_SAVE["multiplayer_stats"]))
    else:
        for key in DEFAULT_MULTIPLAYER_SAVE["multiplayer_stats"]:
            if key not in data["multiplayer_stats"]:
                data["multiplayer_stats"][key] = DEFAULT_MULTIPLAYER_SAVE["multiplayer_stats"][key]
    
    if "multiplayer_unlocks" not in data:
        data["multiplayer_unlocks"] = json.loads(json.dumps(DEFAULT_MULTIPLAYER_SAVE["multiplayer_unlocks"]))
    else:
        for key in DEFAULT_MULTIPLAYER_SAVE["multiplayer_unlocks"]:
            if key not in data["multiplayer_unlocks"]:
                data["multiplayer_unlocks"][key] = DEFAULT_MULTIPLAYER_SAVE["multiplayer_unlocks"][key]
    
    return data

def save_progress(data, multiplayer: bool = False):
    """Save data to file (singleplayer or multiplayer)"""
    filepath = MULTIPLAYER_SAVE_FILE if multiplayer else SAVE_FILE
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def save_multiplayer_progress(data):
    """Save multiplayer data to file"""
    save_progress(data, multiplayer=True)

def reset_save(multiplayer: bool = False):
    """Reset save to defaults"""
    if multiplayer:
        data = json.loads(json.dumps(DEFAULT_MULTIPLAYER_SAVE))
        save_progress(data, multiplayer=True)
    else:
        data = json.loads(json.dumps(DEFAULT_SAVE))
        save_progress(data, multiplayer=False)
    return data

def reset_multiplayer_save():
    """Reset multiplayer save to defaults"""
    return reset_save(multiplayer=True)

def update_multiplayer_stats(data, games_won: int = 0, damage_dealt: float = 0, 
                             bosses_killed: int = 0, deaths: int = 0, 
                             time_played: float = 0):
    """Update multiplayer statistics"""
    stats = data.get("multiplayer_stats", {})
    stats["games_played"] = stats.get("games_played", 0) + 1
    stats["games_won"] = stats.get("games_won", 0) + games_won
    stats["total_damage_dealt"] = stats.get("total_damage_dealt", 0) + damage_dealt
    stats["bosses_killed"] = stats.get("bosses_killed", 0) + bosses_killed
    stats["deaths"] = stats.get("deaths", 0) + deaths
    stats["time_played_seconds"] = stats.get("time_played_seconds", 0) + time_played
    data["multiplayer_stats"] = stats
    
    # Check for title unlocks
    _check_title_unlocks(data)
    
    return data

def _check_title_unlocks(data):
    """Check and unlock titles based on stats"""
    stats = data.get("multiplayer_stats", {})
    unlocks = data.get("multiplayer_unlocks", {"titles": ["Newcomer"], "active_title": "Newcomer"})
    
    titles = unlocks.get("titles", ["Newcomer"])
    
    # Unlock titles based on achievements
    if stats.get("games_won", 0) >= 1 and "Victor" not in titles:
        titles.append("Victor")
    if stats.get("games_won", 0) >= 10 and "Champion" not in titles:
        titles.append("Champion")
    if stats.get("games_won", 0) >= 50 and "Legend" not in titles:
        titles.append("Legend")
    if stats.get("bosses_killed", 0) >= 5 and "Boss Slayer" not in titles:
        titles.append("Boss Slayer")
    if stats.get("bosses_killed", 0) >= 25 and "Boss Hunter" not in titles:
        titles.append("Boss Hunter")
    if stats.get("total_damage_dealt", 0) >= 10000 and "Damage Dealer" not in titles:
        titles.append("Damage Dealer")
    if stats.get("total_damage_dealt", 0) >= 100000 and "Destroyer" not in titles:
        titles.append("Destroyer")
    if stats.get("games_played", 0) >= 100 and "Veteran" not in titles:
        titles.append("Veteran")
    
    unlocks["titles"] = titles
    data["multiplayer_unlocks"] = unlocks

