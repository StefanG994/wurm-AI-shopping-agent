from __future__ import annotations
import json
from typing import Dict, Any, List, Optional
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent

class CommunicationAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("communication_agent_function_schema.json")

    def include_additional_parts_to_prompt(self, extra_sections: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if extra_sections:
            for title, content in extra_sections.items():
                return {"role": "user", "content": f"{title}:\n{content}"}

    async def plan_communication(self, seed: Dict[str, Any],
                                 customerMessage: str = "",
                                 language_id: Optional[str] = None) -> Dict[str, Any]:
        
        msgs = self.build_messages_with_system(
            "COMM_AGENT",
            customerMessage,
            language_id=language_id,
            variables={"COMM_TOOLS": self.tools},
            extra_sections={"SEED": json.dumps(seed, ensure_ascii=False)}
        )

        # return await self.create_plan_with_tools("plan_communication", msgs)
