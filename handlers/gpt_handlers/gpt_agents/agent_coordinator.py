from __future__ import annotations
from typing import Dict, Any, Optional, List
import logging
import json
from graphiti.graphiti_memory import GraphitiMemory
from handlers.gpt_handlers.gpt_agents.planning_agent import PlanningAgent
from handlers.gpt_handlers.gpt_agents.search_agent import SearchAgent
from handlers.gpt_handlers.gpt_agents.communication_agent import CommunicationAgent
from handlers.gpt_handlers.gpt_agents.cart_agent import CartAgent
from handlers.gpt_handlers.gpt_agents.order_agent import OrderAgent
from handlers.gpt_handlers.gpt_agents.intent_agent import IntentAgent
from handlers.shopware_handlers.shopware_utils import SimpleHeaderInfo, ChatResponse
from handlers.multi_intent import MultiIntentResponse

class AgentCoordinator:
    
    INTENT_TO_AGENT = {
        "search": SearchAgent(),
        "cart": CartAgent(),
        "order": OrderAgent(),
        "communication": CommunicationAgent()
    }
    
    def __init__(self):
        self.logger = logging.getLogger("shopware_ai.coordinator")

    def map_intent_to_agent(self, intent: str) -> PlanningAgent:
        if intent in ("greeting", "unclear"):
            intent = "communication"

        agent = self.INTENT_TO_AGENT.get(intent, self.INTENT_TO_AGENT["communication"])
        self.logger.info("Intent '%s' mapped to agent '%s'", intent, agent)
        return agent
    
    async def process_chat_request(
        self, 
        user_message: str, 
        context_outline: Optional[GraphitiMemory] = None
    ) -> ChatResponse:

        # Stage 1: Intent Classification
        intent_agent = IntentAgent()
        intent_data = await intent_agent.classify_multi_intent(user_message)
        
        # Log intent analysis
        self.logger.info("Intent Analysis:")
        self.logger.info("  → Primary intent: %s", intent_data.primary_intent)
        self.logger.info("  → Multi-intent: %s", intent_data.is_multi_intent)
        self.logger.info("  → Intent sequence: %s", intent_data.intent_sequence)
        self.logger.info("  → Message parts: %s", intent_data.message_parts)
        
        if intent_data.primary_intent in ["greeting", "unclear"]:
            return await self.handle_non_shopping_intent(intent_data, user_message)
        
        return await self.process_intent_sequences(intent_data, user_message)
                
        
    async def handle_non_shopping_intent(self, intent_data: MultiIntentResponse, user_message: str) -> Dict[str, Any]:

        seed = {
            "intent_type": intent_data.primary_intent,
            "context": {
                "message": user_message,
                "is_greeting": intent_data.primary_intent == "greeting",
                "is_unclear": intent_data.primary_intent == "unclear"
            },
            "cue": f"Generate a contextual response for {intent_data.primary_intent} intent, acknowledging the user but redirecting to shopping assistance"
        }
        
        comm_agent = self.map_intent_to_agent("communication")
        specialized_plan = await comm_agent.plan_and_execute(seed, user_message, self.header_info.languageId)

        response_message = "I can only help with shopping-related requests."
        if "response_text" in specialized_plan:
            response_message = specialized_plan["response_text"]
        elif "steps" in specialized_plan and specialized_plan["steps"]:
            step = specialized_plan["steps"][0]
            response_message = step.get("parameters", {}).get("message", response_message)

        return {
            "message": response_message,
            "plan": specialized_plan,
            "status": "non_shopping_request",
            "agent": "communication",
            "is_shopping_related": False,
            "intent_data": intent_data.__dict__,
        }
            
    async def process_intent_sequences(self, intent_data: MultiIntentResponse, user_message: str) -> Dict[str, Any]:

        sequence_results = []
        context_data = {}
        
        self.logger.info("Processing multi-intent sequence with %d steps", len(intent_data.intent_sequence))
        
        for i, intent in enumerate(intent_data.intent_sequence):

            message_part = intent_data.message_parts[i] if i < len(intent_data.message_parts) else user_message
            
            specialized_agent = self.map_intent_to_agent(intent)
            
            self.logger.info("Step %d: Processing intent '%s'", i+1, intent)
            self.logger.info("  → Message part: '%s'", message_part[:50])
            self.logger.info("  → Context data passed to agent: %s", json.dumps(context_data, default=str))
            
            try:
                specialized_plan = await specialized_agent.plan_and_execute(
                    seed=context_data,
                    customerMessage=message_part,
                    language_id=self.header_info.languageId
                )
                
                self.logger.info("  → SPECIALIZED PLAN for intent '%s': %s", intent, json.dumps(specialized_plan, default=str))
                step_result = {
                    "step": i + 1,
                    "intent": intent,
                    "message_part": message_part,
                    "plan": specialized_plan,
                    "status": "success"
                }
                
                sequence_results.append(step_result)
                
                # Update context for next step (extract useful data from this step's results)
                if "steps" in specialized_plan and specialized_plan["steps"]:
                    context_data[f"step_{i+1}_results"] = specialized_plan["steps"]
                
            except Exception as e:
                self.logger.error("Multi-intent step %d failed: %s", i+1, str(e))
                step_result = {
                    "step": i + 1,
                    "intent": intent,
                    "message_part": message_part,
                    "error": str(e),
                    "status": "error"
                }
                sequence_results.append(step_result)
                # Continue with remaining steps even if one fails
        
        return {
            "status": "multi_intent_complete",
            "intent_data": intent_data.__dict__,
            "sequence_results": sequence_results,
            "is_shopping_related": True,
            "total_steps": len(intent_data.intent_sequence)
        }
    
    def set_header_info(self, header_info: SimpleHeaderInfo):
        self.header_info = header_info
