import json
import os
from typing import Dict

import sys

def get_config_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.getcwd()

CONFIG_FILE = os.path.join(get_config_path(), "config.json")

DEFAULT_CONFIG = {
    "adb_host": "",
    "adb_port": 5555,
    "tmdb_api_key": "",
    "discord_client_id": "1451010126495617106",
    "discord_wako_client_id": "",
    "update_interval": 2.0,
    "aniskip_enabled": False,
    "mal_client_id": "",
    # Skip Provider Defaults
    "skip_tmdb_id": "",          # Manual TMDB ID for IntroDB
    "skip_mal_id": "",           # Manual MAL ID for AniSkip
    "introhater_enabled": True,
    "introdb_enabled": True,       # IntroSkip (IntroDB API)
    "aniskip_fallback": True,
    "tidb_enabled": False,
    "tidb_api_key": "",
    "remote_json_enabled": False,
    "remote_json_url": "https://busy-jacinta-shugi-c2885b2e.koyeb.app/download-db",
    "videoskip_enabled": False,
    "jumpscare_major_enabled": False,
    "jumpscare_minor_enabled": False,
    "skip_priority_order": ["introdb", "tidb", "introhater", "remote_json", "videoskip", "jumpscare_major", "jumpscare_minor", "aniskip"],
    "wako_mode": False,           # Wako Telemetry Mode (UI scraping via uiautomator)
    # Phase 1: Auto-Play Next
    "autoplay_next_enabled": True,
    # Phase 3: Smart Home Lighting
    "smart_home_enabled": False,
    "smart_home_provider": "webhook",  # "webhook", "hue", "homeassistant"
    "smart_home_play_url": "",
    "smart_home_pause_url": "",
    "hue_bridge_ip": "",
    "hue_api_key": "",
    "hue_group_id": "0",
    "hue_dim_brightness": 25,
    "ha_url": "",
    "ha_token": "",
    "ha_entity": "light.living_room",
    "ha_dim_brightness": 25,
    # Phase 4: Watch Party
    "watch_party_enabled": False,
    "watch_party_mode": "off",
    "watch_party_port": 5467,
    "watch_party_host_ip": "",
    # RPC Enhancements
    "rpc_buttons_enabled": True,
    "rpc_streaming_mode": True,
    "rpc_custom_status": "",
    "rpc_time_display": "remaining", # "remaining" or "elapsed"
    "rpc_large_image_mode": "season", # "show", "season", "episode"
    "rpc_rating_badges_enabled": False,
    "rpc_status_cycling_enabled": False,
    "rpc_status_effects_enabled": False,
    "rpc_small_icon_mode": "play_status" # "play_status", "ascend_rpc", "wako", "device", "streaming_service"
}

def load_config() -> Dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG) # Save it immediately so user sees it
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, 'r') as f:
            file_config = json.load(f)
            # Merge: Use default for missing keys
            config = DEFAULT_CONFIG.copy()
            config.update(file_config)
            return config
    except:
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
