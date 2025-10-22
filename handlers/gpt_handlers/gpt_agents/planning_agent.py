from __future__ import annotations
import asyncio
import json
import time
from typing import Any, Dict, List
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent
from handlers.prompts_translated.get_translated_prompt import get_translated_prompt

class PlanningAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)


    async def create_plan_with_tools(self, plan_name: str, message: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        start = time.perf_counter()

        resp = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.get_small_llm_model(),
            temperature=0.2,
            messages=message,
            tools=[{"type": "function", "function": f} for f in tools],
            tool_choice="none",
            response_format={"type": "json_object"},
        )
        
        elapsed = time.perf_counter() - start
        self.logger.info(f"{plan_name} finished in: {elapsed:.2f} seconds")

        return json.loads(resp.choices[0].message.content or "{}")
	
    async def create_plan(self, plan_name: str, message: str) -> Dict[str, Any]:
        start = time.perf_counter()

        resp = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.get_small_llm_model(),
            temperature=0.2,
            messages=message,
            response_format={"type": "json_object"},
        )
        
        elapsed = time.perf_counter() - start
        self.logger.info(f"{plan_name} finished in: {elapsed:.2f} seconds")

        return json.loads(resp.choices[0].message.content or "{}")
    
    
