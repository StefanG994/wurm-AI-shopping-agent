from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional

# --------- Example entities ----------
class UserMessageEntity(BaseModel):
    kind: str = Field(default="UserMessage")
    message_id: str
    content: str
    timestamp: Optional[str] = None  # ISO 8601 format

class UserEntity(BaseModel):
    kind: str = Field(default="User")
    display_name: str = Field(description="Human-readable user name")
    user_id: Optional[str] = None
    user_uuid: Optional[str] = None
    locale: Optional[str] = None

class ProductEntity(BaseModel):
    kind: str = Field(default="Product")
    product_id: str
    product_number: Optional[str] = None
    display_name: Optional[str] = Field(default=None, description="Product title or name")
    brand: Optional[str] = None
    price: Optional[float] = None
    min_order_quantity: Optional[int] = None
    currency: Optional[str] = None

class BrandEntity(BaseModel):
    kind: str = Field(default="Brand")
    label: str = Field(description="Brand label")
    brand_id: Optional[str] = None

class ProductConceptEntity(BaseModel):
    kind: str = Field(default="ProductConcept")
    label: str = Field(description="Concept label for a requested product (e.g., 'earbuds')")
    category: Optional[str] = None

class ProductPropertyEntity(BaseModel):
    kind: str = Field(default="ProductProperty")
    property_name: str = Field(description="Property type (e.g., 'color')")
    property_value: str = Field(description="Property value (e.g., 'yellow')")

class IntentEntity(BaseModel):
    kind: str = Field(default="Intent")
    label: Literal[
        'PRODUCTS',
        'CART',
        'ORDERS',
        'COMMUNICATION',
        'UNKNOWN',
    ]

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

class HasIntentEdge(BaseModel):
    name: str = Field(default="HAS_INTENT")
    confidence: float = 0.9

class HasBrandEdge(BaseModel):
    name: str = Field(default="HAS_BRAND")
    rationale: Optional[str] = None

class HasPropertyEdge(BaseModel):
    name: str = Field(default="HAS_PROPERTY")
    rationale: Optional[str] = None

class CartEntity(BaseModel):
    kind: str = Field(default="Cart")
    cart_id: str
    user_id: Optional[str] = None
    user_uuid: Optional[str] = None

class WantsToBuyEdge(BaseModel):
    name: str = Field(default="WANTS_TO_BUY")
    product_id: str
    quantity: int

class PurchasedEdge(BaseModel):
    name: str = Field(default="PURCHASED")
    product_id: str
    quantity: int
    purchase_date: Optional[str] = None  # ISO 8601 format

class ProductPropertyEdge(BaseModel):
    name: str = Field(default="PRODUCT_PROPERTY")
    property_name: str
    property_value: str


# Dodati nod ChatRoom entity i relaciju ChatHistory

# Graphiti expects mapping dicts; you can pass these in add_episode* calls.
ENTITY_TYPES = {
    "User": UserEntity,
    "UserMessage": UserMessageEntity,
    "Product": ProductEntity,
    "Brand": BrandEntity,
    "ProductConcept": ProductConceptEntity,
    "ProductProperty": ProductPropertyEntity,
    "Intent": IntentEntity,
    "Cart": CartEntity,
}

EDGE_TYPES = {
    "WANTS": WantsEdge,
    "MENTIONS": MentionsEdge,
    "LAST_VIEWED_PRODUCT": LastViewedProductEdge,
    "HAS_IN_CART": HasInCartEdge,
    "VARIANT_OF": VariantOfEdge,
    "HAS_INTENT": HasIntentEdge,
    "WANTS_TO_BUY": WantsToBuyEdge,
    "PURCHASED": PurchasedEdge,
    "PRODUCT_PROPERTY": ProductPropertyEdge,
    "HAS_BRAND": HasBrandEdge,
    "HAS_PROPERTY": HasPropertyEdge,
}

# Optionally constrain which entity pairs can connect with specific edges:
EDGE_TYPE_MAP = {
    ("User", "Product"): ["WANTS", "MENTIONS", "LAST_VIEWED_PRODUCT", "WANTS_TO_BUY", "PURCHASED"],
    ("User", "ProductConcept"): ["WANTS", "MENTIONS"],
    ("User", "Intent"): ["MENTIONS", "HAS_INTENT"],
    ("ProductConcept", "Brand"): ["HAS_BRAND"],
    ("ProductConcept", "ProductProperty"): ["HAS_PROPERTY"],
    ("Cart", "Product"): ["HAS_IN_CART"],
    ("Product", "Product"): ["VARIANT_OF", "PRODUCT_PROPERTY"],
}
