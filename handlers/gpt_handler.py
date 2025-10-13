import os
import json
from typing import Tuple, Dict, Any, List, Optional
from dotenv import load_dotenv
import logging
from .prompts_translated.get_translated_prompt import get_translated_prompt
from pydantic import BaseModel

# OpenAI SDK v1
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_LARGE = os.getenv("OPENAI_MODEL_LARGE", "gpt-5")
OPENAI_MODEL_SMALL = os.getenv("OPENAI_MODEL_SMALL", "gpt-5-nano")

logger = logging.getLogger("shopware_ai.gpt")

FUNCTION_SCHEMA = [
    # ---------- COMMUNICATION ----------
    {
        "name": "communication",
        "description": "Ask the user for missing information. No Shopware API call.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Human-readable question or clarification for the user."},
                "missing": {"type": "array", "items": {"type": "string"}, "description": "List of missing fields (e.g., ['quantity'])."},
                "context": {"type": "object", "description": "Optional context to display (e.g., suggested products)."}
            },
            "required": ["message"]
        }
    },
    # ---------- SEARCH & LISTINGS ----------
    {
        "name": "search_product_by_productNumber",
        "description": "Search products by product number via /store-api/product with optional listing criteria and shorthand filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "productNumber": {"type": "string", "description": "Product number to search for"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, 'description':'Number of items per result page'},
                "quantity":{"type" : "integer", "description": "Total number of items found"},
                "page": {"type": "integer", "minimum": 1},
                "min_price": {"type": "number"},
                "max_price": {"type": "number"}
            },
            "required": ["productNumber"]
        }
    },
    {
        "name": "search_products",
        "description": "Search products via /store-api/search with optional listing criteria and shorthand filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Free-text query (e.g. 'wireless mouse')"},
                "order": {"type": "string", "description": "Sorting key: score | name-asc | name-desc | price-asc | price-desc | topseller"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, 'description':'Number of items per result page'},
                "quantity":{"type" : "integer", "description": "Total number of items found"},
                "page": {"type": "integer", "minimum": 1},
                "min_price": {"type": "number"},
                "max_price": {"type": "number"},
                "manufacturer": {"type": "string", "description": "Manufacturers (IDs separated by |)"},
                "properties": {"type": "string", "description": "Property IDs separated by |"},
                "shipping_free": {"type": "boolean"},
                "rating": {"type": "integer", "minimum": 0, "maximum": 5},
                "filter": {"type": "array", "items": {"type": "object"}, "description": "Advanced search criteria array (range/equals/etc.)"},
                "includes": {"type": "object", "description": "Field projection map keyed by apiAlias"},
                "associations": {"type": "object", "description": "Associations to hydrate (e.g. categories)"}
            },
            "required": ["search"]
        }
    },
    {
        "name": "list_products",
        "description": "Entity search on /store-api/product using a raw criteria object.",
        "parameters": {
            "type": "object",
            "properties": {
                "criteria": {"type": "object", "description": "Search Criteria object: page, limit, filter, sort, aggregations, etc."},
                "includes": {"type": "object", "description": "Field projection map keyed by apiAlias"}
            }
        }
    },
    {
        "name": "product_listing_by_category",
        "description": "Fetch listing for a specific category via /store-api/product-listing/{categoryId}.",
        "parameters": {
            "type": "object",
            "properties": {
                "category_id": {"type": "string", "description": "Category ID (32 hex)"},
                "order": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "page": {"type": "integer", "minimum": 1},
                "filter": {"type": "array", "items": {"type": "object"}},
                "includes": {"type": "object"},
                "associations": {"type": "object"}
            },
            "required": ["category_id"]
        }
    },
    {
        "name": "search_suggest",
        "description": "Search preview suggestions via /store-api/search-suggest (lightweight listing, no aggregations).",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Free-text query"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "page": {"type": "integer", "minimum": 1},
                "filter": {"type": "array", "items": {"type": "object"}},
                "includes": {"type": "object"}
            },
            "required": ["search"]
        }
    },

    # ---------- PRODUCT DETAILS / VARIANTS / CROSS-SELL ----------
    {
        "name": "get_product",
        "description": "Fetch a single product by ID via /store-api/product/{productId}.",
        "parameters": {
            "type": "object",
            "properties": {
                "productId": {"type": "string", "description": "Product ID (32 hex)"},
                "includes": {"type": "object"},
                "associations": {"type": "object"}
            },
            "required": ["productId"]
        }
    },
    {
        "name": "product_cross_selling",
        "description": "Fetch cross-selling groups for a product via /store-api/product/{productId}/cross-selling.",
        "parameters": {
            "type": "object",
            "properties": {
                "productId": {"type": "string", "description": "Product ID (32 hex)"},
                "includes": {"type": "object"}
            },
            "required": ["productId"]
        }
    },
    {
        "name": "find_variant",
        "description": "Find the best matching variant for a product via /store-api/product/{productId}/find-variant.",
        "parameters": {
            "type": "object",
            "properties": {
                "productId": {"type": "string", "description": "Parent product ID (32 hex)"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Option IDs (e.g., selected color/size option IDs)"
                },
                "switchedGroup": {"type": "string", "description": "Option group ID that was changed"},
                "includes": {"type": "object"}
            },
            "required": ["productId", "options"]
        }
    },

    # ---------- CART ----------
    {
        "name": "add_to_cart",
        "description": "Add one or more products to the cart by product numbers or IDs.",
        "parameters": {
            "type": "object",
            "properties": {
            "items": {
                "type": "array",
                "items": {
                "type": "object",
                "properties": {
                    "productId": { "type": "string" },
                    "productNumber": { "type": "string" },
                    "quantity": { "type": "integer", "minimum": 1, "default": 1 }
                },
                "anyOf": [
                    { "required": ["productId", "quantity"] },
                    { "required": ["productNumber", "quantity"] }
                ]
                }
            }
            },
            "required": ["items"]
        }
    },
    {
        "name": "update_cart_items",
        "description": "Update quantity/referencedId for existing line items via /store-api/checkout/cart/line-item (PATCH).",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Line item ID in cart"},
                            "quantity": {"type": "integer", "minimum": 0},
                            "referencedId": {"type": "string"}
                        },
                        "required": ["id"]
                    }
                }
            },
            "required": ["items"]
        }
    },
    {
        "name": "remove_from_cart",
        "description": "Remove one or more line items via /store-api/checkout/cart/line-item (DELETE).",
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["ids"]
        }
    },
    {
        "name": "delete_cart",
        "description": "Delete the entire cart via /store-api/checkout/cart (DELETE). Use only when user clearly requests it.",
        "parameters": {"type": "object", "properties": {}}
    },
     # ---------- ORDER ----------
    {
        "name": "fetch_orders_list",
        "description": "Fetches a list of orders via /store-api/checkout/order (POST).",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {"type": "integer", "minimum": 1},                
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, 'description':'Number of items per result page'},
                "filter": {"type": "array", "items": {"type": "object"}, "description": "Advanced search criteria array (range/equals/etc.)"},
                "associations": {"type": "object"},                
                "sort": {"type": "array", "items": {"type": "object"}, "description": "Sorting in the search result either in ASC or DESC order"},
                "message": {"type": "string", "description": "Short description what you are doing BUT in a language which user was using."}
            },
        }
    }
]


