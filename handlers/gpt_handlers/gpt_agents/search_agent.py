from __future__ import annotations
import asyncio
from typing import Dict, Any, Literal, Optional, cast, Iterable
from pydantic import BaseModel, ConfigDict
from openai.types.chat import ChatCompletionMessageParam
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent

class SearchAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("search_agent_function_schema.json")

    async def plan_search(self, customer_message: str,
                          language_id: Optional[str] = None) -> ProductSearchResponse:

        msgs = self.build_messages_with_system(
            "SEARCH_AGENT",
            customer_message,
            language_id=language_id,
            variables={"SEARCH_TOOLS": self.tools}
        )
        resp = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=self.get_small_llm_model(),
            messages=cast("Iterable[ChatCompletionMessageParam]", msgs),
            response_format=ProductSearchResponse,
        )

        parsed = resp.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("Failed to parse search product response: parsed value is None")
        return parsed
    
    #dodati comunikacijskog agenta i sve dok se ne zavrsi i ne nadje proizvod ne izlazi iz agenta

class ProductSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name : str | None
    description: str
    productNumber: str | None
    quantity: int | None
    action: Literal["search_product_by_productNumber", "search_products_by_description", "list_products", "product_listing_by_category", "search_suggest", "get_product", "product_cross_selling", "find_variant"]