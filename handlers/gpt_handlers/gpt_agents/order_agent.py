from __future__ import annotations
from typing import Dict, Any, Optional
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent

class OrderAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("order_agent_function_schema.json")

    async def plan_order(self, customerMessage: str,
                         language_id: Optional[str] = None) -> Dict[str, Any]:
        
        msgs = self.build_messages_with_system(
            "ORDER_AGENT",
            customerMessage,
            language_id=language_id,
            variables={"ORDER_TOOLS": self.tools}
        )

        # resp = await self.create_plan_with_tools("plan_order", msgs, self.tools)
        # return resp