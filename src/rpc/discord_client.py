import time
import logging
from pypresence import Presence
from pypresence.exceptions import DiscordNotFound, InvalidPipe
from pypresence.types import ActivityType
from typing import Optional

logger = logging.getLogger("stremio-rpc")

class DiscordRPC:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.rpc: Optional[Presence] = None
        self.connected = False
        self._last_reconnect_attempt = 0

    def connect(self):
        if not self.client_id: 
            logger.info("RPC: No Client ID provided.")
            return

        # Add a cooldown of 15 seconds between connection attempts to avoid spamming logs
        now = time.time()
        if now - self._last_reconnect_attempt < 15:
            return
        self._last_reconnect_attempt = now

        # Ensure we close any existing instance properly before creating a new one
        if self.rpc:
            try: self.rpc.close()
            except: pass
        
        logger.info(f"RPC: Attempting to connect with ID {self.client_id}...")
        try:
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception as e:
                logger.warning(f"RPC: Loop creation warning: {e}")

            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.connected = True
            logger.info(f"RPC: Successfully Connected with ID {self.client_id}!")
        except (DiscordNotFound, InvalidPipe, ConnectionRefusedError):
            logger.warning(f"RPC: Could not find Discord running. Waiting 15s for next retry...")
            self.connected = False
        except Exception as e:
            self.connected = False
            logger.error(f"RPC Connection Failed: {e}")

    def reconnect_with_id(self, new_client_id: str):
        """Switch to a different Discord Application ID (changes the 'Watching X' header)"""
        if new_client_id == self.client_id and self.connected:
            return  # Already connected with this ID
        
        logger.info(f"RPC: Switching to App ID {new_client_id}...")
        self.close()
        self.client_id = new_client_id
        self._last_reconnect_attempt = 0 # Force immediate reconnect
        self.connect()

    def update(self, details: str, state: str, 
               image_url: Optional[str] = None, 
               small_image: Optional[str] = None,
               small_text: Optional[str] = None,
               start_timestamp: Optional[int] = None,
               end_timestamp: Optional[int] = None,
               buttons: Optional[list] = None,
               activity_type: Optional[int] = None,
               party_id: Optional[str] = None,               join_secret: Optional[str] = None):
        
        if not self.connected or not self.rpc:
            return

        try:
            large_image = image_url if image_url else "stremio_logo"
            
            # Ensure proper field lengths
            details = str(details)[:128] if details else "Watching Content"
            state = str(state)[:128] if state else None
            
            # Prepare kwargs
            payload = {
                "details": details,
                "state": state,
                "large_image": large_image,
                "large_text": details,
                "small_image": small_image,
                "small_text": small_text or ("Playing" if small_image == "play" else "Paused"),
                "start": start_timestamp,
                "end": end_timestamp,
                "buttons": buttons,
                "party_id": party_id,
                "join": join_secret,
                "party_size": [1, 100] if party_id else None,
                "activity_type": activity_type
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            self.rpc.update(**payload)
        except (InvalidPipe, BrokenPipeError, AttributeError):
            logger.error("RPC Update Failed: Pipe closed or connection lost. Attempting to reconnect...")
            self.connected = False
            self.connect()
        except Exception as e:
            logger.error(f"RPC Update Failed: {e}")
            self.connected = False
            try: self.rpc.close() 
            except: pass
            
            # The monitor loop in app.py will trigger reconnect on next loop, 
            # but our connect() cooldown will keep it sane.
            time.sleep(2)

    def clear(self):
        if self.rpc and self.connected:
            try:
                self.rpc.clear()
            except: pass

    def close(self):
        """Fully close the connection"""
        if self.rpc:
            try: self.rpc.close()
            except: pass
        self.connected = False
        self.rpc = None
        logger.info("RPC: Closed connection.")
