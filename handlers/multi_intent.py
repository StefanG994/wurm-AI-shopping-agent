import json
from pathlib import Path
from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict

FUNCTION_SCHEMA_FILES = [
    "cart_agent_function_schema.json",
    "order_agent_function_schema.json",
    "search_agent_function_schema.json",
    "communication_agent_function_schema.json",
]
SCHEMA_DIR = Path(__file__).parent / "gpt_handlers" / "gpt_agents" / "agent_function_schemas"


def _load_function_descriptions(schema_dir: Path, schema_files: List[str]) -> Dict[str, str]:
    """Load the available tool/function descriptions so the prompt stays in sync with the schemas."""
    descriptions: Dict[str, str] = {}
    for schema_name in schema_files:
        schema_path = schema_dir / schema_name
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        try:
            with schema_path.open("r", encoding="utf-8") as schema_file:
                entries = json.load(schema_file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Unable to parse schema file: {schema_path}") from exc

        if isinstance(entries, dict):
            entries = entries.get("functions", [])
        if not isinstance(entries, list):
            continue

        for entry in entries:
            name = entry.get("name")
            description = entry.get("description")
            if name and description:
                descriptions[name] = description.strip()

    return descriptions


Name_to_description: Dict[str, str] = _load_function_descriptions(SCHEMA_DIR, FUNCTION_SCHEMA_FILES)

if not Name_to_description:
    raise ValueError("No function descriptions could be loaded from schema files.")

categories_list = "\n".join(
    f"- {name}: {description}"
    for name, description in Name_to_description.items()
)

def build_multi_intent_prompt(user_message: str):
    system_content = f"""
    You are an AI shopping assistant that analyzes customer messages for multiple intentions.\n\n
    Available actions with descriptions:\n{categories_list}\n\n
    Analyze this user message and identify ALL intentions present, then determine the logical order of execution.\n\n
    Instructions:\n
    1. Identify the PRIMARY intention (most important), i.e. identify what customer's end GOAL is.\n
    2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions\n
    3. Provide a GOAL intention separately
    """

    prompt = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message}
    ]
    return prompt
goals_list = {
        'PRODUCTS':'Searching products by product number, description, category or listing products, finding variants, cross selling etc.',
        'CART':'Managing the shopping cart, including adding, updating, and removing items.',
        'ORDERS':'Handling customer orders, including tracking and managing order status.',
        'COMMUNICATION':'Facilitating communication between the customer and support agents.',
        'UNKNOWN':'Handling unrecognized or ambiguous intents.'
        }
def build_primary_intent_prompt(user_message: str):
    system_content = f"""
    You are an AI shopping assistant that analyzes customer messages for multiple intentions.\n\n
    Available actions with descriptions:\n{goals_list}\n\n
    Analyze this user message and identify ALL intentions present, then determine the logical order of execution.\n\n
    Instructions:\n
    1. Identify the PRIMARY intention (most important), i.e. identify what customer's end GOAL is.\n
    2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions\n
    3. Provide a GOAL intention separately
    """

    prompt = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message}
    ]
    return prompt

class MultiIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_list_order: List[Literal[
        'add_to_cart',
        'update_cart_items',
        'remove_from_cart',
        'delete_cart',
        'communication',
        'fetch_orders_list',
        'search_product_by_productNumber',
        'search_products_by_description',
        'list_products',
        'product_listing_by_category',
        'search_suggest',
        'get_product',
        'product_cross_selling',
        'find_variant',
    ]]
    # missing_properties: List[str] = []
    goal: str
    message: str

class PrimaryGoals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_list_order: List[Literal[
        'PRODUCTS',
        'CART',
        'ORDERS',
        'COMMUNICATION',
        'UNKNOWN',
    ]]
    # missing_properties: List[str] = []
    goal: str
    message: str