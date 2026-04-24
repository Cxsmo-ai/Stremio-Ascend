import logging
import os
import re
import time
from typing import Optional, Dict
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

logger = logging.getLogger("ascend-rpc")

ADB_KEY_PATH = os.path.expanduser("~/.android/adbkey")

class AscendController:
    def __init__(self, host: str, port: int = 5555):
        self.host = host
        self.port = port
        self.device: Optional[AdbDeviceTcp] = None
        self.connected = False

    def connect(self) -> bool:
        """Synchronous connection to ADB"""
        if not self.host:
            return False
            
        try:
            signer = None
            if os.path.exists(ADB_KEY_PATH):
                try:
                    with open(ADB_KEY_PATH) as f:
                        priv_key = f.read()
                    with open(ADB_KEY_PATH + '.pub') as f:
                        pub_key = f.read()
                    signer = PythonRSASigner(pub_key, priv_key)
                except: pass

            self.device = AdbDeviceTcp(self.host, self.port, default_transport_timeout_s=9.0)
            
            # Connect synchronously
            self.device.connect(rsa_keys=[signer] if signer else [], auth_timeout_s=5)

            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            self.connected = False
            return False

    def get_device_name(self) -> str:
        """Fetch device model name meticulously"""
        if not self.device or not self.connected:
            return "Android TV"
        
        try:
            # 1. Try to get Manufacturer and Model
            manufacturer = self.device.shell("getprop ro.product.manufacturer").strip()
            model = self.device.shell("getprop ro.product.model").strip()
            
            # 2. Clean up
            if manufacturer and model:
                # If model starts with manufacturer (e.g. "NVIDIA SHIELD"), don't repeat it
                if model.lower().startswith(manufacturer.lower()):
                    return model
                return f"{manufacturer} {model}"
            
            if model:
                return model
                
            # 3. Fallback to hostname if model is missing
            hostname = self.device.shell("getprop net.hostname").strip()
            if hostname:
                return hostname
                
            return "Android TV"
        except Exception as e:
            logger.warning(f"Failed to get device name: {e}")
            return "Android TV"

    def get_playback_status(self, wako_mode: bool = False) -> Dict:
        """Synchronous status check with Clock Synchronization"""
        if not self.device or not self.connected:
            return {"playing": False, "state": "disconnected"}

        status = {
            "playing": False,
            "app": None,
            "title": None,
            "position": 0,
            "duration": 0,
            "state": "stopped",
            "timestamp": 0 
        }

        try:
            # OPTIMIZATION: Don't fetch uptime every look if we have a valid offset?
            # Actually, to detect PAUSE/PLAY, we still need 'dumpsys media_session'.
            # BUT we don't need 'cat /proc/uptime' constantly if we trust our local clock.
            # However, simpler approach first: Gather data, then smooth it.
            
            # Fetch Dumpsys ONLY (Fast)
            # We will fetch uptime only if we need to re-sync
            cmd = "dumpsys media_session"
            
            # If we don't have a clock offset, we MUST fetch uptime to establish it.
            # OR if we want to re-verify every X seconds.
            fetch_uptime = False
            # SYNC FIX: Sync more often (every 5s) to prevent drift and ensure seeking updates are caught accurately relative to device time.
            if not getattr(self, "clock_offset", None) or (time.time() - getattr(self, "last_clock_sync", 0) > 5):
                fetch_uptime = True
                cmd += " && echo '|UPTIME_DIV|' && cat /proc/uptime"
            
            try:
                raw_out = self.device.shell(cmd)
            except:
                return status
            
            uptime_str = None
            if "|UPTIME_DIV|" in raw_out:
                parts = raw_out.split("|UPTIME_DIV|")
                result = parts[0]
                uptime_str = parts[1].strip().split()[0] if len(parts) > 1 else "0"
            else:
                result = raw_out
            
            if not result:
                return {"playing": False, "state": "unknown"}
            
            # --- Parsing Logic (Find Target Block) ---
            current_app = None
            MEDIA_APPS = ["com.stremio.one", "com.brouken.player", "org.videolan.vlc", "com.google.android.youtube.tv"]
            blocks = result.split("Session ")
            target_block = None
            for block in blocks:
                if "package=" not in block: continue
                
                if not wako_mode:
                    for app in MEDIA_APPS:
                        if f"package={app}" in block:
                            current_app = app
                            break
                    if current_app: # Found known app
                         pass 
                    else:
                         import re
                         s_match = re.search(r'state=PlaybackState \{state=(\d+)', block)
                         if not s_match or int(s_match.group(1)) not in [2, 3, 4, 5, 6]:
                             continue
                else:
                    # Wako Mode: Accept ANY app with active playback
                    current_app = "Wako"

                import re
                s_match = re.search(r'state=PlaybackState \{state=(\d+)', block)
                if s_match:
                    raw_s = int(s_match.group(1))
                    if raw_s in [2, 3, 4, 5, 6]:
                        target_block = block
                        if raw_s == 3:
                            break 
            
            if not target_block:
                return status

            status["app"] = current_app or "External Player"

            # Parse State
            state_match = re.search(r'state=PlaybackState \{state=(\d+)', target_block)
            raw_state = int(state_match.group(1)) if state_match else 0
            if raw_state == 3: status["playing"] = True; status["state"] = "playing"
            elif raw_state in [2, 4, 5, 6]: status["state"] = "paused"
            else: status["state"] = "stopped"; return status

            # Parse Timestamps
            pos_match = re.search(r'position=(\d+)', target_block)
            updated_match = re.search(r'updated=(\d+)', target_block)
            speed_match = re.search(r'speed=([\d\.]+)', target_block)
            
            base_pos = int(pos_match.group(1)) if pos_match else 0
            updated_ts = int(updated_match.group(1)) if updated_match else 0
            speed = float(speed_match.group(1)) if speed_match else 1.0
            
            # FORCE PAUSE if speed is 0 (even if state=3)
            # This fixes timer counting up while paused (if device reports state=3 but speed=0)
            if speed <= 0.0 and status["playing"]:
                status["playing"] = False
                status["state"] = "paused"
            
            # --- Clock Synchronization Logic ---
            # device_uptime_ms is what we need.
            # Strategy:
            # 1. If we grabbed Uptime this loop, calculate Offset = (LocalNow - DeviceUptime)
            # 2. Use Offset to Estimate DeviceUptime = (LocalNow - Offset)
            
            local_now_ms = time.time() * 1000
            
            if fetch_uptime and uptime_str:
                try:
                    fetched_uptime_ms = float(uptime_str) * 1000
                    # Calculate Offset: How much LocalTime is ahead/behind DeviceTime
                    # Offset = Local - Device
                    # Device = Local - Offset
                    self.clock_offset = local_now_ms - fetched_uptime_ms
                    self.last_clock_sync = time.time()
                    # print(f"DEBUG: Clock Synced. Offset={self.clock_offset:.0f}ms")
                except:
                    pass
            
            # Use Estimated Uptime for smoothness
            if getattr(self, "clock_offset", None) is not None:
                device_uptime_ms = local_now_ms - self.clock_offset
            else:
                # Fallback if sync failed: 0 (will skip projection)
                device_uptime_ms = 0
            
            # Calculate Projected Position
            if status["state"] == "playing" and updated_ts > 0 and device_uptime_ms > updated_ts:
                delta = device_uptime_ms - updated_ts
                projected = int(base_pos + (delta * speed))
                
                # Retrieve Duration early for clamping
                # 1. Standard "duration=123"
                dur_match = re.search(r'duration=(\d+)', target_block)
                if dur_match: status["duration"] = int(dur_match.group(1))
                
                # 2. "contentDuration=123"
                if status["duration"] <= 0:
                     cd_match = re.search(r'contentDuration=(\d+)', target_block)
                     if cd_match: status["duration"] = int(cd_match.group(1))
                
                # 3. Metadata "DURATION=123" (Case insensitive, often found in metadata bundles)
                if status["duration"] <= 0:
                     meta_match = re.search(r'(?:android\.media\.metadata\.DURATION|DURATION)=([0-9]+)', target_block, re.IGNORECASE)
                     if meta_match: status["duration"] = int(meta_match.group(1))
                
                # CACHE DURATION: If we have a valid duration, save it. If we get 0, try to use cache.
                if status["duration"] > 0:
                    self.last_duration = status["duration"]
                elif getattr(self, "last_duration", 0) > 0 and status["title"] == getattr(self, "last_title_cache", None):
                    # Only use cached duration if title hasn't changed (approximate check)
                    status["duration"] = self.last_duration
                
                # Update title cache
                if status["title"]: self.last_title_cache = status["title"]

                # Sanity Clamp
                if status["duration"] > 0 and projected > status["duration"]:
                     projected = status["duration"]

                status["position"] = projected
            else:
                # PAUSED or STOPPED
                # If we parsed 0 but we were previously at X, and title is same, keep X.
                # Use base_pos parsed from block
                final_pos = base_pos
                
                if final_pos == 0 and status["state"] == "paused":
                     if getattr(self, "last_position_cache", 0) > 0 and status["title"] == getattr(self, "last_title_cache", None):
                         final_pos = self.last_position_cache
                
                status["position"] = final_pos

                status["position"] = final_pos

            # Anti-Reset Glitch (Universal)
            # If position looks like it reset to 0 (or near 0) but we were just deep in the video (>5s),
            # and the title hasn't changed, assume it's a glitch (e.g. transient buffering state).
            if status["position"] < 2000 and getattr(self, "last_position_cache", 0) > 5000:
                if status["title"] == getattr(self, "last_title_cache", None):
                    # Keep the old position to avoid "Restarting" UI 
                    status["position"] = self.last_position_cache

            # Save Position Cache
            if status["position"] > 0:
                self.last_position_cache = status["position"]
            
            # Save Title Cache
            if status["title"]: self.last_title_cache = status["title"]

            # Parse Description/Title
            desc_match = re.search(r'description=([^,]+)', target_block)
            if desc_match: 
                status["title"] = desc_match.group(1).strip()
                
                # Try to parse Season/Episode from title
                # Matches S01E01, S1E1, 1x01, etc.
                match = re.search(r'(?:S|Season\s*)(\d+)\s*(?:E|Episode\s*)(\d+)', status["title"], re.IGNORECASE)
                if match:
                    status["season"] = int(match.group(1))
                    status["episode"] = int(match.group(2))
                else:
                    # Try 1x01 format
                    match = re.search(r'(\d+)x(\d+)', status["title"])
                    if match:
                        status["season"] = int(match.group(1))
                        status["episode"] = int(match.group(2))
                    else:
                        status["season"] = None
                        status["episode"] = None

            return status

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            self.connected = False
            return {"playing": False, "state": "error"}

    def send_key(self, keycode: int):
        """Send a key event to the device"""
        if not self.device or not self.connected:
            return

        try:
            # We can run this synchronously in a thread or directly if the caller handles it
            # But the previous implementation used asyncio. 
            # This class uses synchronous adb-shell calls (AdbDeviceTcp).
            # So we should probably just use blocking calls here or run in executor if called from async context.
            # However, looking at the App class (Stremio_RPC_GUI/src/gui/app.py), it calls run_in_executor sometimes.
            # But the Controller methods here are defined synchronously (def connect, not async def).
            # So I will make these synchronous for simplicity and compatibility with this version of the class.
            self.device.shell(f"input keyevent {keycode}")
        except Exception as e:
            logger.error(f"Error sending key {keycode}: {e}")

    def play_pause(self):
        """Toggle play/pause (KEYCODE_MEDIA_PLAY_PAUSE = 85)"""
        # Run synchronously
        try:
            self.device.shell(f"input keyevent 85")
        except: pass

    def play(self):
        """Force play (KEYCODE_MEDIA_PLAY = 126)"""
        try:
            self.device.shell(f"input keyevent 126")
        except: pass

    def pause(self):
        """Force pause (KEYCODE_MEDIA_PAUSE = 127)"""
        try:
            self.device.shell(f"input keyevent 127")
        except: pass

    def stop(self):
        """Stop playback (KEYCODE_MEDIA_STOP = 86)"""
        try:
            self.device.shell(f"input keyevent 86")
        except: pass

    def next_track(self):
        """Next track (KEYCODE_MEDIA_NEXT = 87)"""
        try:
            self.device.shell(f"input keyevent 87")
        except: pass

    def prev_track(self):
        """Previous track (KEYCODE_MEDIA_PREVIOUS = 88)"""
        try:
            self.device.shell(f"input keyevent 88")
        except: pass

    def volume_up(self):
        """Volume Up (KEYCODE_VOLUME_UP = 24)"""
        try:
            self.device.shell(f"input keyevent 24")
        except: pass

    def volume_down(self):
        """Volume Down (KEYCODE_VOLUME_DOWN = 25)"""
        try:
            self.device.shell(f"input keyevent 25")
        except: pass

    def mute(self):
        """Toggle Mute (KEYCODE_MUTE = 164)"""
        try:
            self.device.shell(f"input keyevent 164")
        except: pass

    def next_episode_macro(self):
        """Netflix-style auto-play next: DPAD_RIGHT then ENTER"""
        try:
            self.device.shell("input keyevent 22")  # RIGHT
            time.sleep(0.3)
            self.device.shell("input keyevent 66")  # ENTER
        except: pass

    def seek_to(self, target_ms: int, current_ms: int = 0):
        """
        Seek using Key Events since 'media_session dispatch seek-to' is not supported.
        Assumes Stremio uses Right Arrow for skipping (approx 10-15s).
        """
        if not self.device or not self.connected:
            return
            
        try:
            # Fallback Logic: Calculate hops
            # Stremio default skip is often 15s or 30s. Let's assume 15s for safety, or check if we can configure it.
            # Using DPAD_RIGHT (22)
            
            if current_ms <= 0:
                # If we don't know where we are, we can't do relative seek easily.
                # Assuming this is called from AutoSkip, we usually know current_ms.
                return

            diff_ms = target_ms - current_ms
            
            if diff_ms > 0:
                # SKIP FORWARD
                # Assume 1 hop = 10 seconds (10000ms) - Trying to be conservative to not overshoot?
                # Stremio TV: Right Arrow is usually small skip, FF is fast forward.
                # Let's try sending DPAD_RIGHT events.
                
                HOP_SIZE_MS = 10000 
                hops = int(diff_ms / HOP_SIZE_MS)
                
                # Cap hops to avoid insanity (e.g. max 20 clicks)
                if hops > 30: hops = 30
                
                if hops > 0:
                    logger.info(f"Seeking: Sending {hops} Right Clicks (Target +{diff_ms}ms)")
                    # Send burst
                    # "input keyevent 22 22 22..." works in newer Android, but safer to loop or join
                    key_cmd = " ".join(["22"] * hops)
                    self.device.shell(f"input keyevent {key_cmd}")
            
            else:
                # SKIP BACKWARD? (Not implemented for auto-skip usually)
                pass

        except Exception as e:
            logger.error(f"Error seeking: {e}")

    def launch_deep_link(self, url: str):
        """
        Force stop Stremio and launch a deep link.
        URL formats:
        - stremio://detail/movie/tt1234567
        - stremio://detail/series/tt1234567/tt1234567:1:1
        """
        if not self.device or not self.connected:
            return False
            
        try:
            # 1. Force Stop
            self.device.shell("am force-stop com.stremio.one")
            
            # 2. Launch Intent
            # Use IMPLICIT Intent with CLEAR_TOP and NEW_TASK flags (-f 0x14000000)
            # This forces the app to handle the intent even if already running.
            cmd = f'am start -a android.intent.action.VIEW -f 0x14000000 -d "{url}"'
            logger.info(f"Running ADB Command: {cmd}")
            output = self.device.shell(cmd)
            logger.info(f"ADB Output: {output}")
            
            if "Error" in output or "does not exist" in output:
                 logger.error(f"Implicit launch failed: {output}")
                 return False
                
            return True
            
        except Exception as e:
            logger.error(f"Launch Deep Link Failed: {e}")
            return False
            
            logger.info(f"Launched Deep Link: {url}")
            return True
        except Exception as e:
            logger.error(f"Launch Deep Link Failed: {e}")
            return False

    def execute_wako_heist(self) -> Dict:
        """Wako Telemetry Heist: Ghost Keystroke -> UI Dump -> Data Extract -> Cleanup
        
        Executes the rapid-fire ADB sequence to extract title and episode
        from Wako's ExoPlayer overlay.
        """
        if not self.device or not self.connected:
            return {}
            
        # Try up to 2 attempts with increasing delays
        for attempt in range(2):
            try:
                delay = 1.5 if attempt == 0 else 3.0
                
                # Phase 2: Ghost Keystroke - Wake ExoPlayer overlay
                # DPAD_CENTER (23) simulates a tap which toggles the player overlay
                self.device.shell("input keyevent 23")
                
                # Render buffer - ExoPlayer needs time to draw text nodes
                logger.info(f"Wako Heist: Attempt {attempt+1}, waiting {delay}s for UI render...")
                time.sleep(delay)
                
                # Phase 3: Data Heist - Dump UI hierarchy then read the XML
                self.device.shell("uiautomator dump /sdcard/window_dump.xml")
                time.sleep(0.3)
                xml_data = self.device.shell("cat /sdcard/window_dump.xml")
                
                # Phase 4: Cleanup - Dismiss overlay WITHOUT exiting the player
                # Another DPAD_CENTER toggles it back off
                self.device.shell("input keyevent 23")
                
                if not xml_data:
                    logger.warning(f"Wako Heist: Attempt {attempt+1} - Empty UI dump")
                    continue
                
                # Debug: Log raw XML length
                logger.info(f"Wako Heist: Raw XML length={len(xml_data)}")
                
                # Phase 5: Parse - Extract ALL attribute values that could contain metadata
                # Check both text="" and content-desc="" attributes
                text_nodes = re.findall(r'text="([^"]+)"', xml_data)
                desc_nodes = re.findall(r'content-desc="([^"]+)"', xml_data)
                
                # Combine and deduplicate
                all_nodes = text_nodes + desc_nodes
                
                # Filter out empty, control chars, and system strings
                valid_texts = [t.strip() for t in all_nodes 
                              if t.strip() 
                              and not t.startswith('&#')
                              and len(t.strip()) > 0]
                
                # Debug: Log ALL non-empty attribute values found
                logger.info(f"Wako Heist: text nodes={len(text_nodes)}, desc nodes={len(desc_nodes)}, valid={len(valid_texts)}")
                logger.info(f"Wako Heist: ALL values: {valid_texts[:15]}")
                
                if not valid_texts:
                    logger.warning(f"Wako Heist: Attempt {attempt+1} - No text found, will retry")
                    continue
            
                # Strategy: Find SxxExx pattern, then grab the text node before it as Title
                for i, text in enumerate(valid_texts):
                    # Match isolated S03E14, S1E1, etc.
                    if re.match(r'^S\d+E\d+$', text, re.IGNORECASE):
                        episode_str = text
                        title = None
                        
                        # Walk backwards to find the title (first non-empty, non-timestamp text)
                        for j in range(i - 1, -1, -1):
                            candidate = valid_texts[j]
                            # Skip timestamps like "1:11 / 41:41"
                            if re.match(r'^\d+:\d+\s*/\s*\d+:\d+$', candidate):
                                continue
                            title = candidate
                            break
                        
                        if title:
                            ep_match = re.match(r'S(\d+)E(\d+)', episode_str, re.IGNORECASE)
                            if ep_match:
                                result = {
                                    "title": title,
                                    "season": int(ep_match.group(1)),
                                    "episode": int(ep_match.group(2))
                                }
                                logger.info(f"UI Heist SUCCESS (Isolated): {result}")
                                return result
                    
                    # Also try isolated 1x01 format
                    if re.match(r'^\d+x\d+$', text, re.IGNORECASE):
                        episode_str = text
                        title = None
                        for j in range(i - 1, -1, -1):
                            candidate = valid_texts[j]
                            if re.match(r'^\d+:\d+\s*/\s*\d+:\d+$', candidate):
                                continue
                            title = candidate
                            break
                        
                        if title:
                            ep_match = re.match(r'(\d+)x(\d+)', episode_str, re.IGNORECASE)
                            if ep_match:
                                result = {
                                    "title": title,
                                    "season": int(ep_match.group(1)),
                                    "episode": int(ep_match.group(2))
                                }
                                logger.info(f"UI Heist SUCCESS (Isolated): {result}")
                                return result
                    
                    # Try Combined Format (Stremio usually does "Title - S1 E1 - EpTitle")
                    combined_match = re.search(r'(.*?)\s*[-–]\s*(?:S|Season\s*)(\d+)\s*(?:E|Episode\s*)(\d+)', text, re.IGNORECASE)
                    if not combined_match:
                         # Try 1x01 format inline
                         combined_match = re.search(r'(.*?)\s*[-–]\s*(\d+)x(\d+)', text, re.IGNORECASE)
                         
                    if combined_match:
                         title = combined_match.group(1).strip()
                         # Clean up any leading artifact logic
                         title = re.sub(r'\[.*?\]', '', title).strip()
                         if title:
                             result = {
                                 "title": title,
                                 "season": int(combined_match.group(2)),
                                 "episode": int(combined_match.group(3))
                             }
                             logger.info(f"UI Heist SUCCESS (Combined): {result}")
                             return result
                
                # Fallback: If we found valid text but no episode pattern,
                # return first valid text as a movie title
                if valid_texts:
                    first = valid_texts[0]
                    if not re.match(r'^\d+:\d+', first):
                        logger.info(f"Wako Heist: No episode pattern, treating as movie: {first}")
                        return {"title": first, "season": None, "episode": None}
                
                logger.warning(f"Wako Heist: Attempt {attempt+1} - Could not extract metadata")
                    
            except Exception as e:
                logger.error(f"Wako Heist FAILED (attempt {attempt+1}): {e}")
        
        logger.warning("Wako Heist: All attempts exhausted")
        return {}
