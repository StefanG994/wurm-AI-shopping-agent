from __future__ import annotations
from typing import Dict, Any
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent

class ProductAgent(PlanningAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("product_agent_function_schema.json")

    async def plan_search(self, customer_message: str) -> Dict[str, Any]:
        resp = await self.create_plan_with_tools("plan_search", customer_message, self.tools)
        return resp