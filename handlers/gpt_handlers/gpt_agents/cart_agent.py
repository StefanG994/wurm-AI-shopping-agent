from __future__ import annotations
from typing import Dict, Any
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent

class CartAgent(PlanningAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.tools = self.load_function_schemas("cart_agent_function_schema.json")

    async def plan_cart(self, customerMessage: str) -> Dict[str, Any]:
        resp = await self.create_plan_with_tools("plan_cart", customerMessage, self.tools)
        return resp