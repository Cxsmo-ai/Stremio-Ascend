import os
import json
import time
from datetime import datetime, timedelta
from .logger import logger

class AnalyticsDB:
    """Manages session-based analytics for Stremio RPC activity tracking."""
    def __init__(self, db_path="data/analytics.json"):
        self.db_path = db_path
        self.sessions = []
        self.total_skips = 0
        self.total_saved_ms = 0
        self.load()

    def load(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", [])
                    self.total_skips = data.get("total_skips", 0)
                    self.total_saved_ms = data.get("total_saved_ms", 0)
            except Exception as e:
                logger.error(f"Failed to load analytics: {e}")

    def save(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "sessions": self.sessions[-500:], # Keep last 500 sessions
                    "total_skips": self.total_skips,
                    "total_saved_ms": self.total_saved_ms
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")

    def start_session(self, title, subtitle, imdb_id, media_type, image_url, device, total_duration_ms):
        session_id = len(self.sessions)
        session = {
            "id": session_id,
            "title": title,
            "subtitle": subtitle,
            "imdb_id": imdb_id,
            "type": media_type,
            "image_url": image_url,
            "device": device,
            "duration": total_duration_ms,
            "start_time": int(time.time()),
            "end_time": None,
            "watch_time": 0
        }
        self.sessions.append(session)
        self.save()
        return session_id

    def end_session(self, session_id, final_position_ms):
        if 0 <= session_id < len(self.sessions):
            session = self.sessions[session_id]
            session["end_time"] = int(time.time())
            session["watch_time"] = final_position_ms
            self.save()

    def add_skip(self, saved_ms):
        self.total_skips += 1
        self.total_saved_ms += saved_ms
        self.save()

    def get_total_stats(self):
        total_watch_ms = sum(s.get("watch_time", 0) for s in self.sessions)
        
        # Calculate Top Titles
        title_counts = {}
        for s in self.sessions:
            t = s.get("title")
            if t: title_counts[t] = title_counts.get(t, 0) + 1
        
        top_titles = sorted([{"title": k, "count": v} for k, v in title_counts.items()], key=lambda x: x["count"], reverse=True)

        return {
            "total_watch_time_min": int(total_watch_ms / 60000),
            "total_hours": round(total_watch_ms / 3600000, 1),
            "total_sessions": len(self.sessions),
            "total_skips": self.total_skips,
            "total_saved_hours": round(self.total_saved_ms / 3600000, 2),
            "completed_count": sum(1 for s in self.sessions if s.get("watch_time", 0) > s.get("duration", 0) * 0.9),
            "top_titles": top_titles[:5]
        }

    def get_daily_stats(self, days=7):
        # Placeholder for daily histograms
        return []

    def get_recent_sessions(self, limit=50):
        # Newest first
        return sorted(self.sessions, key=lambda x: x["start_time"], reverse=True)[:limit]
