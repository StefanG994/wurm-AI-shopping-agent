from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

class MessageCategory(Enum):

    SEARCH = ("search", "User is searching for products, product variant or product category.")
    CART = ("cart", "User wants to add items to cart, view their shopping cart, or remove items from cart")
    ORDER = ("order", "User wants to look at shipping status of his last order")
    GREETING = ("greeting", "User is greeting, saying hello or goodbye")
    UNCLEAR = ("unclear", "User message is unclear or ambiguous")    

    @property
    def description(self):
        return self.value[1]

    
def build_multi_intent_prompt(user_message: str) -> List[Dict[str, str]]:
    categories_text = []
    for category in MessageCategory:
        categories_text.append(f"- {category.value}: {category.description}")
    categories_list = "\n".join(categories_text)

    system_content = f"""You are an AI assistant that analyzes user messages for multiple intentions.\n\nAvailable categories:\n{categories_list}\n\nAnalyze this user message and identify ALL intentions present, then determine the logical order of execution.\n\nInstructions:\n1. Identify the PRIMARY intention (most important)\n2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions\n3. Extract the specific message part corresponding to each intent\n4. Provide a boolean flag "is_multi_intent" indicating if multiple intentions were detected or not\n\nExample for "find me red shoes and add them to cart":\n- primary_intent: "search"\n- intent_sequence: ["search", "cart"]\n- message_parts: ["find me red shoes", "add them to cart"]\n- is_multi_intent: true"""

    prompt = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message}
    ]
    return prompt

class MultiIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_intent: Literal[
        'search',
        'cart',
        'order',
        'greeting',
        'unclear',
    ]
    intent_sequence: List[Literal[
        'search',
        'cart',
        'order',
        'greeting',
        'unclear',
    ]]
    message_parts: List[str] = Field(
        description="Message parts corresponding to each intent in intent_sequence",
        default_factory=list
    )
    is_multi_intent: bool = False
    



