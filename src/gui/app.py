import threading
import time
import sys
import os
import json
import logging
import re
import webbrowser

try:
    import webview
    HAS_WEBVIEW = True
except (ImportError, Exception) as e:
    HAS_WEBVIEW = False
    # If using standalone python, pywebview might be missing or fail due to missing WebView2 runtime
    print(f"WARNING: 'pywebview' could not initialize (Reason: {e})")
    print("FALLBACK: Opening dashboard in your default system browser instead.")

from src.core.config import load_config, save_config
from src.core.controller import AscendController
from src.core.tmdb import TMDBClient
from src.core.skip_manager import SkipManager
from src.core.aniskip import AniskipClient
from src.core.mal_mapper import MalMapper
from src.core.trakt import TraktClient
from src.rpc.discord_client import DiscordRPC
from pypresence.types import ActivityType
from src.core.history import SkipHistory
from src.core.stats import StatsManager
# from src.core.smart_home import SmartHomeController # Removed per user request
from src.core.watch_party import WatchPartyManager
from src.core.analytics import AnalyticsDB
from src.web.server import run_server

class MemoryLogHandler(logging.Handler):
    def __init__(self, capacity=50):
        super().__init__()
        self.capacity = capacity
        self.buffer = []
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
            if len(self.buffer) > self.capacity:
                self.buffer.pop(0)
        except Exception:
            self.handleError(record)


