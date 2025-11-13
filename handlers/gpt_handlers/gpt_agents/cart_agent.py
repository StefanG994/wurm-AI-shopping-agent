from __future__ import annotations
from typing import Dict, Any, List, Optional
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent

class CartAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("cart_agent_function_schema.json")

    async def plan_cart(self, customerMessage: str,
                    language_id: Optional[str] = None) -> Dict[str, Any]:
        
        msgs = self.build_messages_with_system(
            "CART_AGENT",
            customerMessage,
            language_id=language_id,
            variables={"CART_TOOLS": self.tools}
        )
        # resp = #napraviti klasu i pozivanje ka OpenAI
        # return resp