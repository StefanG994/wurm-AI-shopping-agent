from enum import Enum
from typing import Dict, List, Literal

from openai import BaseModel

class MessageCategory(Enum):

    PRODUCT_SEARCH = ("product_search", "User is searching for products, product variant or product category.")
    ADD_TO_CART = ("add_to_cart", "User wants to add items to cart")
    VIEW_CART = ("view_cart", "User wants to view their shopping cart")
    REMOVE_FROM_CART = ("remove_from_cart", "User wants to remove items from cart")
    VIEW_ORDER = ("view_order", "User wants to look at shipping status of his last order")
    GREETING = ("greeting", "User is greeting, saying hello or goodbye")
    UNCLEAR = ("unclear", "User message is unclear or ambiguous")    

    @property
    def description(self):
        return self.value[1]

    
def build_multi_intent_prompt(user_message: str, concise: bool = False) -> List[Dict[str, str]]:
    categories_text = []
    for category in MessageCategory:
        categories_text.append(f"- {category.value}: {category.description}")
    categories_list = "\n".join(categories_text)

    if concise:
        system_content = f"""Analyze the user's message for multiple intentions.\n\nCategories:\n{categories_list}\n\nInstructions:\n- Identify the primary intent (most important)\n- List all detected intents in logical order (intent_sequence)\n- Set is_multi_intent to true if more than one intent is found\n\nExample ("find me red shoes and add them to cart"):\nprimary_intent: "product_search"\nintent_sequence: ["product_search", "add_to_cart"]\nis_multi_intent: true"""
    else:
        system_content = f"""You are an AI assistant that analyzes user messages for multiple intentions.\n\nAvailable categories:\n{categories_list}\n\nAnalyze this user message and identify ALL intentions present, then determine the logical order of execution.\n\nInstructions:\n1. Identify the PRIMARY intention (most important)\n2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions\n3. Provide a boolean flag "is_multi_intent" indicating if multiple intentions were detected or not\n\nExample for "find me red shoes and add them to cart":\n- primary_intent: "product_search"\n- intent_sequence: ["product_search", "add_to_cart"]\n- is_multi_intent: true"""

    prompt = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message}
    ]
    return prompt

class MultiIntentResponse(BaseModel):

    AllowedIntent = Literal[
        'product_search',
        'add_to_cart',
        'view_cart',
        'remove_from_cart',
        'view_order',
        'greeting',
        'unclear',
    ]

    primary_intent: AllowedIntent
    intent_sequence: List[AllowedIntent]
    is_multi_intent: bool = False

