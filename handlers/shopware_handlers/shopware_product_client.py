from __future__ import annotations
from typing import Any, Dict, List, Mapping, Optional, Union
import httpx
from copy import deepcopy

from .shopware_base_client import ShopwareBaseClient
from .shopware_utils import SimpleHeaderInfo, wrap_response

class ProductClient(ShopwareBaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name=self.__class__.__name__, **kwargs)
        self.load_shopware_includes("shopware_product_includes.json")

    async def search_products_by_description(
        self,
        *,
        payload: Dict[str, Any],
        # Headers
        header_info: Optional[SimpleHeaderInfo] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        
        self.logger.info("[TEST] PAYLOAD IN SEARCH}, body=%s", payload)
        # END: TODO switch this part so that we get only payload and headers
        # Headers + params
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "sw-access-key": self.access_key,
            "sw-context-token": header_info.contextToken if header_info else "",
        }

        # Includes handling
        payload["includes"] = self.merge_includes(default_includes=self.get_action_includes("Default"), user_includes=payload.get("includes", {}))
        self.logger.info("[TEST] PAYLOAD INCLUDES}, body=%s", payload["includes"])
        # if payload.get("includes") is not None:
        #     existing = payload.get("includes") or {}
        #     payload["includes"] = self.merge_includes(payload.get("includes"), existing) if isinstance(existing, dict) else payload.get("includes")
        # if use_default_includes:
        #     payload["includes"] = self.merge_includes(DEFAULT_INCLUDES, payload.get("includes", {}))

        params: Dict[str, Any] = {"sw-language-id": header_info.languageId if header_info else None}
        # if p is not None:
        #     params["p"] = p

        self.logger.info("search_products: params=%s, headers=%s, body=%s", params, headers, payload)
        try:
            resp = await self._client.post("/search", headers=headers, json=payload, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if resp.status_code == 412 and header_info and header_info.contextToken:
                self.logger.warning("search_products: 412 with context token; retrying without token")
                hdrs = self.create_header(
                    context_token=None,
                    language_id=header_info.languageId if header_info else None,
                    extra=headers,
                )

                resp = await self._client.post("/search", headers=hdrs, json=payload, params=params)
                resp.raise_for_status()
            else:
                raise
                
        return wrap_response(resp)

    async def get_product(
        self,
        productId: str,
        *,
        body: Optional[Mapping[str, Any]] = None,
        context_token: Optional[str] = None,
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Get single product by ID."""
        payload = deepcopy(body or {})
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("get_product: productId=%s, headers=%s, body=%s", productId, headers, payload)
        resp = await self._client.post(f"/product/{productId}", headers=headers, json=payload)
        return wrap_response(resp)

    async def list_products(
        self,
        *,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """List products by criteria."""
        payload = deepcopy(body or {})
        headers = self.create_header()
        self.logger.debug("list_products: headers=%s, body=%s", headers, payload)
        resp = await self._client.post("/product", headers=headers, json=payload)
        return wrap_response(resp)

    async def find_variant(
        self,
        productId: str,
        *,
        options: Union[List[str], Mapping[str, str]],
        switched_group: Optional[str] = None,
        context_token: Optional[str] = None,
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Find product variant by options."""
        payload: Dict[str, Any] = {"options": options}
        if switched_group:
            payload["switchedGroup"] = switched_group
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("find_variant: productId=%s, headers=%s, payload=%s", productId, headers, payload)
        resp = await self._client.post(f"/product/{productId}/find-variant", headers=headers, json=payload)
        return wrap_response(resp)

    async def product_listing_by_category(
        self,
        category_id: str,
        *,
        body: Optional[Mapping[str, Any]] = None,
        p: Optional[int] = None,
        context_token: Optional[str] = None,
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Get product listing by category."""
        params = {}
        payload = deepcopy(body or {})
        if p is not None:
            params["p"] = p
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("product_listing_by_category: category_id=%s, headers=%s, body=%s", category_id, headers, payload)
        resp = await self._client.post(f"/product-listing/{category_id}", params=params, headers=headers, json=payload)
        return wrap_response(resp)

    async def get_product_by_productNumber(self, productNumber: str, language_id: str) -> Optional[str]:
        """Fetch a product by productNumber and return full response."""
        url = "/product"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "sw-access-key": self.access_key
        }
        body = {
            "filter": [
                {"type": "equals", "field": "active", "value": True},
                {"type": "equals", "field": "productNumber", "value": productNumber}
            ],
            "limit": 10
        }
        params = {'sw-language-id': language_id}
        resp = await self._client.post(url, headers=headers, json=body, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data

    async def get_productId_by_number(self, productNumber: str, language_id: str) -> Optional[str]:
        """Fetch a product by productNumber and return its productId."""
        url = "/product"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "sw-access-key": self.access_key
        }
        body = {
            "filter": [
                {"type": "equals", "field": "active", "value": True},
                {"type": "equals", "field": "productNumber", "value": productNumber}
            ],
            "limit": 10
        }
        params = {'sw-language-id': language_id}
        resp = await self._client.post(url, headers=headers, json=body, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        elements = (data or {}).get("elements") or []
        if not elements:
            return None

        first = elements[0] or {}
        # 1) Typical location: elements[0].cover.productId
        cover = first.get("cover")
        if isinstance(cover, dict):
            pid = cover.get("productId")
            if isinstance(pid, str) and pid:
                return pid

        # 2) Fallback: search the first element for the first occurrence of key == 'productId'
        def _find_productId(obj):
            if isinstance(obj, dict):
                if "productId" in obj and isinstance(obj["productId"], str) and obj["productId"]:
                    return obj["productId"]
                for v in obj.values():
                    found = _find_productId(v)
                    if found:
                        return found
            elif isinstance(obj, list):
                for v in obj:
                    found = _find_productId(v)
                    if found:
                        return found
            return None

        return _find_productId(first)

