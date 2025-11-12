from __future__ import annotations
import asyncio
import json
import time
from typing import Any, Dict, List
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent

class PlanningAgent(BaseAgent):

    def __init__(self, name: str):
        super().__init__(name=name)

    async def create_plan_with_tools(self, plan_name: str, message: str, class_name: BaseModel) -> Dict[str, Any]:
        start = time.perf_counter()

        self.logger.info(f"[TEST] Tools available: {tools}... plan name: {plan_name}... message: {message}")
        resp = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=self.get_small_llm_model(),
            messages=message,
            response_format=class_name,
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
    
    
