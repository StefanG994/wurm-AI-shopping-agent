from __future__ import annotations
from typing import Any, Dict, List, Mapping, Optional, Union
import httpx
from copy import deepcopy

from .shopware_base_client import ShopwareBaseClient
from .shopware_utils import wrap_response

class ProductClient(ShopwareBaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name=self.__class__.__name__, **kwargs)

    async def search_products(
        self,
        *,
        # Core search payload (per docs)
        search: Optional[str] = None,
        filter: Optional[List[Dict[str, Any]]] = None,
        sort: Optional[List[Dict[str, Any]]] = None,
        post_filter: Optional[List[Dict[str, Any]]] = None,
        page: Optional[int] = None,
        term: Optional[str] = None,
        limit: Optional[int] = None,
        ids: Optional[List[str]] = None,
        query: Optional[str] = None,
        associations: Optional[Dict[str, Any]] = None,
        aggregations: Optional[List[Dict[str, Any]]] = None,
        fields: Optional[List[str]] = None,
        grouping: Optional[List[str]] = None,
        quantity_mode: Optional[str] = None,
        # Listing flags from the storefront layer
        order: Optional[str] = None,
        p: Optional[int] = None,  # query-string page (Shopware supports ?p=)
        manufacturer: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        rating: Optional[int] = None,
        shipping_free: Optional[bool] = None,
        properties: Optional[str] = None,
        manufacturer_filter: Optional[bool] = None,
        price_filter: Optional[bool] = None,
        rating_filter: Optional[bool] = None,
        shipping_free_filter: Optional[bool] = None,
        property_filter: Optional[bool] = None,
        property_whitelist: Optional[str] = None,
        reduce_aggregations: Optional[str] = None,
        no_aggregations: Optional[str] = None,
        only_aggregations: Optional[str] = None,
        # Back-compat direct body merge (optional)
        body: Optional[Mapping[str, Any]] = None,
        # Headers
        context_token: Optional[str] = None,
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:

        payload: Dict[str, Any] = {} if body is None else dict(body)

        def put(k: str, v: Any) -> None:
            if v is not None:
                payload[k] = v

        # Core body
        put("search", search)
        put("filter", filter)
        put("sort", sort)
        if post_filter is not None:
            payload["post-filter"] = post_filter
        put("page", page)
        put("term", term)
        put("limit", limit)
        put("ids", ids)
        put("query", query)
        put("associations", associations)
        put("aggregations", aggregations)
        put("fields", fields)
        put("grouping", grouping)
        if quantity_mode is not None:
            payload["quantity-mode"] = quantity_mode

        # Storefront flags
        put("order", order)
        put("manufacturer", manufacturer)
        if min_price is not None:
            payload["min-price"] = min_price
        if max_price is not None:
            payload["max-price"] = max_price
        put("rating", rating)
        if shipping_free is not None:
            payload["shipping-free"] = shipping_free
        put("properties", properties)
        if manufacturer_filter is not None:
            payload["manufacturer-filter"] = manufacturer_filter
        if price_filter is not None:
            payload["price-filter"] = price_filter
        if rating_filter is not None:
            payload["rating-filter"] = rating_filter
        if shipping_free_filter is not None:
            payload["shipping-free-filter"] = shipping_free_filter
        if property_filter is not None:
            payload["property-filter"] = property_filter
        if property_whitelist is not None:
            payload["property-whitelist"] = property_whitelist
        if reduce_aggregations is not None:
            payload["reduce-aggregations"] = reduce_aggregations
        if no_aggregations is not None:
            payload["no-aggregations"] = no_aggregations
        if only_aggregations is not None:
            payload["only-aggregations"] = only_aggregations

        # Headers + params
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "sw-access-key": self.access_key,
            "sw-context-token": context_token
        }
        params: Dict[str, Any] = {"sw-language-id": language_id}
        if p is not None:
            params["p"] = p

        self._log.info("search_products: params=%s, headers=%s, body=%s", params, headers, payload)
        try:
            resp = await self._client.post("/search", headers=headers, json=payload, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if resp.status_code == 412 and context_token:
                self._log.warning("search_products: 412 with context token; retrying without token")
                hdrs = self._headers(
                    context_token=None,  # <- drop the token
                    language_id=language_id,
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
        headers = self._headers(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self._log.debug("get_product: productId=%s, headers=%s, body=%s", productId, headers, payload)
        resp = await self._client.post(f"/product/{productId}", headers=headers, json=payload)
        return wrap_response(resp)

    async def list_products(
        self,
        *,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """List products by criteria."""
        payload = deepcopy(body or {})
        headers = self._headers()
        self._log.debug("list_products: headers=%s, body=%s", headers, payload)
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
        headers = self._headers(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self._log.debug("find_variant: productId=%s, headers=%s, payload=%s", productId, headers, payload)
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
        headers = self._headers(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )
        self._log.debug("product_listing_by_category: category_id=%s, headers=%s, body=%s", category_id, headers, payload)
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

