from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FUNCTION_SCHEMA_FILES = [
    "cart_agent_function_schema.json",
    "order_agent_function_schema.json",
    "search_agent_function_schema.json",
    "communication_agent_function_schema.json",
]
SCHEMA_DIR = Path(__file__).parent / "gpt_handlers" / "gpt_agents" / "agent_function_schemas"


def _load_function_metadata(schema_dir: Path, schema_files: List[str]) -> Dict[str, Dict[str, Any]]:
    """Load descriptions plus parameter metadata for every available tool."""
    metadata: Dict[str, Dict[str, Any]] = {}
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
            parameters: Dict[str, Any] = entry.get("parameters", {}) if isinstance(entry, dict) else {}
            if name and description:
                metadata[name] = {
                    "description": description.strip(),
                    "required": list(parameters.get("required", []) or []),
                    "properties": parameters.get("properties", {}) or {},
                }

    return metadata


FUNCTION_SCHEMAS: Dict[str, Dict[str, Any]] = _load_function_metadata(SCHEMA_DIR, FUNCTION_SCHEMA_FILES)

if not FUNCTION_SCHEMAS:
    raise ValueError("No function descriptions could be loaded from schema files.")

Name_to_description: Dict[str, str] = {
    name: meta["description"] for name, meta in FUNCTION_SCHEMAS.items()
}

categories_list = "\n".join(
    f"- {name}: {description}"
    for name, description in Name_to_description.items()
)

function_catalog = "\n".join(
    f"- {name}: required={meta.get('required') or []}, optional={[k for k in meta.get('properties', {}).keys() if k not in (meta.get('required') or [])]}"
    for name, meta in FUNCTION_SCHEMAS.items()
)

def build_multi_intent_prompt(user_message: str):
    system_content = f"""
    You are an AI shopping assistant that analyzes customer messages for multiple intentions.\n\n
    Available actions with descriptions:\n{categories_list}\n\n
    Function catalog for parameter extraction:\n{function_catalog}\n\n
    Analyze this user message and identify ALL intentions present, then determine the logical order of execution. For each intention, also extract a structured payload ready for the corresponding Shopware API call.\n\n
    Instructions:\n
    1. Identify the PRIMARY intention (most important), i.e. identify what customer's end GOAL is.\n
    2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions\n
    3. Provide a GOAL intention separately\n
    4. For each intention, output an object in parsed_intents with: agent (PRODUCTS/CART/ORDERS/COMMUNICATION/UNKNOWN), function (choose the concrete API/tool name), parameters (dict with extracted values), missing (list of required fields still unknown), and summary (short rationale). Use the function catalog to decide which parameters belong to each function.
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
    Available goal categories:\n{goals_list}\n\n
    Function catalog for parameter extraction:\n{function_catalog}\n\n
    Analyze this user message and identify ALL intentions present, then determine the logical order of execution. Also decompose the request into actionable parameters that align with the provided function catalog.\n\n
    Instructions:\n
    1. Identify the PRIMARY intention (most important), i.e. identify what customer's end GOAL is.\n
    2. List ALL intentions found in the message (including the primary one) and sort them in the logical sequence of actions\n
    3. Provide a GOAL intention separately\n
    4. Populate parsed_intents with structured elements containing: agent (goal bucket), function (concrete API/tool), parameters (dict), missing (list of still-required params), and summary (why this function is needed). Use only parameters defined in the catalog.
    """

    prompt = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message}
    ]
    return prompt


class ParsedIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal[
        'PRODUCTS',
        'CART',
        'ORDERS',
        'COMMUNICATION',
        'UNKNOWN',
    ]
    function: str = Field(..., description="Concrete Shopware function/tool to call")
    parameters: IntentParameters
    missing: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    summary: Optional[str] = None

class IntentParameters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    search: str | None = None
    productNumber: int | None = None
    # add every field you expect

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
    parsed_intents: List[ParsedIntent] = Field(default_factory=list)
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
    parsed_intents: List[ParsedIntent] = Field(default_factory=list)
    goal: str
    message: str