class App:
    def __init__(self):
        # --- CONFIG & STATE ---
        self.config = load_config()
        self.shared_state = {
            "connected": False,
            "device": "Disconnected",
            "title": "Ready to Play",
            "subtitle": "Waiting for device...",
            "progress": 0,
            "is_playing": False,
            "duration": 0,
            "position": 0,
            "meta_imdb": None,
            "meta_season": None,
            "meta_episode": None,
            "skip_status_msg": "System Ready",
            "skip_status_color": "gray",
            "auto_skip": False,
            "logs": [], # Live Log Buffer
            "history": [] 
        }
        
        
        # History & Stats
        self.history = SkipHistory()
        self.stats = StatsManager(self.config)
        
        # Setup Logging to Buffer
        
        # Setup Logging to Buffer
        self.log_handler = MemoryLogHandler()
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        self.log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_handler)
        self.shared_state["logs"] = self.log_handler.buffer
        
        # Initialize Backend Components
        self.controller = AscendController(self.config["adb_host"], self.config["adb_port"])
        self.tmdb_key = self.config["tmdb_api_key"]
        self.tmdb = TMDBClient(self.tmdb_key)
        self.rpc = DiscordRPC(self.config["discord_client_id"] or "1451010126495617106")
        
        self.mal_mapper = MalMapper(client_id=self.config.get("mal_client_id", ""))
        self.skip_manager = SkipManager(self.config)
        self.skip_manager.enabled = (self.config.get("skip_mode", "off") != "off")
        self.skip_manager.smart_mode = self.config.get("aniskip_smart", False) # Initialize Smart Mode
        self.aniskip = AniskipClient()
        self.trakt = TraktClient(
            client_id=self.config.get("trakt_client_id"),
            client_secret=self.config.get("trakt_client_secret"),
            access_token=self.config.get("trakt_access_token"),
            refresh_token=self.config.get("trakt_refresh_token")
        )
        
        # Phase 4: Watch Party
        self.watch_party = WatchPartyManager(self.config, controller_ref=self.controller)
        if self.config.get("watch_party_enabled"):
            self.watch_party.start()

        # Phase 3: Analytics Database
        self.analytics = AnalyticsDB()
        self._current_session_id = -1
        self._session_start_position = 0
        
        # self.smart_home = SmartHomeController(self.config) # Removed
        # self._last_smart_home_state = None
        self.last_full_details = None # Genre/Cast cache

        self.last_image_url = None
        
        # Caches
        self.cached_ep_details = None
        self.mal_id_cache = {}
        self.aniskip_cache = {}
        self.rpc_fail_count = 0
        self.last_rpc_payload = {}
        self.last_update_success_time = 0

        # State Variables
        self.running = True
        self.device_name = "Scanning..."
        
        # Wako Telemetry Cache
        self.wako_cached_title = None
        self.wako_cached_season = None
        self.wako_cached_episode = None
        
        # Helper Variables (Properties for compatibility with old logic if needed, but avoiding TK vars)
        self.var_show_device = type('obj', (object,), {'get': lambda: self.config.get("show_device_name", True), 'set': lambda x: self.update_config("show_device_name", x)})
        self.var_profanity = type('obj', (object,), {'get': lambda: self.config.get("profanity_filter", False), 'set': lambda x: self.update_config("profanity_filter", x)})
        self.device_var = type('obj', (object,), {'set': lambda x: self.update_config("adb_host", x)})

        # Start Backend Threads
        self.connect_adb()
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        threading.Thread(target=self._start_web_server, daemon=True).start()
        
        # Start WebView or Browser
        self.start_gui()

    def update_config(self, key, value):
        self.config[key] = value
        save_config(self.config)

    def start_gui(self):
        url = 'http://127.0.0.1:5466'
        if HAS_WEBVIEW:
            # Create a native window pointing to the local Flask server
            webview.create_window('Ascend Media RPC', url, width=1280, height=850, background_color='#000000')
            webview.start()
            self.running = False # App loop ends when webview closes
        else:
            # Fallback to system browser
            print(f"INFO: Opening Dashboard in system browser: {url}")
            time.sleep(1.0) # Wait for server to definitely start
            webbrowser.open(url)
            
            # Keep main thread alive since verify_loop handles daemons but we need a blocker or just join
            # For simplicity, we loop with sleep until keyboard interrupt
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.running = False

        # Clean up RPC on exit
        try: self.rpc.close()
        except: pass

    def _start_web_server(self):
        run_server(self)

    def connect_adb(self):
        def _connect():
            print("INFO: Connecting to ADB...")
            res = self.controller.connect()
            if res:
                self.device_name = self.config['adb_host']
                print(f"INFO: Connected to {self.device_name}")
                self.shared_state["device"] = self.device_name
                self.shared_state["connected"] = True
            else:
                self.shared_state["connected"] = False
        threading.Thread(target=_connect, daemon=True).start()

    # --- INPUT METHODS ---
    def play_pause(self): self.controller.send_key("KEYCODE_MEDIA_PLAY_PAUSE")
    def stop_playback(self): self.controller.send_key("KEYCODE_MEDIA_STOP")
    def next_track(self): self.controller.send_key("KEYCODE_MEDIA_NEXT")
    def prev_track(self): self.controller.send_key("KEYCODE_MEDIA_PREVIOUS")
    def seek_forward(self): self.controller.send_key("KEYCODE_MEDIA_FAST_FORWARD")
    def seek_backward(self): self.controller.send_key("KEYCODE_MEDIA_REWIND")
    
    def start_trakt_auth(self):
        """Initiates Trakt Device Flow"""
        if not self.trakt.client_id:
            return {"error": "Missing Client ID"}
            
        code_data = self.trakt.get_device_code()
        if not code_data:
            return {"error": "Failed to get device code"}
            
        # Start Polling Thread
        threading.Thread(target=self._poll_trakt, args=(code_data,), daemon=True).start()
        
        return {
            "user_code": code_data.get("user_code"),
            "verification_url": code_data.get("verification_url"),
            "expires_in": code_data.get("expires_in")
        }
        
    def _poll_trakt(self, code_data):
        device_code = code_data.get("device_code")
        interval = code_data.get("interval", 5)
        
        # Poll until expiration or success
        # Basic implementation: Loop for X attempts
        attempts = int(code_data.get("expires_in", 600) / interval)
        
        for _ in range(attempts):
            time.sleep(interval)
            res = self.trakt.poll_for_token(device_code)
            
            if isinstance(res, dict) and "access_token" in res:
                # Success!
                self.config["trakt_access_token"] = res["access_token"]
                self.config["trakt_refresh_token"] = res["refresh_token"]
                self.config["trakt_created_at"] = time.time()
                
                # Update Client
                self.trakt.set_auth(res["access_token"], res["refresh_token"])
                
                self.save_settings()
                print("INFO: Trakt Authenticated Successfully!")
                if "api_status" in self.shared_state:
                     self.shared_state["api_status"]["trakt"] = True
                return
            
            if res in ["expired", "denied", "invalid_code"]:
                print(f"INFO: Trakt Auth {res}")
                return
    
    def seek_to(self, ms):
        # Only supported if controller supports direct input or we implement it
        pass 

    def toggle_skip(self):
        self.skip_manager.enabled = not self.skip_manager.enabled
        self.config["skip_mode"] = "auto" if self.skip_manager.enabled else "off"
        save_config(self.config)

    def update_poster(self, img_bytes):
        # Since we are web-based, we don't display PIL bytes.
        # We just rely on the URL in shared_state["image_url"] which the frontend fetches directly or via proxy.
        pass

    def restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    def save_settings(self):
        save_config(self.config)

    def scan_for_api(self):
        from src.core.discovery import ADBDiscovery
        import asyncio
        
        print("INFO: Starting Network Scan...")
        self.shared_state["scan_results"] = [] # Clear previous
        
        async def run_scan():
            discovery = ADBDiscovery()
            results = await discovery.scan_network()
            return results

        try:
            # Create a new loop for this thread if needed, or use run
            devices = asyncio.run(run_scan())
            print(f"INFO: Scan Complete. Found: {devices}")
            self.shared_state["scan_results"] = devices
        except Exception as e:
            print(f"ERROR: Scan failed: {e}")
            self.shared_state["scan_results"] = []
            
        return self.shared_state["scan_results"]

    def scan_network(self):
        return self.scan_for_api()

    def apply_filter(self, text):
        if not text: return ""
        if self.config.get("profanity_filter"):
            # Basic filter list
            bad_words = ["shit", "fuck", "bitch", "cunt", "ass", "dick", "pussy"]
            pattern = re.compile(r'\b(' + '|'.join(bad_words) + r')\b', re.IGNORECASE)
            return pattern.sub(lambda m: '*' * len(m.group()), text)
        return text

    # --- MAIN LOOP ---
    def _monitor_loop(self):
        if self.config["discord_client_id"] and not self.rpc.connected:
            try: self.rpc.connect()
            except: pass 

        if self.tmdb_key != self.config["tmdb_api_key"]:
             self.tmdb_key = self.config["tmdb_api_key"]
             self.tmdb = TMDBClient(self.tmdb_key)
             
        self.mal_client_id = self.config.get("mal_client_id", "")
        self.mal_mapper.client_id = self.mal_client_id
             
        if self.config["discord_client_id"] != self.rpc.client_id:
            try: self.rpc.close()
            except: pass
            self.rpc = DiscordRPC(self.config["discord_client_id"])
            
        last_title = None

        # Trakt Scrobble State
        self.last_trakt_playing = False
        self.last_trakt_progress = 0
        self.trakt_scrobbled = False 
        
        while self.running:
            try:
                # 1. Ensure Discord RPC Connection
                if self.config["discord_client_id"] and not self.rpc.connected:
                    try: self.rpc.connect()
                    except: pass

                # 2. Ensure ADB Connection
                # 2. ADB Connection Check (Passive)
                # We used to auto-connect here, but user requested manual control.
                # Just update state based on current controller status.
                if self.controller.connected:
                    self.device_name = self.controller.get_device_name()
                    self.shared_state["connected"] = True
                else:
                    self.shared_state["connected"] = False
                
                if self.controller.connected:
                    is_wako = self.config.get("wako_mode", False)
                    status = self.controller.get_playback_status(wako_mode=is_wako)
                    
                    title = status.get("title")
                    state = status.get("state")
                    position = status.get("position", 0)
                    duration = status.get("duration", 0)
                    app_pkg = status.get("app")
                    
                    # Normalize 'null' title reported by some ExoPlayer media sessions
                    if title and title.lower() in ["null", "none"]:
                        title = ""
                        status["title"] = ""
                    
                    # === EXOPLAYER TELEMETRY HEIST ===
                    # Phase 1: Tripwire - If Wako mode is ON or Stremio gives no title, execute Ghost Keystroke sequence
                    is_missing_title = not title and getattr(self, "wako_cached_title", None) is None
                    if (is_wako or app_pkg == "com.stremio.one") and state == "playing" and is_missing_title:
                        print(f"INFO: Missing Title Tripwire TRIGGERED for {app_pkg} - Executing UI Heist...")
                        heist_data = self.controller.execute_wako_heist()
                        if heist_data and heist_data.get("title"):
                            self.wako_cached_title = heist_data["title"]
                            self.wako_cached_season = heist_data.get("season")
                            self.wako_cached_episode = heist_data.get("episode")
                            print(f"INFO: UI Heist LOCKED: {self.wako_cached_title} S{self.wako_cached_season}E{self.wako_cached_episode}")
                        else:
                            print("WARNING: UI Heist returned empty - will retry next cycle")
                    
                    # Phase 5: Inject cached Heist data into the status object
                    if getattr(self, "wako_cached_title", None):
                        title = self.wako_cached_title
                        status["title"] = title
                        if getattr(self, "wako_cached_season", None) is not None:
                            status["season"] = self.wako_cached_season
                        if getattr(self, "wako_cached_episode", None) is not None:
                            status["episode"] = self.wako_cached_episode
                    
                    # 0. Custom Title Overrides
                    if title == "MSNBC": title = "MS NOW"
                    
                    image_url = None
                    clean_title = title
                    episode_info = ""
                    season_num = status.get("season")
                    episode_num = status.get("episode")
                    imdb_id = None

                    if title and state in ["playing", "paused"]:
                        # 1. Parse Title
                        # Robust SxxExx Detection (Handles S7:E10, 1x01, Season 1 Episode 1, etc.)
                        match = re.search(r'(.*?)(?:[\s\._\-:]+|^)[sS](\d+)[\s\._\-:x]*[eE](\d+)', title)
                        if not match: match = re.search(r'(.*?)(?:[\s\._\-:]+|^)(?:[sS]eason[\s_]*(\d+))[\s\._\-:]*(?:[eE]pisode[\s_]*(\d+))', title, re.I)
                        if not match: match = re.search(r'(.*?)(?:[\s\._\-:]+|^)(\d+)[xX](\d+)', title)
                        # Anime style: "Chainsaw Man S1 - 01"
                        if not match: match = re.search(r'(.*?)[\s_]*[sS](\d+)[\s_]*[-–:_]*[\s_]*(\d+)', title)
                        # Anime absolute: "Chainsaw Man - 01" -> (Chainsaw Man, 01) -> Season 1 assumed
                        if not match: match = re.search(r'(?:\[.*?\]\s*)?(.*?)(?:[\s_]+[-–][\s_]+)(\d+)(?:[vV]\d+)?(?:[\.\s\[\(_]|$)', title)
                        
                        if match:
                            raw_name = match.group(1).replace(".", " ").replace("_", " ").strip()
                            raw_name = re.sub(r'\[.*?\]', '', raw_name)
                            raw_name = re.sub(r'\(.*?\)', '', raw_name)
                            clean_title = raw_name.strip()
                            
                            # Clean up trailing separators
                            clean_title = re.sub(r'[:\-– ]+$', '', clean_title).strip()
                            
                            # Handle different group counts
                            if not season_num: season_num = int(match.group(2)) if len(match.groups()) > 2 else 1
                            if not episode_num: episode_num = int(match.group(3)) if len(match.groups()) > 2 else int(match.group(2))
                            
                            episode_info = f"S{season_num}:E{episode_num}"
                        else:
                            clean_title = re.sub(r'\[.*?\]', '', title)
                            clean_title = re.sub(r'\(.*?\)', '', clean_title)
                            clean_title = re.sub(r'\.(mkv|mp4|avi)$', '', clean_title, flags=re.IGNORECASE)
                            clean_title = clean_title.replace(".", " ").replace("_", " ").strip()

                        # Wako Mode: If season/episode came from the heist but regex didn't match,
                        # still format the episode_info string
                        if not match and season_num and episode_num:
                            episode_info = f"S{season_num}:E{episode_num}"

                        # Timestamps - use TMDB runtime as fallback for progress bar
                        start_ts = None
                        end_ts = None
                        # Prefer ADB duration, fallback to cached TMDB runtime
                        effective_duration = duration if duration > 0 else getattr(self, "last_runtime_ms", 0)
                        
                        if state == "playing" and position > 0:
                            start_ts = int(time.time() - (position / 1000))
                            if effective_duration > 0: 
                                end_ts = int(start_ts + (effective_duration / 1000))

                        # Reset Trakt state if new item
                        if clean_title != getattr(self, "last_clean_title", None):
                             self.last_trakt_playing = False
                             self.last_trakt_progress = 0
                             self.trakt_scrobbled = False

                        # 2. Metadata Search
                        has_movie_pattern = re.search(r'\(\d{4}\)', clean_title) # e.g. "Avatar (2009)"
                        has_wako_data = (is_wako and season_num and episode_num)  # Wako provided structured data
                        should_search = (match is not None) or (has_movie_pattern is not None) or has_wako_data

                        is_new_media = False
                        if title != getattr(self, "last_raw_user_title", None):
                            is_new_media = True
                            print(f"INFO: New Media Detected: '{clean_title}'. Pausing player while fetching metadata & skip times...")
                            self.controller.pause()
                            
                            self.last_episode_name = None # Clear old cache
                            
                            if should_search:
                                q_stripped = re.sub(r'\s*\(?\d{4}\)?.*$', '', clean_title).strip()
                                # Enhance: Force TV search if season/episode detected to ensure season art works
                                m_type_hint = "tv" if (season_num and episode_num) else None
                                meta = self.tmdb.search_content(q_stripped, media_type_hint=m_type_hint)
                                if meta:
                                    if meta.get("title"): clean_title = meta.get("title")
                                    show_image = meta.get("image_url")
                                    season_image = None
                                    episode_image = None
                                    imdb_id = meta.get("imdb_id")
                                    
                                    if season_num and episode_num:
                                        # 1. Season Art (if enabled)
                                        season_data = self.tmdb.get_season_details(meta['id'], season_num)
                                        if season_data: season_image = season_data.get("image_url")
                                        
                                        # 2. Episode Still
                                        ep_data = self.tmdb.get_episode_details(meta['id'], season_num, episode_num)
                                        if ep_data:
                                            episode_image = ep_data.get("image_url")
                                            if ep_data.get("name"): self.last_episode_name = ep_data.get("name")
                                            if ep_data.get("runtime_ms"): self.last_runtime_ms = ep_data.get("runtime_ms")
                                                 
                                    # Select Large Image based on Mode
                                    mode = self.config.get("rpc_large_image_mode", "season")
                                    if mode == "episode" and episode_image:
                                        self.last_image_url = episode_image
                                    elif mode == "season" and season_image:
                                        self.last_image_url = season_image
                                    else:
                                        self.last_image_url = show_image or "stremio_logo"
                                                
                                    # Fetch Trailer URL for RPC buttons
                                    if self.config.get("rpc_buttons_enabled"):
                                        m_type = "tv" if (season_num and episode_num) else "movie"
                                        self.last_trailer_url = self.tmdb.get_content_trailer(meta['id'], m_type)
                                        self.last_tmdb_id = meta['id']
                                        self.last_media_type = m_type
                                else:
                                    # MAL Fallback
                                    if self.config.get("aniskip_enabled") and self.mal_client_id:
                                        try:
                                            mal_id = self.mal_id_cache.get(clean_title)
                                            if not mal_id:
                                                 mal_id = self.mal_mapper.search_anime(clean_title)
                                                 if mal_id: self.mal_id_cache[clean_title] = mal_id
                                            
                                            if mal_id:
                                                mal_details = self.mal_mapper.get_anime_details(mal_id)
                                                if mal_details:
                                                     clean_title = mal_details.get("title")
                                                     self.last_image_url = mal_details.get("image_url")
                                                     imdb_id = f"mal_{mal_id}"
                                        except: pass
                            else:
                                print(f"INFO: Skipping Metadata Search for ambiguous title: '{clean_title}'")
                                # Fallback: Treat as generic file (imdb_id remains None)

                            self.last_clean_title = clean_title
                            self.last_raw_user_title = title
                            self.last_imdb_id = imdb_id  # Cache IMDB ID for skip logic
                            
                            # Analytics: End previous session, start new one
                            if self._current_session_id >= 0:
                                self.analytics.end_session(self._current_session_id, position)
                            media_type = "episode" if (season_num and episode_num) else "movie"
                            self._current_session_id = self.analytics.start_session(
                                title=clean_title,
                                subtitle=episode_info or "Movie",
                                imdb_id=imdb_id or "",
                                media_type=media_type,
                                image_url=self.last_image_url or "",
                                device=self.device_name,
                                total_duration_ms=effective_duration
                            )
                            self._session_start_position = position
                            # Insane RPC: Fetch genres, cast, and ratings
                            self.last_full_details = self.tmdb.get_full_details(self.last_tmdb_id, self.last_media_type) if getattr(self, "last_tmdb_id", None) else None
                        else:
                            clean_title = self.last_clean_title
                            image_url = self.last_image_url
                            imdb_id = getattr(self, 'last_imdb_id', None)  # Restore cached IMDB ID
                            
                        # Rebuild formatted episode name string for the RPC
                        if season_num and episode_num:
                            episode_info = f"S{season_num}:E{episode_num}"
                            if getattr(self, "last_episode_name", None):
                                episode_info += f" ({self.last_episode_name})"

                        # Watch Party: Broadcast state changes
                        if self.watch_party.enabled:
                            self.watch_party.broadcast(state, position)

                        # 3. Auto Skip
                        now = time.time()
                        skip_status_msg = ""
                        skip_status_color = "gray"
                        
                        if imdb_id and season_num and episode_num:
                             # Logic: Get Skip Times -> Check Position -> Seek if needed
                             skip_times = self.skip_manager.get_skip_times(imdb_id, season_num, episode_num, tmdb_id=self.last_tmdb_id)
                             
                             if is_new_media:
                                 print("INFO: Fetched skips. Resuming playback.")
                                 self.controller.play()

                             if skip_times:
                                 skip_status_msg = "Skip Interval Found"
                                 skip_status_color = "#2CC985"
                                 
                                 # Debug: Check if skip manager is enabled
                                 print(f"DEBUG SKIP: enabled={self.skip_manager.enabled}, skip_mode={self.config.get('skip_mode')}, position={position}ms ({position/1000:.1f}s)")
                                 
                                 if now - getattr(self, "last_skip_time", 0) > 5:
                                     skip_res = self.skip_manager.should_skip(position, skip_times)
                                     print(f"DEBUG SKIP: should_skip result = {skip_res}")
                                     if skip_res:
                                         target_ms, skip_type = skip_res
                                         skip_mode = self.config.get("skip_mode", "auto")
                                         if skip_mode == "auto":
                                              print(f"DEBUG SKIP: AUTO MODE - Seeking to {target_ms}ms from {position}ms")
                                              
                                              if skip_type in ["outro", "ed"] and self.config.get("autoplay_next_enabled", True):
                                                  print(f"INFO: AUTOPLAY NEXT - Firing setup!")
                                                  self.controller.send_key(22)
                                                  time.sleep(0.3)
                                                  self.controller.send_key(66)
                                              
                                              self.controller.seek_to(target_ms, current_ms=position)
                                              self.last_skip_time = now
                                              
                                              # Increment Stat
                                              self.stats.increment("skips")
                                              saved_sec = (target_ms - position) / 1000
                                              saved_min = saved_sec / 60
                                              current_saved = self.stats.get("saved", 0)
                                              self.stats.set("saved", current_saved + saved_min)

                                              self.shared_state["skip_button"] = {"visible": False}
                                              
                                              # Record History
                                              self.history.add_entry({
                                                  "timestamp": int(time.time()),
                                                  "title": clean_title,
                                                  "subtitle": episode_info or "Movie",
                                                  "image_url": self.last_image_url or "",
                                                  "type": skip_type,
                                                  "saved_str": f"{int(saved_sec)}s",
                                                  "device": self.device_name
                                              })
                                              
                                         elif skip_mode == "button":
                                              # Manual Mode: Show Button in UI
                                              self.shared_state["skip_button"] = {
                                                  "visible": True,
                                                  "target": target_ms,
                                                  "label": f"SKIP {skip_type.upper()}"
                                              }
                                     else:
                                         self.shared_state["skip_button"] = {"visible": False}
                                 else:
                                     self.shared_state["skip_button"] = {"visible": False}

                        # 4. RPC Update
                        package_map = {
                            "com.stremio.one": "Stremio",
                            "com.brouken.player": "Just Player",
                            "org.videolan.vlc": "VLC",
                            "com.google.android.youtube.tv": "YouTube",
                            "com.netflix.ninja": "Netflix",
                            "com.amazon.amazonvideo.livingroom": "Prime Video",
                            "com.disney.disneyplus": "Disney+",
                            "com.plexapp.android": "Plex",
                            "Wako": "Wako"
                        }
                        
                        clean_app_name = package_map.get(app_pkg, "Android TV")
                        
                        # Streaming Mode Logic
                        display_title = self.apply_filter(clean_title)
                        if self.config.get("rpc_streaming_mode"):
                            display_title = f"{display_title} (on {clean_app_name})"
                                                  # Custom Status Prep
                        display_subtitle = self.apply_filter(episode_info) if episode_info else (state.title() if state else "Idle")
                        custom_status = self.config.get("rpc_custom_status", "").strip()
                        if custom_status:
                            display_subtitle = f"{display_subtitle} | {custom_status}" if display_subtitle else custom_status
                        
                        # Insane RPC: Status Cycling (Cast, Rating, Progress)
                        if self.config.get("rpc_status_effects_enabled") and self.config.get("rpc_status_cycling_enabled"):
                            cycle_idx = int(time.time() / 15) % 3
                            if cycle_idx == 1 and self.last_full_details:
                                rating = self.last_full_details.get("vote_average")
                                count = self.last_full_details.get("vote_count")
                                if rating: display_subtitle = f"Rating: {rating:.1f}/10 ({count} votes)"
                            elif cycle_idx == 2 and self.last_full_details:
                                cast = self.last_full_details.get("cast")
                                if cast: display_subtitle = f"Cast: {', '.join(cast)}"

                        try:
                            # Contextual Discord App Switching (Wako vs Stremio)
                            target_client_id = self.config.get("discord_client_id")
                            if is_wako and self.config.get("discord_wako_client_id"):
                                target_client_id = self.config.get("discord_wako_client_id")
                                
                            if target_client_id and self.rpc.client_id != target_client_id:
                                self.rpc.reconnect_with_id(target_client_id)
                                
                            # Show RPC when playing OR paused
                            if state in ["playing", "paused"]:
                                # Use cached metadata art (Season Art if found)
                                rpc_image = self.last_image_url or "stremio_logo"
                                
                                # Spotify Mode: Use LISTENING activity type for Music
                                rpc_activity_type = ActivityType.WATCHING
                                if self.config.get("rpc_status_effects_enabled") and self.last_full_details:
                                    if "Music" in self.last_full_details.get("genres", []):
                                        rpc_activity_type = ActivityType.LISTENING
                                
                                # Letterbox HTTP images (TMDB/MAL) into a 1:1 square so Discord doesn't cut them off
                                if rpc_image.startswith("http"):
                                    stripped = rpc_image.replace("https://", "").replace("http://", "")
                                    # Output as transparent PNG padded square
                                    rpc_image = f"https://wsrv.nl/?url={stripped}&w=512&h=512&fit=contain&output=png"
                                
                                # Construct Buttons
                                rpc_buttons = None
                                if self.config.get("rpc_buttons_enabled"):
                                    rpc_buttons = []
                                    # Button 1: TMDB
                                    if getattr(self, "last_tmdb_id", None):
                                        m_type = getattr(self, "last_media_type", "movie")
                                        tmdb_url = f"https://www.themoviedb.org/{m_type}/{self.last_tmdb_id}"
                                        rpc_buttons.append({"label": "View on TMDB", "url": tmdb_url})
                                    
                                    # Button 2: Trailer
                                    if getattr(self, "last_trailer_url", None):
                                        rpc_buttons.append({"label": "Watch Trailer", "url": self.last_trailer_url})

                                if state == "playing":
                                    rpc_small_text = f"Watching on {self.device_name}" if self.var_show_device.get() else "Playing"
                                    s_ts = start_ts
                                    
                                    # Dynamic Time Display
                                    if self.config.get("rpc_time_display") == "elapsed":
                                        e_ts = None
                                    else:
                                        e_ts = end_ts
                                else:
                                    rpc_small_text = f"Paused on {self.device_name}" if self.var_show_device.get() else "Paused"
                                    # Hide timer when paused
                                    s_ts = None
                                    e_ts = None

                                # Dynamic Small Image Selection (Insane RPC)
                                # Dynamic Small Image Selection (Insane RPC)
                                rpc_small_mode = self.config.get("rpc_small_icon_mode", "play_status")
                                small_img = "play" if state == "playing" else "pause" # Default

                                if rpc_small_mode == "stremio":
                                    small_img = "stremio_logo"
                                elif rpc_small_mode == "wako":
                                    small_img = "wako"
                                elif rpc_small_mode == "device":
                                    small_img = "device"
                                elif rpc_small_mode in ["streaming_service", "content_network", "content_network_full"]:
                                    import urllib.parse
                                    inner_url = None
                                    
                                    if rpc_small_mode in ["content_network", "content_network_full"]:
                                        inner_url = self.last_full_details.get("network_logo") if self.last_full_details else None
                                    
                                    if not inner_url:
                                        domain_map = {
                                            "com.stremio.one": "stremio.com", "app.wako": "wako.tv",
                                            "org.videolan.vlc": "videolan.org", "com.netflix.ninja": "netflix.com"
                                        }
                                        domain = domain_map.get(app_pkg, f"{app_pkg}.com")
                                        inner_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                                    
                                    # Encode correctly for the Discord proxy
                                    encoded_inner = urllib.parse.quote(inner_url)
                                    small_img = f"https://wsrv.nl/?url={encoded_inner}&w=128&h=128&fit=contain&mask=circle&output=png"
                                    
                                # Dynamic Small Text (Badge Tooltip)
                                # Override rpc_small_text only if content_network_full or explicitly desired
                                if rpc_small_mode == "content_network_full":
                                    net_name = self.last_full_details.get("network_name") if self.last_full_details else None
                                    if net_name:
                                        rpc_small_text = f"Service: {net_name}"
                                
                                if rpc_small_mode == "play_status":
                                    small_img = "play" if state == "playing" else "pause"

                                # Activity Update
                                self.rpc.update(
                                    details=display_title,
                                    state=display_subtitle,
                                    image_url=rpc_image,
                                    small_image=small_img,
                                    small_text=rpc_small_text,
                                    start_timestamp=s_ts,
                                    end_timestamp=e_ts,
                                    buttons=rpc_buttons if rpc_buttons else None,
                                    activity_type=rpc_activity_type
                                )
                            else:
                                # Clear RPC when stopped
                                self.rpc.clear()
                        except: pass

                        # 5. Update Web Shared State
                        # Use effective_duration (ADB or TMDB fallback) for UI
                        self.shared_state.update({
                            "title": display_title,
                            "subtitle": display_subtitle,
                            "progress": position / effective_duration if effective_duration > 0 else 0,
                            "position": position,  # Current position in ms
                            "duration": effective_duration,  # Total duration in ms (ADB or TMDB fallback)
                            "image_url": image_url,
                            "connected": True,
                            "device": self.device_name,
                            "is_playing": state == "playing",
                            "auto_skip": self.skip_manager.enabled,
                            "skip_status_msg": skip_status_msg,
                            "skip_status_color": skip_status_color
                        })
                        
                        # 6. Trakt Live Scrobbling (State Machine)
                        # Requirements: Start (0%), Pause, Stop (Finished or Quit)
                        
                        if self.trakt.access_token:
                            # Determine Current Identity
                            current_trakt_id = None
                            media_data = {}
                            
                            # Construct Identity & Payload
                            if imdb_id:
                                current_trakt_id = imdb_id # Use IMDB as unique key
                                # Use effective_duration (ADB or TMDB fallback) for progress calculation
                                progress_pct = (position / effective_duration * 100) if effective_duration > 0 else 0
                                
                                if season_num and episode_num:
                                    # Episode Payload
                                    # Trakt best practice: Send Show Identity + Episode Number
                                    # Or Episode Identity if known. We have Show IMDB.
                                    current_trakt_id = f"{imdb_id}_S{season_num}_E{episode_num}"
                                    media_data = {
                                        "show": {"ids": {"imdb": imdb_id}},
                                        "episode": {"season": season_num, "number": episode_num}
                                    }
                                else:
                                    # Movie Payload
                                    media_data = {
                                        "movie": {"ids": {"imdb": imdb_id, "slug": clean_title}}
                                    }
                                    # If not an IMDB ID (e.g. mal_123), we might need different handling
                                    if str(imdb_id).startswith("mal_"):
                                         # Trakt doesn't support MAL ID in 'ids' directly usually, but we can try slug or title
                                         media_data["movie"]["title"] = clean_title
                                         del media_data["movie"]["ids"]["imdb"]

                            # State Determination
                            current_state_action = None # start, pause, stop
                            
                            # Detect Identity Change (New Content)
                            if current_trakt_id != getattr(self, "last_trakt_id", None):
                                # If we were playing something else, STOP it
                                if getattr(self, "last_trakt_id", None):
                                    self.trakt.scrobble("stop", getattr(self, "last_media_data", {}), getattr(self, "last_progress", 0))
                                
                                # New Content Started
                                if state == "playing" and current_trakt_id:
                                    current_state_action = "start"

                            # Detect State Change (Same Content)
                            elif state != getattr(self, "last_trakt_state", "stopped"):
                                if state == "playing": current_state_action = "start" # Acts as Resume
                                elif state == "paused": current_state_action = "pause"
                                elif state == "stopped": current_state_action = "stop"

                            # Execute Action
                            if current_state_action and current_trakt_id:
                                self.trakt.scrobble(current_state_action, media_data, progress_pct)
                                # Increment Stat
                                self.stats.increment("trakt")
                            
                            # Update State Tracking
                            self.last_trakt_id = current_trakt_id
                            self.last_trakt_state = state
                            self.last_media_data = media_data
                            self.last_progress = progress_pct if effective_duration > 0 else 0
                        
                    elif state == "stopped":
                        # Phase 6: Wako Session Termination - Flush cache
                        if self.config.get("wako_mode", False):
                            if self.wako_cached_title:
                                print(f"INFO: Wako Session ENDED - Flushing cache for '{self.wako_cached_title}'")
                            self.wako_cached_title = None
                            self.wako_cached_season = None
                            self.wako_cached_episode = None
                        
                        self.rpc.clear()
                        self.shared_state["is_playing"] = False
                        self.shared_state["title"] = "Ready to Play"
                        self.shared_state["subtitle"] = "Waiting for media..."
                        self.shared_state["connected"] = True # Fix: Mark connected even if stopped
                        self.shared_state["device"] = self.device_name
                        
                        # Trakt Stop Logic
                        if getattr(self, "last_trakt_id", None):
                             self.trakt.scrobble("stop", getattr(self, "last_media_data", {}), getattr(self, "last_progress", 0))
                             self.last_trakt_id = None
                             self.last_trakt_state = "stopped"
                        
                        # Analytics: End session on stop
                        if self._current_session_id >= 0:
                            self.analytics.end_session(self._current_session_id, 0)
                            self._current_session_id = -1
                        
            except Exception as e:
                print(f"Monitor Loop Error: {e}")
            
            # 7. Global API Status Update (Always run)
            # Helps user debug why RPC might be missing (Disconnected vs Hidden due to no metadata)
            self.shared_state["api_status"] = {
                "discord": self.rpc.connected,
                "trakt": bool(self.trakt.access_token),
                "adb": self.controller.connected,
                "metadata": bool(self.tmdb_key or self.mal_client_id) 
            }
            
            time.sleep(1)

if __name__ == "__main__":
    app = App()
