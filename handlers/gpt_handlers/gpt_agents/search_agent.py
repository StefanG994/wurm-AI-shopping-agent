from __future__ import annotations
import json
import logging
from typing import Dict, Any, Optional
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent
from handlers.shopware_handlers.shopware_product_client import ProductClient
from handlers.shopware_handlers.shopware_utils import SimpleHeaderInfo

class SearchAgent(PlanningAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("search_agent_function_schema.json")
        self.set_shopware_client(ProductClient())

    async def plan_search(self, seed: Dict[str, Any], customer_message: str,
                          language_id: Optional[str] = None) -> Dict[str, Any]:

        msgs = self.build_messages_with_system(
            "SEARCH_AGENT",
            customer_message,
            language_id=language_id,
            variables={"SEARCH_TOOLS": self.tools},
            extra_sections={"SEED": json.dumps(seed, ensure_ascii=False)}
        )
        return await self.create_plan_with_tools("plan_search", msgs, self.tools)
    
    async def plan_and_execute(self, seed: Optional[Dict[str, Any]] = None,
                                 customerMessage: str = "",
                                 header_info: Optional[SimpleHeaderInfo] = None) -> Dict[str, Any]:
        self.logger.info("Plan and execute called in Search Agent")
        search_plan = await self.plan_search(seed or {}, customerMessage, language_id=header_info.languageId if header_info else None)

        steps = search_plan.get("steps") or []
        for step in steps:
            action = step.get("action")
            self.logger.info("ACTION: %s", action)
            params = step.get("parameters") or {}
            payload, missing_params = self.get_function_parameter_info(action, params)
            self.logger.info("PAYLOAD AFTER METHOD: %s", json.dumps(payload))
            self.logger.info("MISSING AFTER METHOD: %s", missing_params)

            shopware_method = getattr(self.shopware_client, action, None)
            if callable(shopware_method):
                self.logger.info(f"Executing method for action '{action}'")
                return await shopware_method(payload=payload, header_info=header_info)
            else:
                self.logger.error(f"No method found for action '{action}'")