def _client():
    if OpenAI is None:
        raise RuntimeError("Install openai>=1.0.0 to use the new SDK (pip install openai)")
    return OpenAI(api_key=OPENAI_API_KEY)

def _build_messages_with_system(system_key: str,
                                customerMessage: str,
                                *,
                                language_id: Optional[str] = None,
                                variables: Optional[Dict[str, Any]] = None,
                                extra_sections: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Build messages for any agent using:
      - translated system prompt (by system_key)
      - Context from episodes in graph
      - optional extra sections (e.g., SEED)
    """
    system_prompt = get_translated_prompt(system_key, language_id=language_id, variables=variables or {})

    msgs: List[Dict[str, str]] = [
        {"role": "system", "content": "In the output JSON, 'steps' cannot be an empty array"},
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": f"USER GOAL:\n{customerMessage}".strip()},
        {"role": "user", "content": "CONTEXT_OUTLINE:\n" + "context outline goes here"},
    ]
    # Optional extra sections inserted before the strict-output instruction
    if extra_sections:
        for title, content in extra_sections.items():
            msgs.append({"role": "user", "content": f"{title}:\n{content}"})
    # (Optional) log the outline for debugging
    # logging.getLogger("shopware_ai.middleware").info("CONTEXT_OUTLINE:\n%s", outline)
    return msgs

################################################
# BASE MODELS DEFINING THE STRUCTURE OF THE RESPONSES
################################################
class TestGPTResponse(BaseModel):
    action: str
    message: str
    data: Optional[Dict[str, Any]] = None




#################################################
# GPT HANDLER
#################################################

async def test_gpt(customerMessage: str) -> Dict[str, Any]:
    """
    Simple test function to verify GPT integration.
    """
    client = _client()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": customerMessage}
    ]
    response = client.beta.chat.completions.parse(
        model=OPENAI_MODEL_SMALL,
        messages=messages,
        response_format=TestGPTResponse,
    )
    try:
        content = response.choices[0].message.content
        parsed = json.loads(content)
        result = TestGPTResponse(**parsed) #nepotreban korak? vrati parsed direktno?
        return result.dict()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse GPT response: %s", e)
        raise