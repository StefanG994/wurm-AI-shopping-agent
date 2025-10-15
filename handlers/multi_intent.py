from enum import Enum

class MessageCategory(Enum):
    PRODUCT_SEARCH = ("product_search", "User is searching for specific products")
    ADD_TO_CART = ("add_to_cart", "User wants to add items to cart")
    VIEW_CART = ("view_cart", "User wants to view their shopping cart")
    REMOVE_FROM_CART = ("remove_from_cart", "User wants to remove items from cart")
    GREETING = ("greeting", "User is greeting, saying hello or goodbye")
    UNCLEAR = ("unclear", "User message is unclear or ambiguous")    

    
def build_multi_intent_prompt(user_message: str) -> str:
    categories_text = []
    for category in MessageCategory:
        categories_text.append(f"- {category.value}: {category.description}")
    
    categories_list = "\n".join(categories_text)
    
    prompt = f"""You are an AI assistant that analyzes user messages for multiple intentions.

        Available categories:
        {categories_list}

        Analyze this message and identify ALL intentions present, then determine the logical order of execution.

        User message: "{user_message}"

        Instructions:
        1. Identify the PRIMARY intention (most important)
        2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions
        3. Provide a boolean flag "is_multi_intent" indicating if multiple intentions were detected or not

        Example for "find me red shoes and add them to cart":
        - primary_intent: "product_search"
        - intent_sequence: ["product_search", "add_to_cart"]
        - is_multi_intent: true"""

    return prompt