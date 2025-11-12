from __future__ import annotations
import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent
from handlers.shopware_handlers.shopware_base_client import ShopwareBaseClient

class PlanningAgent(BaseAgent):

    def __init__(self, name: str):
        super().__init__(name=name)

    async def create_plan_with_tools(self, plan_name: str, message: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        start = time.perf_counter()

        self.logger.info(f"[TEST] Tools available: {tools}... plan name: {plan_name}... message: {message}")
        resp = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.get_small_llm_model(),
            messages=message,
            tools=[{"type": "function", "function": f} for f in tools],
            tool_choice="none",
            response_format={"type": "json_object"},
        )
        
        self.logger.info(f"[TEST] RESP: {resp}")
        elapsed = time.perf_counter() - start
        self.logger.info(f"{plan_name} finished in: {elapsed:.2f} seconds")

        return json.loads(resp.choices[0].message.content or "{}")
	
    async def create_plan(self, plan_name: str, message: str) -> Dict[str, Any]:
        start = time.perf_counter()

        resp = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.get_small_llm_model(),
            messages=message,
            response_format={"type": "json_object"},
        )
        
        elapsed = time.perf_counter() - start
        self.logger.info(f"{plan_name} finished in: {elapsed:.2f} seconds")

        return json.loads(resp.choices[0].message.content or "{}")
    
    async def plan_and_execute(self, seed: Optional[Dict[str, Any]] = None,
                                 customerMessage: str = "",
                                 language_id: Optional[str] = None) -> Dict[str, Any]:
        self.logger.info("Plan and execute called in base PlanningAgent")
        raise NotImplementedError("Subclasses must implement plan_and_execute method")
    
    def set_shopware_client(self, shopware_client: ShopwareBaseClient) -> None:
        self.shopware_client = shopware_client