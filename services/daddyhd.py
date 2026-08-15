from urllib.parse import urlparse
from bs4 import BeautifulSoup
from . import BaseService
import requests
import re
import base64
import concurrent.futures


class DaddyHD(BaseService):
    def __init__(self) -> None:
        super().__init__(
            SERVICE_NAME="DaddyHD",
            SERVICE_URL="https://dlhd.st/24-7-channels.php",
        )

    def _resolve_stream(self, channel_id: str, channel_name: str) -> dict:
        """Resolves the secure stream URL and referer for a given channel ID."""
        stream_page_url = f"https://dlhd.st/stream/stream-{channel_id}.php"
        referer_watch = f"https://dlhd.st/watch.php?id={channel_id}"
        
        try:
            # Step 1: Fetch the stream page to get the player iframe
            res = self.requests_session.get(stream_page_url, headers={"Referer": referer_watch}, timeout=10)
            if res.status_code != 200:
                return None
                
            soup = BeautifulSoup(res.text, "html.parser")
            iframe = soup.find("iframe", {"id": "thatframe"})
            if not iframe:
                return None
                
            iframe_url = iframe.get("src")
            if not iframe_url:
                return None
                
            # Step 2: Fetch the player iframe to extract the stream URL
            iframe_parsed = urlparse(iframe_url)
            iframe_origin = f"{iframe_parsed.scheme}://{iframe_parsed.netloc}/"
            
            res_iframe = self.requests_session.get(iframe_url, headers={"Referer": "https://dlhd.st/"}, timeout=10)
            if res_iframe.status_code != 200:
                return None
                
            # Extract the base64 encoded stream source
            pattern = r"window\.atob\('([^']+)'\)"
            match = re.search(pattern, res_iframe.text)
            if not match:
                return None
                
            encoded_url = match.group(1)
            stream_url = base64.b64decode(encoded_url).decode('utf-8', errors='ignore')
            
            return {
                "name": channel_name,
                "logo": "",
                "group": "DaddyHD",
                "stream-url": stream_url,
                "headers": {
                    "referer": iframe_origin,
                    "user-agent": self.USER_AGENT
                }
            }
        except Exception:
            return None

    def _get_data(self) -> list:
        soup = BeautifulSoup(self._get_src(), "html.parser")
        cards = soup.select("a.card")
        
        channels_to_resolve = []
        for card in cards:
            channel_slug = card.get("href", "").strip()
            match = re.search(r"[?&]id=(\d+)", channel_slug)
            if not match:
                continue
                
            channel_id = match.group(1)
            channel_name = card.select_one(".card__title")
            if not channel_name:
                continue
            channel_name = channel_name.text.strip()
            
            if "18+" in channel_name:
                continue
                
            channels_to_resolve.append((channel_id, channel_name))

        # Resolve streams in parallel to speed up playlist generation
        channels_data = []
        # Use 30 workers to resolve pages efficiently
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = {
                executor.submit(self._resolve_stream, cid, name): (cid, name)
                for cid, name in channels_to_resolve
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        channels_data.append(result)
                except Exception:
                    pass

        # Sort the channels by name for readability/consistency
        channels_data.sort(key=lambda x: x["name"])
        return channels_data
