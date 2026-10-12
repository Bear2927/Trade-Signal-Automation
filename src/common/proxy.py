"""Proxy rotation manager for Messenger scraper."""

import logging
import random
from typing import List, Optional

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages residential proxy pool with health checking."""

    def __init__(self, proxies: List[str] = None):
        """
        Args:
            proxies: List of proxy strings in format "host:port:user:pass"
        """
        self._proxies = proxies or []
        self._healthy_proxies: List[str] = []
        self._failed_proxies: dict = {}  # proxy -> failure_count
        self._max_failures = 3

    @classmethod
    def from_config(cls, proxy_string: str = "") -> "ProxyManager":
        """Create from config string (comma-separated proxies)."""
        proxies = [p.strip() for p in proxy_string.split(",") if p.strip()]
        return cls(proxies)

    def add_proxy(self, proxy: str) -> None:
        """Add a proxy to the pool."""
        if proxy not in self._proxies:
            self._proxies.append(proxy)
            logger.info(f"Added proxy: {self._mask_proxy(proxy)}")

    def get_proxy(self) -> Optional[str]:
        """Get a healthy proxy (random selection)."""
        if not self._healthy_proxies and self._proxies:
            # First time or all failed - try all
            self._healthy_proxies = self._proxies.copy()

        if not self._healthy_proxies:
            return None

        return random.choice(self._healthy_proxies)

    def mark_failed(self, proxy: str) -> None:
        """Mark proxy as failed, remove if too many failures."""
        if proxy not in self._failed_proxies:
            self._failed_proxies[proxy] = 0
        self._failed_proxies[proxy] += 1

        if self._failed_proxies[proxy] >= self._max_failures:
            self._remove_proxy(proxy)
            logger.warning(f"Proxy removed after {self._max_failures} failures: {self._mask_proxy(proxy)}")

    def mark_success(self, proxy: str) -> None:
        """Mark proxy as successful."""
        if proxy in self._failed_proxies:
            del self._failed_proxies[proxy]
        if proxy not in self._healthy_proxies and proxy in self._proxies:
            self._healthy_proxies.append(proxy)

    def _remove_proxy(self, proxy: str) -> None:
        """Remove proxy from all lists."""
        if proxy in self._proxies:
            self._proxies.remove(proxy)
        if proxy in self._healthy_proxies:
            self._healthy_proxies.remove(proxy)
        if proxy in self._failed_proxies:
            del self._failed_proxies[proxy]

    def _mask_proxy(self, proxy: str) -> str:
        """Mask credentials in proxy string for logging."""
        parts = proxy.split(":")
        if len(parts) >= 4:
            return f"{parts[0]}:{parts[1]}:***:***"
        return proxy

    def get_stats(self) -> dict:
        """Get proxy pool statistics."""
        return {
            "total": len(self._proxies),
            "healthy": len(self._healthy_proxies),
            "failed": len(self._failed_proxies),
            "proxies": [self._mask_proxy(p) for p in self._proxies],
        }

    def parse_proxy(self, proxy: str) -> dict:
        """Parse proxy string into Playwright/axios format."""
        parts = proxy.split(":")
        if len(parts) >= 4:
            return {
                "server": f"http://{parts[0]}:{parts[1]}",
                "username": parts[2],
                "password": parts[3],
            }
        elif len(parts) == 2:
            return {"server": f"http://{parts[0]}:{parts[1]}"}
        return {}


# Global instance
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """Get or create the global proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        from src.common.config import get_settings
        settings = get_settings()
        _proxy_manager = ProxyManager.from_config(settings.messenger.proxy)
    return _proxy_manager