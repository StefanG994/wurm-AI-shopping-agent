from __future__ import annotations
from typing import Dict, Any
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent

class RouterAgent(PlanningAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)

    async def plan_router(self, customerMessage: str) -> Dict[str, Any]:
        resp = await self.create_plan("plan_router", customerMessage)        
        return resp