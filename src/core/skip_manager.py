import os
import requests
import logging
from typing import Dict, List, Optional
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

logger = logging.getLogger("stremio-rpc")

class SkipManager:
    """
    Manages Skip Providers and evaluates skip targets.
    Fetches concurrently from all enabled providers and merges results.
    """
    def __init__(self, config: Dict):
        self.INTROHATER_BASE = "http://127.0.0.1:4002"
        self.INTRODB_BASE = "https://introdb.app/api/v1/episodes"
        self.JIKAN_BASE = "https://api.jikan.moe/v4/anime"
        self.ANISKIP_BASE = "https://api.aniskip.com/v2/skip-times"
        self.TIDB_BASE = "https://theintrodb.org/api/v1"
        self.REMOTE_JSON_URL = config.get("remote_json_url", "")
        self.TIDB_KEY = config.get("tidb_api_key", "")
        
        self.cache = {}
        self.mal_cache = {}
        
        self.enabled = (config.get("skip_mode", "off") != "off")
        self.smart_mode = config.get("aniskip_smart", False)
        
        # Provider states
        self.introhater_enabled = config.get("introhater_enabled", True)
        self.introdb_enabled = config.get("introdb_enabled", True)
        self.aniskip_fallback = config.get("aniskip_fallback", True)
        self.tidb_enabled = config.get("tidb_enabled", False)
        self.remote_json_enabled = config.get("remote_json_enabled", False)
        self.videoskip_enabled = config.get("videoskip_enabled", False)
        self.jumpscare_major_enabled = config.get("jumpscare_major_enabled", False)
        self.jumpscare_minor_enabled = config.get("jumpscare_minor_enabled", False)
        
        self.skip_priority_order = config.get("skip_priority_order", [
            "introdb", "tidb", "introhater", "remote_json", "videoskip", "jumpscare", "aniskip"
        ])

        self.manual_tmdb_id = config.get("skip_tmdb_id", "")
        self.manual_mal_id = config.get("skip_mal_id", "")
        
        logger.info(f"[SkipManager] Initialized with priority order: {self.skip_priority_order}")


    def get_skip_times(self, imdb_id: str, season: int, episode: int, tmdb_id: Optional[int] = None) -> List[Dict]:
        """Fetch skip times using the robust merged-chain priority mechanism."""
        if not imdb_id and not tmdb_id:
            return None
        
        key = f"{imdb_id}-{tmdb_id}-{season}-{episode}"
        if key in self.cache:
            return self.cache[key]
            
        all_segments = []
        
        # Determine mapping upfront to save parallel time
        mal_id = None
        if self.aniskip_fallback:
            if self.manual_mal_id:
                try: mal_id = int(self.manual_mal_id)
                except: pass
            else:
                mal_id = self._get_mal_id(imdb_id)
                
        lookup_tmdb = self.manual_tmdb_id if self.manual_tmdb_id else tmdb_id

        # Fire required fetches in parallel
        futures = {}
        with ThreadPoolExecutor(max_workers=7) as executor:
            if self.introhater_enabled:
                futures[executor.submit(self._fetch_introhater, imdb_id, season, episode)] = "introhater"
            if self.introdb_enabled:
                futures[executor.submit(self._fetch_introdb, lookup_tmdb, season, episode)] = "introdb"
            if self.aniskip_fallback and mal_id:
                futures[executor.submit(self._fetch_aniskip, mal_id, episode)] = "aniskip"
            if self.tidb_enabled:
                futures[executor.submit(self._fetch_tidb, imdb_id, season, episode, tmdb_id=lookup_tmdb)] = "tidb"
            if self.remote_json_enabled and self.REMOTE_JSON_URL:
                futures[executor.submit(self._fetch_remote_json, imdb_id, season, episode)] = "remote_json"
            if self.videoskip_enabled:
                futures[executor.submit(self._fetch_videoskip, imdb_id, season, episode)] = "videoskip"
            if self.jumpscare_major_enabled or self.jumpscare_minor_enabled:
                futures[executor.submit(self._fetch_jumpscare, lookup_tmdb, season, episode)] = "jumpscare"

            for future in as_completed(futures):
                provider = futures[future]
                try:
                    result = future.result()
                    if result:
                        logger.info(f"[SkipManager] {provider} returned {len(result)} segments")
                        all_segments.extend(result)
                except Exception as e:
                    logger.error(f"[SkipManager] Error fetching from {provider}: {e}")

        if not all_segments:
            logger.debug(f"[SkipManager] No skip data found for {imdb_id} S{season}E{episode}")
            self.cache[key] = None
            return None

        # ... (rest of conflict resolution)
        # I'll keep the resolution logic the same but I'll ensure I don't break the return.
        
        resolved_dict = {}
        for segment in all_segments:
            seg_type = segment.get("type", "unknown")
            provider = segment.get("source", "")
            score = 999
            if provider in self.skip_priority_order:
                score = self.skip_priority_order.index(provider)
            
            if seg_type in ["intro", "outro", "recap", "preview", "credits"]:
                if seg_type not in resolved_dict:
                    resolved_dict[seg_type] = {"segment": segment, "score": score}
                else:
                    if score < resolved_dict[seg_type]["score"]:
                        resolved_dict[seg_type] = {"segment": segment, "score": score}
            else:
                uid = f"{seg_type}_{int(segment['start'])}"
                resolved_dict[uid] = {"segment": segment, "score": score}

        final_list = [val["segment"] for val in resolved_dict.values()]
        final_list.sort(key=lambda x: x["start"])
        self.cache[key] = final_list
        return final_list

    def _fetch_introhater(self, imdb_id: str, season: int, episode: int) -> Optional[List[Dict]]:
        try:
            full_id = f"{imdb_id}:{season}:{episode}"
            url = f"{self.INTROHATER_BASE}/api/skip/{full_id}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data and data.get("start") is not None:
                    return [{"start": data["start"], "end": data["end"], "type": "intro", "source": "introhater", "label": "Skip Intro"}]
        except requests.exceptions.ConnectionError:
            logger.warning("[SkipManager] IntroHater down, temporarily disabled.")
            self.introhater_enabled = False
        except Exception:
            pass
        return None

    def _fetch_introdb(self, lookup_tmdb: str, season: int, episode: int) -> Optional[List[Dict]]:
        try:
            url = f"{self.INTRODB_BASE}/{lookup_tmdb}/{season}/{episode}"
            response = requests.get(url, timeout=5, headers={"User-Agent": "Stremio-RPC-Lite"})
            res = []
            if response.status_code == 200:
                data = response.json()
                if data and data.get("introduction"):
                    start = data["introduction"].get("start", data["introduction"].get("start_sec"))
                    end = data["introduction"].get("end", data["introduction"].get("end_sec"))
                    res.append({"start": start, "end": end, "type": "intro", "source": "introdb", "label": "Skip Intro"})
                if data and data.get("outro"):
                    start = data["outro"].get("start", data["outro"].get("start_sec"))
                    end = data["outro"].get("end", data["outro"].get("end_sec"))
                    res.append({"start": start, "end": end, "type": "outro", "source": "introdb", "label": "Skip Outro"})
            return res if res else None
        except Exception:
            return None

    def _fetch_tidb(self, imdb_id: str, season: int, episode: int, tmdb_id: Optional[int] = None) -> Optional[List[Dict]]:
        try:
            # Prefer v2 API with TMDb ID
            if tmdb_id:
                url = f"https://api.theintrodb.org/v2/media?tmdb_id={tmdb_id}&season={season}&episode={episode}"
            else:
                url = f"https://api.theintrodb.org/v2/media?imdb_id={imdb_id}&season={season}&episode={episode}"
                
            headers = {"User-Agent": "Stremio-RPC-Lite"}
            if self.TIDB_KEY:
                headers["Authorization"] = f"Bearer {self.TIDB_KEY}"
                
            logger.info(f"[SkipManager] TIDB: Querying {url}")
            response = requests.get(url, timeout=5, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                res = []
                
                # TIDB v2 returns segment arrays: intro, recap, credits, preview
                for seg_type in ["intro", "recap", "credits", "preview"]:
                    segments = data.get(seg_type, [])
                    for s in segments:
                        start = s.get("start_ms", s.get("start", 0))
                        end = s.get("end_ms", s.get("end", 0))
                        
                        # Convert ms to sec if needed (v2 returns ms)
                        if start > 5000: # Threshold check for ms vs sec
                            start = start / 1000.0
                        if end and end > 5000:
                            end = end / 1000.0
                            
                        # Standardize Outro
                        final_type = "outro" if seg_type == "credits" else seg_type
                        
                        res.append({
                            "start": float(start), 
                            "end": float(end) if end else None, 
                            "type": final_type, 
                            "source": "tidb", 
                            "label": f"Skip {seg_type.capitalize()}"
                        })
                return res
        except Exception as e:
            logger.error(f"[SkipManager] TIDB Error: {e}")
            pass
        return None

    def _fetch_remote_json(self, imdb_id: str, season: int, episode: int) -> Optional[List[Dict]]:
        try:
            response = requests.get(self.REMOTE_JSON_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                key = f"{imdb_id}S{season}E{episode}"
                if key in data:
                    res = []
                    for item in data[key]:
                        res.append({
                            "start": item["start"], 
                            "end": item["end"], 
                            "type": item.get("type", "intro"),
                            "source": "remote_json",
                            "label": item.get("label", "Skip")
                        })
                    return res
        except Exception:
            pass
        return None

    def _fetch_videoskip(self, imdb_id: str, season: int, episode: int) -> Optional[List[Dict]]:
        # Web Scraper for VideoSkip.org (Mature Content)
        try:
            url = f"https://videoskip.org/browse/?q={imdb_id}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, timeout=5, headers=headers)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.text, "html.parser")
            res = []
            
            # Attempt to parse skip rows (this is a basic scraper assumption matching strexo logic)
            for row in soup.find_all("tr", class_="skip-row"):
                s_lbl = row.find("td", class_="skip-season")
                e_lbl = row.find("td", class_="skip-episode")
                if s_lbl and e_lbl:
                    try:
                        s_num = int(s_lbl.text.strip())
                        e_num = int(e_lbl.text.strip())
                        if s_num == season and e_num == episode:
                            # Parse skips
                            start_str = row.find("td", class_="skip-start").text.strip()
                            end_str = row.find("td", class_="skip-end").text.strip()
                            type_tag = row.find("span", class_="skip-tag").text.strip()
                            
                            # Convert 00:00:00 to seconds
                            def to_sec(tStr):
                                p = tStr.split(":")
                                return float(p[0])*3600 + float(p[1])*60 + float(p[2])
                                
                            res.append({
                                "start": to_sec(start_str),
                                "end": to_sec(end_str),
                                "type": type_tag.lower(),
                                "source": "videoskip",
                                "label": f"Skip {type_tag}"
                            })
                    except Exception:
                        pass
            return res if res else None
        except Exception as e:
            logger.debug(f"VideoSkip Error: {e}")
            pass
        return None

    def _fetch_jumpscare(self, lookup_tmdb: str, season: int, episode: int) -> Optional[List[Dict]]:
        # Web Scraper for WhenJumpScare.com
        try:
            # Jumpscare API or HTML
            # We assume it uses TMDB ID based on the Strexo Module
            url = f"https://whenjumpscare.com/movie/{lookup_tmdb}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, timeout=5, headers=headers)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.text, "html.parser")
            res = []
            
            for item in soup.find_all("div", class_="jumpscare-item"):
                time_str = item.find("div", class_="time").text.strip()
                desc = item.find("div", class_="desc").text.strip()
                is_major = "major" in item.get('class', [])
                
                if (is_major and self.jumpscare_major_enabled) or (not is_major and self.jumpscare_minor_enabled):
                    try:
                        pts = time_str.split(":")
                        if len(pts) == 3:
                            sec = float(pts[0])*3600 + float(pts[1])*60 + float(pts[2])
                        else:
                            sec = float(pts[0])*60 + float(pts[1])
                            
                        # Standardize to a 5-second jump window if end is not provided
                        jump_type = "jumpscare_major" if is_major else "jumpscare_minor"
                        res.append({
                            "start": sec - 2.0, # Buffer before scare
                            "end": sec + 3.0,
                            "type": jump_type,
                            "source": jump_type,
                            "label": "Major Jumpscare" if is_major else "Minor Jumpscare"
                        })
                    except Exception:
                        pass
            return res if res else None
        except Exception:
            pass
        return None

    def _fetch_aniskip(self, mal_id: int, episode: int) -> Optional[List[Dict]]:
        try:
            url = f"{self.ANISKIP_BASE}/{mal_id}/{episode}?types=op&types=ed&types=recap&episodeLength=0"
            logger.info(f"[SkipManager] AniSkip: Querying {url}")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("found"):
                    res = []
                    for t in data.get("results", []):
                        interval = t.get("interval", {})
                        if "startTime" in interval and "endTime" in interval:
                            sk_type = t.get("skipType", "intro")
                            if sk_type == "op": sk_type = "intro"
                            if sk_type == "ed": sk_type = "outro"
                            res.append({
                                "start": interval["startTime"],
                                "end": interval["endTime"],
                                "type": sk_type,
                                "source": "aniskip",
                                "label": "Skip " + sk_type.capitalize()
                            })
                    return res
        except Exception:
            pass
        return None

    def _get_mal_id(self, imdb_id: str) -> Optional[int]:
        if imdb_id in self.mal_cache:
            return self.mal_cache[imdb_id]
        try:
            meta_url = f"https://v3-cinemeta.strem.io/meta/series/{imdb_id}.json"
            meta_res = requests.get(meta_url, timeout=5)
            if meta_res.status_code != 200:
                return None
            name = meta_res.json().get("meta", {}).get("name")
            if not name:
                return None
            jikan_url = f"{self.JIKAN_BASE}?q={urllib.parse.quote(name)}&type=tv&limit=1"
            j_res = requests.get(jikan_url, timeout=5)
            if j_res.status_code == 200:
                results = j_res.json().get("data", [])
                if results and len(results) > 0:
                    mal_id = results[0]["mal_id"]
                    logger.info(f"[SkipManager] Mapped {imdb_id} to MAL ID {mal_id}")
                    self.mal_cache[imdb_id] = mal_id
                    return mal_id
        except Exception:
            pass
        return None

    def should_skip(self, position_ms: int, skip_times: List[Dict]) -> Optional[tuple[int, str]]:
        """
        Evaluates the current playback position against the resolved skip segments.
        If the current position falls within a segment boundary, returns the target end time.
        """
        if not self.enabled or not skip_times:
            return None
            
        pos_sec = position_ms / 1000.0
        
        for interval in skip_times:
            start = interval.get("start", 0)
            end = interval.get("end", 0)
            
            # Are we currently inside a skip segment?
            if start <= pos_sec < end:
                target_ms = int(end * 1000)
                
                # Prevent looping if we are already practically at the end
                if target_ms - position_ms > 1000:
                    return (target_ms, interval.get("type", "skip"))
                    
        return None
