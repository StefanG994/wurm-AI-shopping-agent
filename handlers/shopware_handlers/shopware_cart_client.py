from __future__ import annotations
from typing import Any, Dict, Iterable, Mapping, Optional

from .shopware_base_client import ShopwareBaseClient
from .shopware_utils import wrap_response

class CartClient(ShopwareBaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name=self.__class__.__name__, **kwargs)

    async def get_or_create_cart(
        self,
        *,
        context_token: Optional[str] = None,
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Get existing cart or create new one."""
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("get_or_create_cart: headers=%s", headers)
        resp = await self._client.get("/checkout/cart", headers=headers)
        return wrap_response(resp)

    async def delete_cart(
        self,
        *,
        context_token: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        sales_channel_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete cart."""
        headers = self.create_header(
            context_token=context_token,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("delete_cart: headers=%s", headers)
        resp = await self._client.delete("/checkout/cart", headers=headers)
        return wrap_response(resp)

    async def add_line_items(
        self,
        *,
        items: Iterable[Mapping[str, Any]],
        context_token: Optional[str],
        language_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add items to cart."""
        payload = {"items": list(items)}
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "sw-access-key": self.access_key,
            "sw-context-token": context_token,
        }
        params = {'sw-language-id': language_id}
        self.logger.debug("add_line_items: headers=%s, payload=%s", headers, payload)
        resp = await self._client.post("/checkout/cart/line-item", headers=headers, json=payload, params=params)
        return wrap_response(resp)

    async def update_line_items(
        self,
        *,
        items: Iterable[Mapping[str, Any]],
        context_token: Optional[str],
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Update cart line items."""
        if not context_token:
            raise ValueError("update_line_items: context_token is required")
        payload = {"items": list(items)}
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("update_line_items: context_token=%s, headers=%s, payload=%s", context_token, headers, payload)
        resp = await self._client.patch("/checkout/cart/line-item", headers=headers, json=payload)
        return wrap_response(resp)

    async def remove_line_items(
        self,
        *,
        ids: Iterable[str],
        context_token: Optional[str],
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Remove items from cart."""
        if not context_token:
            raise ValueError("remove_line_items: context_token is required")
        payload = {"ids": list(ids)}
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self.logger.debug("remove_line_items: context_token=%s, headers=%s, payload=%s", context_token, headers, payload)
        resp = await self._client.request("DELETE", "/checkout/cart/line-item", headers=headers, json=payload)
        return wrap_response(resp)
