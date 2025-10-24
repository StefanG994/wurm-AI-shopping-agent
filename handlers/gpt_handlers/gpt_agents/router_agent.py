from __future__ import annotations
from typing import Dict, Any, List, Optional
from handlers.gpt_handlers.gpt_agents.intent_agent import IntentAgent
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent
from main import SimpleHeaderInfo

class RouterAgent(PlanningAgent):
    
    def __init__(self, header_info: SimpleHeaderInfo):
        super().__init__(name=self.__class__.__name__, header_info=header_info)
        self.intent_agent = IntentAgent()

    def include_additional_parts_to_prompt(self, extra_sections: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        return { 
            "role": "system",
            "content": "In the output JSON, you must include 'agent' with value: communication || search || cart || order."
            }

    async def get_response(self, customerMessage: str) -> Dict[str, Any]:
        #plan = await self.plan_router(customerMessage)
        response = await self.intent_agent.classify_multi_intent(customerMessage)
                
        return response

    async def plan_router(self, customerMessage: str) -> Dict[str, Any]:
        
        msgs = self.build_messages_with_system(
            "ROUTER_AGENT",
            customerMessage,
            language_id=self.header_info.languageId,
            variables=None
        )

        resp = await self.create_plan("plan_route", msgs)        
        return resp