from __future__ import annotations
import asyncio
import time
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent
from handlers.multi_intent import MultiIntentResponse, build_multi_intent_prompt


class IntentAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)

    async def classify_multi_intent(self, user_message: str) -> MultiIntentResponse:

        start = time.perf_counter()
        prompt = build_multi_intent_prompt(user_message, True)
        messages = prompt

        intent_response = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=self.get_small_llm_model(),
            messages=messages,
            response_format=MultiIntentResponse,
        )

        elapsed = time.perf_counter() - start
        self.logger.info(f"INTENT CATEGORIZATION FINISHED IN: {elapsed:.2f} seconds")
        return intent_response.choices[0].message.parsed
    
    
