from bs4 import BeautifulSoup
from .daddyhd import DaddyHD
from . import BaseService
import re
import concurrent.futures


class DaddyHDCricket(DaddyHD):
    def __init__(self) -> None:
        BaseService.__init__(
            self,
            SERVICE_NAME="DaddyHDCricket",
            SERVICE_URL="https://dlhd.st/index.php?cat=Cricket+%F0%9F%8F%8F",
        )

    def _get_data(self) -> list:
        soup = BeautifulSoup(self._get_src(), "html.parser")
        
        # Find all watch.php links on the page (inside schedule or anywhere)
        links = soup.find_all("a", href=True)
        channels_to_resolve = {} # Use dict to deduplicate by channel_id
        
        for link in links:
            href = link.get("href").strip()
            match = re.search(r"[?&]id=(\d+)", href)
            if not match:
                continue
                
            channel_id = match.group(1)
            channel_name = link.text.strip() or link.get("title", "").strip() or f"Cricket {channel_id}"
            
            # Skip adult channels
            if "18+" in channel_name:
                continue
                
            # If already added, keep the first one
            if channel_id not in channels_to_resolve:
                channels_to_resolve[channel_id] = channel_name

        # Resolve streams in parallel to speed up playlist generation
        channels_data = []
        # Use 30 workers to resolve pages efficiently
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = {
                executor.submit(self._resolve_stream, cid, name): (cid, name)
                for cid, name in channels_to_resolve.items()
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
