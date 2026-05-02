import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger("stremio-rpc")

class MDBListClient:
    BASE_URL = "https://mdblist.com/api/"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.cache = {}

    def get_ratings(self, imdb_id: str) -> Optional[Dict]:
        """Fetch all aggregated ratings from MDBList for an IMDB ID"""
        if not self.api_key or not imdb_id:
            return None

        if imdb_id in self.cache:
            return self.cache[imdb_id]

        try:
            params = {
                "apikey": self.api_key,
                "i": imdb_id
            }
            resp = self.session.get(self.BASE_URL, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                
                # Extract relevant ratings
                ratings = {
                    "imdb": "N/A",
                    "metacritic": "N/A",
                    "rotten_tomatoes": "N/A",
                    "trakt": "N/A",
                    "score": "N/A"
                }

                # MDBList maps these in an array or specific fields
                # We want the 'score' (MDBList average) and others
                ratings["score"] = data.get("score", "N/A")
                
                for r in data.get("ratings", []):
                    source = r.get("source", "").lower()
                    val = r.get("value", "N/A")
                    
                    if "imdb" in source: ratings["imdb"] = str(val)
                    elif "metacritic" in source: ratings["metacritic"] = str(val)
                    elif "rotten" in source: ratings["rotten_tomatoes"] = str(val)
                    elif "trakt" in source: ratings["trakt"] = str(val)

                self.cache[imdb_id] = ratings
                return ratings
            return None
        except Exception as e:
            logger.error(f"MDBList lookup failed: {e}")
            return None
