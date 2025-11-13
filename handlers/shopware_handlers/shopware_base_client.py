from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Mapping, Optional
import httpx
from dotenv import load_dotenv
import logging

from handlers.shopware_handlers.shopware_utils import _make_timeout

includes_dir = "shopware_response_includes"
load_dotenv()

class ShopwareBaseClient:

    def __init__(
        self,
        base_url: Optional[str] = None,
        access_key: Optional[str] = None,
        default_language_id: Optional[str] = None,
        timeout: float = os.getenv("TIMEOUT", 60.0),
        client: Optional[httpx.AsyncClient] = None,
        name: str = "ShopwareBaseClient"
    ):
        self.logger = logging.getLogger(name)

        self.base_url = (base_url or os.getenv("SHOPWARE_API_BASE") or "").rstrip("/")
        if not self.base_url:
            raise RuntimeError("SHOPWARE_API_BASE is not set")
        self.access_key = access_key or os.getenv("SHOPWARE_ACCESS_KEY")
        if not self.access_key:
            raise RuntimeError("SHOPWARE_ACCESS_KEY is not set")
        self.default_language_id = default_language_id or os.getenv("SHOPWARE_LANGUAGE_ID")
        
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=_make_timeout(timeout))
            self._owns_client = True
            

    def create_header(
        self,
        *,
        context_token: Optional[str] = None,
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        """Build headers for Shopware API requests."""
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "sw-access-key": self.access_key,
        }
        lang = language_id or self.default_language_id
        if lang:
            headers["sw-language-id"] = lang
        if context_token:
            headers["sw-context-token"] = context_token
        if sales_channel_id:
            headers["sw-sales-channel-id"] = sales_channel_id
        if extra:
            headers.update({k: str(v) for k, v in extra.items()})
        return headers
    
    def load_shopware_includes(self, includes_name: str):
        base_dir = os.path.dirname(__file__)
        includes_path = os.path.join(base_dir, includes_dir, includes_name)
        with open(includes_path, "r", encoding="utf-8") as f:
            self.includes =  json.load(f)

    def get_action_includes(self, predefined_includes_group: str) -> Any:

        for item in self.includes:
            for includes_name, includes_value in item.items():
                if includes_name == predefined_includes_group or includes_name.lower() == predefined_includes_group.lower():
                    return includes_value

        return {}
    
    def merge_includes(self,
        user_includes: Optional[Mapping[str, List[str]]],
        default_includes: Optional[Mapping[str, List[str]]] = None,
    ) -> Dict[str, List[str]]:

        result: Dict[str, List[str]] = {}
        bases = [default_includes or {}, user_includes or {}]
        for inc in bases:
            for alias, fields in inc.items():
                existing = set(result.get(alias, []))
                existing.update(fields or [])
                result[alias] = list(existing)
        return result

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "ShopwareBaseClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()