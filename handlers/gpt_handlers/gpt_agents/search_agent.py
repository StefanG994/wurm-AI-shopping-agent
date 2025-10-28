from __future__ import annotations
from typing import Dict, Any, Optional
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent

class SearchAgent(PlanningAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("search_agent_function_schema.json")

    async def plan_search(self, customer_message: str,
                          language_id: Optional[str] = None) -> Dict[str, Any]:

        msgs = self.build_messages_with_system(
            "SEARCH_AGENT",
            customer_message,
            language_id=language_id,
            variables={"SEARCH_TOOLS": self.tools}
        )
        resp = await self.create_plan_with_tools("plan_search", msgs, self.tools)
        return resp