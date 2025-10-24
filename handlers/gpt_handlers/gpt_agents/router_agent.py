from __future__ import annotations
from typing import Dict, Any, List, Optional
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent

class RouterAgent(PlanningAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)

    def include_additional_parts_to_prompt(self, extra_sections: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        return { 
            "role": "system",
            "content": "In the output JSON, you must include 'agent' with value: communication || search || cart || order."
            }

    async def plan_router(self, customerMessage: str,
                          language_id: Optional[str] = None) -> Dict[str, Any]:
        
        msgs = self.build_messages_with_system(
            "ROUTER_AGENT",
            customerMessage,
            language_id=language_id,
            variables=None
        )

        resp = await self.create_plan("plan_route", msgs)        
        return resp