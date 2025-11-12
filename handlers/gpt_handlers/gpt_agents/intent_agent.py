from __future__ import annotations
import asyncio
import time
from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent
from handlers.multi_intent import MultiIntentResponse, PrimaryGoals, build_multi_intent_prompt, build_primary_intent_prompt

class IntentAgent(BaseAgent):

    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        # START TESTING PART
        self.load_function_schemas("search_agent_function_schema.json")
        self.load_function_schemas("cart_agent_function_schema.json")
        self.load_function_schemas("order_agent_function_schema.json")
        self.load_function_schemas("communication_agent_function_schema.json")
        #self.get_function_parameter_info("search_product_by_productNumber")
        # END TESTING PART

    async def classify_multi_intent(self, user_message: str) -> MultiIntentResponse:
        start = time.perf_counter()
        messages = build_multi_intent_prompt(user_message)

        intent_response = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=self.get_small_llm_model(),
            messages=messages,
            response_format=MultiIntentResponse,
        )

        elapsed = time.perf_counter() - start
        self.logger.info(f"INTENT CATEGORIZATION FINISHED IN: {elapsed:.2f} seconds")

        parsed = intent_response.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("Failed to parse multi-intent response: parsed value is None")
        return parsed
    
    async def classify_general_intent(self, user_message: str) -> PrimaryGoals:
        start = time.perf_counter()
        messages = build_primary_intent_prompt(user_message)

        intent_response = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=self.get_small_llm_model(),
            messages=messages,
            response_format=PrimaryGoals,
        )

        elapsed = time.perf_counter() - start
        self.logger.info(f"INTENT CATEGORIZATION FINISHED IN: {elapsed:.2f} seconds")

        parsed = intent_response.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("Failed to parse multi-intent response: parsed value is None")
        return parsed
    
    
