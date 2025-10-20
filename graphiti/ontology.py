from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

# --------- Example entities ----------
class UserEntity(BaseModel):
    kind: str = Field(default="User")
    display_name: str = Field(description="Human-readable user name")
    user_id: Optional[str] = None
    locale: Optional[str] = None

class ProductEntity(BaseModel):
    kind: str = Field(default="Product")
    product_id: str
    product_number: Optional[str] = None
    display_name: Optional[str] = Field(default=None, description="Product title or name")
    brand: Optional[str] = None
    price: Optional[float] = None

class IntentEntity(BaseModel):
    kind: str = Field(default="Intent")
    label: str  # e.g., "buy", "compare", "find_variant"

# --------- Example edges ----------
class WantsEdge(BaseModel):
    name: str = Field(default="WANTS")
    confidence: float = 0.8

class MentionsEdge(BaseModel):
    name: str = Field(default="MENTIONS")
    note: Optional[str] = None

class LastViewedProductEdge(BaseModel):
    name: str = Field(default="LAST_VIEWED_PRODUCT")
    timestamp: Optional[str] = None  # ISO 8601 format

class HasInCartEdge(BaseModel):
    name: str = Field(default="HAS_IN_CART")
    quantity: Optional[int] = None

class VariantOfEdge(BaseModel):
    name: str = Field(default="VARIANT_OF")
    variant_type: Optional[str] = None  # e.g., "color", "size"

# Graphiti expects mapping dicts; you can pass these in add_episode* calls.
ENTITY_TYPES = {
    "User": UserEntity,
    "Product": ProductEntity,
    "Intent": IntentEntity,
}

EDGE_TYPES = {
    "WANTS": WantsEdge,
    "MENTIONS": MentionsEdge,
}

# Optionally constrain which entity pairs can connect with specific edges:
EDGE_TYPE_MAP = {
    ("User", "Product"): ["WANTS", "MENTIONS"],
    ("User", "Intent"): ["MENTIONS"],
}
