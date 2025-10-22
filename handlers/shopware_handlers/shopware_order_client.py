from __future__ import annotations
from typing import Any, Dict, Mapping, Optional

from .shopware_base_client import ShopwareBaseClient
from .shopware_utils import wrap_response

class OrderClient(ShopwareBaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name=self.__class__.__name__, **kwargs)

    async def fetch_orders_list(
        self,
        *,
        context_token: Optional[str],
        language_id: Optional[str] = None,
        sales_channel_id: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Fetch list of orders for the customer."""
        if not context_token:
            raise ValueError("fetch_orders_list: context_token is required")
        
        body = {
            "limit": 1,
            "associations": {
                "deliveries": {
                    "associations": {
                        "stateMachineState": {}
                    }
                }
            },
            "sort": [
                {
                    "field": "createdAt",
                    "order": "DESC"
                }
            ]
        }
        
        headers = self.create_header(
            context_token=context_token,
            language_id=language_id,
            sales_channel_id=sales_channel_id,
            extra=extra_headers,
        )

        self.logger.info("fetch_orders_list: context_token=%s, headers=%s, payload=%s", context_token, headers, body)
        resp = await self._client.request("POST", "/order", headers=headers, json=body)

        return wrap_response(resp)
