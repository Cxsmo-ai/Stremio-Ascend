
from flask import Flask, render_template, jsonify, request
import logging
import threading
import time
import sys
import os

# Disable Flask Banner
cli = logging.getLogger('werkzeug')
cli.setLevel(logging.ERROR)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
gui_app = None # Reference to the main GUI App instance

import traceback

def run_server(main_app_instance):
    global gui_app
    gui_app = main_app_instance
    try:
        # Run on 0.0.0.0 to allow access from local network
        app.run(host="0.0.0.0", port=5466, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Web Server Failed: {e}")
        traceback.print_exc()

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/state")
def get_state():
    if not gui_app: return jsonify({"error": "No App"}), 500
    
    try:
        # Read from thread-safe dict (shared_state) which app.py updates
        s = gui_app.shared_state
        return jsonify({
            # Base State
            "connected": s.get("connected", False),
            "device": s.get("device", "Disconnected"),
            "title": s.get("title", "Ready"),
            "subtitle": s.get("subtitle", ""),
            "progress": s.get("progress", 0),
            "position": s.get("position", 0),  # Position in ms
            "duration": s.get("duration", 0),  # Duration in ms
            "image_url": s.get("image_url"),
            
            # Additional State for UI Logic
            "is_playing": s.get("is_playing", False),
            "auto_skip": gui_app.skip_manager.enabled, 
            
            # Current Configuration (for populating Settings inputs)
            "config": {
                "adb_host": gui_app.config.get("adb_host", ""),
                "tmdb_key": gui_app.config.get("tmdb_api_key", ""),
                "mal_id": gui_app.config.get("mal_client_id", ""),
                "trakt_id": gui_app.config.get("trakt_client_id", ""),
                "trakt_secret": gui_app.config.get("trakt_client_secret", ""),
                "discord_id": gui_app.config.get("discord_client_id", ""),
                "discord_wako_id": gui_app.config.get("discord_wako_client_id", ""),
                "show_device": gui_app.config.get("show_device_name", True),
                "profanity": gui_app.config.get("profanity_filter", False),
                "aniskip_enabled": gui_app.config.get("aniskip_enabled", True),
                "aniskip_smart": gui_app.config.get("aniskip_smart", False),
                "skip_mode": gui_app.config.get("skip_mode", "auto"),
                # Skip Sources Config
                "skip_tmdb_id": gui_app.config.get("skip_tmdb_id", ""),
                "skip_mal_id": gui_app.config.get("skip_mal_id", ""),
                "introhater_enabled": gui_app.config.get("introhater_enabled", True),
                "introdb_enabled": gui_app.config.get("introdb_enabled", True),
                "aniskip_fallback": gui_app.config.get("aniskip_fallback", True),
                "tidb_enabled": gui_app.config.get("tidb_enabled", False),
                "tidb_api_key": gui_app.config.get("tidb_api_key", ""),
                "remote_json_enabled": gui_app.config.get("remote_json_enabled", False),
                "remote_json_url": gui_app.config.get("remote_json_url", ""),
                "videoskip_enabled": gui_app.config.get("videoskip_enabled", False),
                "jumpscare_major_enabled": gui_app.config.get("jumpscare_major_enabled", False),
                "jumpscare_minor_enabled": gui_app.config.get("jumpscare_minor_enabled", False),
                "skip_priority_order": gui_app.config.get("skip_priority_order", ["introdb", "tidb", "introhater", "remote_json", "videoskip", "jumpscare", "aniskip"]),
                "watch_party_host_ip": gui_app.config.get("watch_party_host_ip", ""),
                "wako_mode": gui_app.config.get("wako_mode", False),
                # RPC Enhancements
                "rpc_buttons": gui_app.config.get("rpc_buttons_enabled", True),
                "rpc_streaming": gui_app.config.get("rpc_streaming_mode", True),
                "rpc_status": gui_app.config.get("rpc_custom_status", ""),
                "rpc_time": gui_app.config.get("rpc_time_display", "remaining"),
                "rpc_rating_badges": gui_app.config.get("rpc_rating_badges_enabled", False),
                "rpc_status_cycling": gui_app.config.get("rpc_status_cycling_enabled", False),
                "rpc_status_effects": gui_app.config.get("rpc_status_effects_enabled", False),
                "rpc_small_icon": gui_app.config.get("rpc_small_icon_mode", "play_status"),
                "rpc_large_image": gui_app.config.get("rpc_large_image_mode", "season")
            },
            
            # Stats (Live from StatsManager)
            "stats": {
                "skips": gui_app.stats.get("skips", 0),
                "saved": gui_app.stats.get("saved", 0),
                "syncs": gui_app.stats.get("trakt", 0)
            },

            # Skipped Catalog
            "history": gui_app.history.get_all(),

            # Debug / Metadata
            "skip_status": {
                "msg": s.get("skip_status_msg", ""),
                "color": s.get("skip_status_color", "gray")
            },
            
            # API Status for Badges
            "api_status": s.get("api_status", {
                "discord": False, 
                "trakt": False, 
                "adb": False, 
                "metadata": False
            }),
            
            # Application Logs
            "logs": s.get("logs", []),
            
            # ADB Scan Results
            "scan_results": s.get("scan_results", [])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings", methods=["POST"])
def update_settings():
    if not gui_app: return jsonify({"error": "No App"}), 500
    try:
        data = request.json
        action = data.get("action")
        
        if action == "connect":
            # Just config update + connect logic
            if "adb_host" in data: 
                gui_app.update_config("adb_host", data["adb_host"])
                gui_app.connect_adb()
                
        elif action == "update":
            # Generic update for any key provided
            for key, val in data.items():
                if key == "action": continue
                
                # Map frontend keys to backend config keys
                config_key = key
                if key == "tmdb": config_key = "tmdb_api_key"
                if key == "mal": config_key = "mal_client_id"
                if key == "trakt": config_key = "trakt_client_id"
                if key == "trakt_secret": config_key = "trakt_client_secret"
                if key == "discord": config_key = "discord_client_id"
                if key == "discord_wako": config_key = "discord_wako_client_id"
                # RPC config mappings
                if key == "rpc_rating_badges": config_key = "rpc_rating_badges_enabled"
                if key == "rpc_status_cycling": config_key = "rpc_status_cycling_enabled"
                if key == "rpc_status_effects": config_key = "rpc_status_effects_enabled"
                if key == "rpc_large_image": config_key = "rpc_large_image_mode"

                # Update Config - all skip and insane RPC keys are valid
                skip_config_keys = ["show_device_name", "profanity_filter", "aniskip_enabled", "aniskip_smart",
                                   "introhater_enabled", "introdb_enabled", "aniskip_fallback", 
                                   "skip_tmdb_id", "skip_mal_id", "wako_mode", 
                                   "rpc_personas", "rpc_rating_badges_enabled", "rpc_status_cycling_enabled", "rpc_status_effects_enabled",
                                   "rpc_small_icon_mode"]
                if config_key in gui_app.config or key in skip_config_keys:
                    gui_app.config[config_key] = val
                    
                # Live Updates for skip manager
                if key == "aniskip_smart": gui_app.skip_manager.smart_mode = val
                if key == "aniskip_enabled": gui_app.skip_manager.enabled = val
                if key == "introhater_enabled": gui_app.skip_manager.introhater_enabled = val
                if key == "introdb_enabled": gui_app.skip_manager.introdb_enabled = val
                if key == "aniskip_fallback": gui_app.skip_manager.aniskip_fallback = val
                if key == "tidb_enabled": gui_app.skip_manager.tidb_enabled = val
                if key == "remote_json_enabled": gui_app.skip_manager.remote_json_enabled = val
                if key == "videoskip_enabled": gui_app.skip_manager.videoskip_enabled = val
                if key == "jumpscare_major_enabled": gui_app.skip_manager.jumpscare_major_enabled = val
                if key == "jumpscare_minor_enabled": gui_app.skip_manager.jumpscare_minor_enabled = val
                if key == "skip_priority_order": gui_app.skip_manager.skip_priority_order = val
                if key == "skip_tmdb_id": gui_app.skip_manager.manual_tmdb_id = val
                if key == "skip_mal_id": gui_app.skip_manager.manual_mal_id = val
                if key == "skip_mode":
                     gui_app.skip_manager.enabled = (val != "off")
            
            gui_app.save_settings()
            
            # Trigger updates for specific items
            if "tmdb_api_key" in gui_app.config:
                gui_app.tmdb_key = gui_app.config["tmdb_api_key"]
            
            # Live refresh Trakt client credentials
            if gui_app.config.get("trakt_client_id"):
                gui_app.trakt.client_id = gui_app.config["trakt_client_id"]
                gui_app.trakt.headers["trakt-api-key"] = gui_app.config["trakt_client_id"]
            if gui_app.config.get("trakt_client_secret"):
                gui_app.trakt.client_secret = gui_app.config["trakt_client_secret"]
                
            # Live refresh Discord Client ID based on wako mode
            if "discord_client_id" in data or "discord_wako" in data or "wako_mode" in data:
                # App logic determines which ID to use in the update loop, but we can force clear it or just let the app handle it.
                pass
                
        return jsonify({"status": "ok"})
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app.route("/api/command", methods=["POST"])
def send_command():
    if not gui_app: return jsonify({"error": "No App"}), 500
    
    cmd = request.json.get("command")
    
    if cmd == "play_pause": gui_app.play_pause()
    elif cmd == "stop": gui_app.stop_playback()
    elif cmd == "next": gui_app.next_track()
    elif cmd == "prev": gui_app.prev_track()
    elif cmd == "seek_fwd": gui_app.seek_forward()
    elif cmd == "seek_back": gui_app.seek_backward()
    elif cmd == "toggle_skip": gui_app.toggle_skip()
    elif cmd == "seek_to":
        target = request.json.get("target")
        if target is not None: gui_app.seek_to(int(target))
    elif cmd == "restart": gui_app.restart_app()
    elif cmd == "start_rpc": gui_app.rpc.connect() # simplified
    elif cmd == "stop_rpc": gui_app.rpc.close()
    elif cmd == "scan_network": gui_app.scan_network()
    elif cmd == "trakt_auth":
        return jsonify(gui_app.start_trakt_auth())
    
    # Open URL command for "Link Handling"
    elif cmd == "open_url":
        url = request.json.get("url")
        if url:
            import webbrowser
            webbrowser.open(url)
            
    return jsonify({"status": "ok"})

@app.route("/api/trakt/lists")
def get_trakt_lists():
    if not gui_app: return jsonify({"error": "No App"}), 500
    lists = gui_app.trakt.get_user_lists()
    return jsonify(lists)

@app.route("/api/trakt/list_items")
def get_trakt_list_items():
    if not gui_app: return jsonify({"error": "No App"}), 500
    list_id = request.args.get('id')
    user = request.args.get('user', 'me')
    
    if not list_id: return jsonify([])
    
    items = gui_app.trakt.get_list_items(list_id, user)
    return jsonify(items)

@app.route('/api/remote/<string:key>', methods=['POST'])
def remote_control(key):
    if not gui_app: return jsonify({"error": "No App"}), 500
    
    key_map = {
        "up": 19,
        "down": 20,
        "left": 21,
        "right": 22,
        "center": 23, # DPAD_CENTER
        "back": 4,    # KEYCODE_BACK
        "home": 3,
        "menu": 82,
        "vol_up": 24,
        "vol_down": 25,
        "mute": 164
    }
    
    if key in key_map:
        gui_app.controller.send_key(key_map[key])
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid key"}), 400

@app.route("/api/launch", methods=["POST"])
def launch_content():
    if not gui_app: return jsonify({"error": "No App"}), 500
    
    data = request.json
    ctype = data.get("type") # movie, show
    cid = data.get("id") # tt1234567
    season = data.get("season")
    episode = data.get("episode")
    
    if not cid: return jsonify({"error": "No ID"}), 400
    
    # Construct Deep Link
    url = ""
    if ctype == "movie":
        url = f"stremio://detail/movie/{cid}"
    elif ctype == "show" or ctype == "series":
        if season is not None and episode is not None:
            # Episode Format: series/ttID/ttID:S:E
            url = f"stremio://detail/series/{cid}/{cid}:{season}:{episode}"
        else:
            url = f"stremio://detail/series/{cid}"
            
    if url:
        success = gui_app.controller.launch_deep_link(url)
        return jsonify({"success": success})
        
    return jsonify({"error": "Invalid Content Type"}), 400

# --- Phase 3: Analytics API ---
@app.route("/api/analytics/stats")
def get_analytics_stats():
    if not gui_app: return jsonify({"error": "No App"}), 500
    return jsonify(gui_app.analytics.get_total_stats())

@app.route("/api/analytics/daily")
def get_analytics_daily():
    if not gui_app: return jsonify({"error": "No App"}), 500
    days = request.args.get("days", 7, type=int)
    return jsonify(gui_app.analytics.get_daily_stats(days))

@app.route("/api/analytics/sessions")
def get_analytics_sessions():
    if not gui_app: return jsonify({"error": "No App"}), 500
    limit = request.args.get("limit", 50, type=int)
    return jsonify(gui_app.analytics.get_recent_sessions(limit))

# --- Phase 4: Watch Party API ---
@app.route("/api/party/host", methods=["POST"])
def party_host():
    if not gui_app: return jsonify({"error": "No App"}), 500
    gui_app.config["watch_party_enabled"] = True
    gui_app.config["watch_party_mode"] = "host"
    gui_app.watch_party.enabled = True
    gui_app.watch_party.mode = "host"
    gui_app.watch_party.start()
    gui_app.save_settings()
    return jsonify({"status": "hosting", "port": gui_app.watch_party.port})

@app.route("/api/party/join", methods=["POST"])
def party_join():
    if not gui_app: return jsonify({"error": "No App"}), 500
    data = request.json
    host_ip = data.get("host_ip", "")
    if not host_ip: return jsonify({"error": "No host IP"}), 400
    
    gui_app.config["watch_party_enabled"] = True
    gui_app.config["watch_party_mode"] = "client"
    gui_app.config["watch_party_host_ip"] = host_ip
    gui_app.watch_party.enabled = True
    gui_app.watch_party.mode = "client"
    gui_app.watch_party.host_ip = host_ip
    gui_app.watch_party.start()
    gui_app.save_settings()
    return jsonify({"status": "joined", "host": host_ip})

@app.route("/api/party/leave", methods=["POST"])
def party_leave():
    if not gui_app: return jsonify({"error": "No App"}), 500
    gui_app.watch_party.stop()
    gui_app.config["watch_party_enabled"] = False
    gui_app.config["watch_party_mode"] = "off"
    gui_app.watch_party.enabled = False
    gui_app.watch_party.mode = "off"
    gui_app.save_settings()
    return jsonify({"status": "left"})

@app.route("/api/party/status")
def party_status():
    if not gui_app: return jsonify({"error": "No App"}), 500
    return jsonify({
        "enabled": gui_app.watch_party.enabled,
        "mode": gui_app.watch_party.mode,
        "peers": gui_app.watch_party.peer_count
    })

