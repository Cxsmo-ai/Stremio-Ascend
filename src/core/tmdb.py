import logging
import requests
from typing import Optional, Dict
from PIL import Image
from io import BytesIO

logger = logging.getLogger("stremio-rpc")

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.cache = {}
        self.genre_map = {"movie": {}, "tv": {}}
        self._fetch_genres()

    def _fetch_genres(self):
        """Pre-fetch genre mappings for movies and TV shows"""
        if not self.api_key: return
        try:
            for mtype in ["movie", "tv"]:
                resp = self.session.get(f"{self.BASE_URL}/genre/{mtype}/list", params={"api_key": self.api_key})
                if resp.status_code == 200:
                    for g in resp.json().get("genres", []):
                        self.genre_map[mtype][g["id"]] = g["name"]
        except: pass

    def get_full_details(self, media_id: int, media_type: str) -> Optional[Dict]:
        """Fetch rich details including cast, genres, and ratings"""
        if not self.api_key or not media_id: return None
        try:
            url = f"{self.BASE_URL}/{media_type}/{media_id}"
            params = {
                "api_key": self.api_key,
                "append_to_response": "credits,external_ids"
            }
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            genres = [g.get("name") for g in data.get("genres", [])]
            cast = [c.get("name") for c in data.get("credits", {}).get("cast", [])[:3]] # Top 3
            imdb_id = data.get("external_ids", {}).get("imdb_id")
            
            network_logo = None
            network_name = None
            if media_type == "tv" and data.get("networks"):
                network = data["networks"][0]
                logo_path = network.get("logo_path")
                network_name = network.get("name")
                if logo_path: network_logo = f"{self.IMAGE_BASE_URL}{logo_path}"
            elif media_type == "movie" and data.get("production_companies"):
                prod = data["production_companies"][0]
                logo_path = prod.get("logo_path")
                network_name = prod.get("name")
                if logo_path: network_logo = f"{self.IMAGE_BASE_URL}{logo_path}"

            return {
                "genres": genres,
                "cast": cast,
                "vote_average": data.get("vote_average"),
                "vote_count": data.get("vote_count"),
                "imdb_id": imdb_id,
                "tagline": data.get("tagline"),
                "network_logo": network_logo,
                "network_name": network_name
            }
        except Exception as e:
            logger.error(f"TMDB full details failed: {e}")
            return None

    def search_content(self, query: str, media_type_hint: str = None) -> Optional[Dict]:
        if not self.api_key or not query:
            return None

        if query in self.cache:
            return self.cache[query]

        try:
            # 1. Search Multi
            params = {
                "api_key": self.api_key,
                "query": query,
                "include_adult": False
            }
            response = self.session.get(f"{self.BASE_URL}/search/multi", params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
            
            # Reorder results to prioritize media_type_hint if provided
            if media_type_hint:
                results.sort(key=lambda x: 0 if x.get("media_type") == media_type_hint else 1)

            for item in results:
                if item["media_type"] in ["movie", "tv"]:
                    # 2. Get External IDs (IMDb)
                    media_id = item["id"]
                    media_type = item["media_type"]
                    
                    try:
                        ext_resp = self.session.get(f"{self.BASE_URL}/{media_type}/{media_id}/external_ids", params={"api_key": self.api_key})
                        ext_data = ext_resp.json()
                        imdb_id = ext_data.get("imdb_id")
                    except:
                        imdb_id = None

                    processed = self._process_item(item, imdb_id)
                    self.cache[query] = processed
                    return processed
            return None
        except Exception as e:
            logger.error(f"TMDB search failed: {e}")
            return None

    def get_season_details(self, tv_id: int, season: int) -> Optional[Dict]:
        """Fetch specific season details including posters"""
        if not self.api_key or not tv_id: return None
        try:
            url = f"{self.BASE_URL}/tv/{tv_id}/season/{season}"
            params = {"api_key": self.api_key}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            poster_path = data.get("poster_path")
            image_url = f"{self.IMAGE_BASE_URL}{poster_path}" if poster_path else None
            return {
                "name": data.get("name"),
                "image_url": image_url,
                "overview": data.get("overview")
            }
        except Exception as e:
            logger.error(f"TMDB Season lookup failed: {e}")
            return None

    def get_content_trailer(self, media_id: int, media_type: str) -> Optional[str]:
        """Fetch primary YouTube trailer URL"""
        if not self.api_key or not media_id: return None
        try:
            url = f"{self.BASE_URL}/{media_type}/{media_id}/videos"
            params = {"api_key": self.api_key}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            videos = response.json().get("results", [])
            
            # Look for YouTube Trailer
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                    return f"https://www.youtube.com/watch?v={v.get('key')}"
            
            # Fallback to any Teaser if no trailer
            for v in videos:
                if v.get("site") == "YouTube":
                    return f"https://www.youtube.com/watch?v={v.get('key')}"
            return None
        except Exception as e:
            logger.error(f"TMDB Trailer lookup failed: {e}")
            return None

    def get_episode_details(self, tv_id: int, season: int, episode: int) -> Optional[Dict]:
        """Fetch specific episode details"""
        if not self.api_key or not tv_id: return None
        
        try:
            url = f"{self.BASE_URL}/tv/{tv_id}/season/{season}/episode/{episode}"
            params = {"api_key": self.api_key}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            still_path = data.get("still_path")
            image_url = f"{self.IMAGE_BASE_URL}{still_path}" if still_path else None
            
            return {
                "name": data.get("name"),
                "overview": data.get("overview"),
                "image_url": image_url,
                "vote_average": data.get("vote_average"),
                "runtime_ms": (data.get("runtime", 0) or 0) * 60 * 1000  # Convert minutes to milliseconds
            }
        except Exception as e:
            logger.error(f"TMDB Episode lookup failed: {e}")
            return None

    def _process_item(self, item: Dict, imdb_id: str = None) -> Dict:
        poster_path = item.get("poster_path")
        image_url = f"{self.IMAGE_BASE_URL}{poster_path}" if poster_path else None
        
        return {
            "title": item.get("title") or item.get("name"),
            "id": item["id"],
            "imdb_id": imdb_id,
            "type": item["media_type"],
            "image_url": image_url,
            "overview": item.get("overview", "")
        }

    def download_image(self, url: str) -> Optional[Image.Image]:
        if not url: return None
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except Exception:
            return None
