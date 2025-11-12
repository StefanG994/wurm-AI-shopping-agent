import logging
import re
from typing import Any, Dict, Optional, Union
import httpx
from pydantic import BaseModel, Field, field_validator

def _make_timeout(t: Union[httpx.Timeout, int, float, str, None]) -> httpx.Timeout:
    """Coerce various inputs into a valid httpx.Timeout."""
    if isinstance(t, httpx.Timeout):
        return t
    if t is None:
        return httpx.Timeout(60.0)
    if isinstance(t, (int, float)):
        return httpx.Timeout(float(t))
    if isinstance(t, str):
        # Accept "10" as seconds, reject "10s" gracefully
        try:
            return httpx.Timeout(float(t))
        except ValueError:
            return httpx.Timeout(60.0)
    return httpx.Timeout(60.0)


def extract_context_token(resp: httpx.Response) -> Optional[str]:
    """Extract context token from response headers."""
    token = resp.headers.get("sw-context-token")
    if not token:
        return None
    parts = [t.strip() for t in token.split(",") if t.strip()]
    return parts[0] if parts else None


def wrap_response(resp: httpx.Response) -> Dict[str, Any]:
    """Wrap HTTP response in standard format."""
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "contextToken": extract_context_token(resp),
        "data": data,
    }

def contains_filter(field: str, value: Any) -> Dict[str, Any]:
    """Create a contains filter for Shopware API."""
    return {"type": "contains", "field": field, "value": value}


def equals_filter(field: str, value: Any) -> Dict[str, Any]:
    """Create an equals filter for Shopware API."""
    return {"type": "equals", "field": field, "value": value}


def range_filter(field: str, *, lt=None, lte=None, gt=None, gte=None) -> Dict[str, Any]:
    """Create a range filter for Shopware API."""
    params = {}
    if lt is not None:
        params["lt"] = lt
    if lte is not None:
        params["lte"] = lte
    if gt is not None:
        params["gt"] = gt
    if gte is not None:
        params["gte"] = gte
    return {"type": "range", "field": field, "parameters": params}


def sort_field(field: str, order: str = "ASC", natural_sorting: bool = False, type_: Optional[str] = None) -> Dict[str, Any]:
    """Create a sort field definition for Shopware API."""
    out = {"field": field, "order": order, "naturalSorting": natural_sorting}
    if type_ is not None:
        out["type"] = type_
    return out

# ------------------------------
# Pydantic base models to define
# ------------------------------
class ChatRequest(BaseModel):
    customerMessage: str = Field(..., description="User's natural language input")
    contextToken: Optional[str] = Field(None, description="Shopware sw-context-token if already known")
    languageId: Optional[str] = Field(None, description="sw-language-id header to localize responses")
    salesChannelId: Optional[str] = Field(None, description="Sales Channel ID from the storefront")
    customerNumber: Optional[str] = Field(None, description="Customer number if known")
    uuid: Optional[str] = Field(None, description="Unique user identifier (e.g., session ID)")

    @field_validator('customerMessage')
    @classmethod
    def validate_customer_message(cls, v):
        try:
            if not isinstance(v, str):
                raise ValueError('Customer message must be a string')
            
            cleaned_message = v.strip()
            
            if not cleaned_message:
                raise ValueError('Customer message cannot be empty or contain only whitespace')
            
            if len(cleaned_message) < 1:
                raise ValueError('Customer message is too short')
            
            max_length = 2000
            if len(cleaned_message) > max_length:
                raise ValueError(f'Customer message is too long (max {max_length} characters, got {len(cleaned_message)})')
            
            # Reject messages that are only special characters or numbers
            if re.match(r'^[^a-zA-Z]*$', cleaned_message) and len(cleaned_message) > 50:
                raise ValueError('Customer message appears to contain only special characters or numbers')
            
            return cleaned_message
        except ValueError as e:
            logging.getLogger("shopware_ai.middleware").error(e)
            
class WidgetProduct(BaseModel):
    referenceId: Union[str, float]
    name: Optional[str] = None
    price: Optional[float] = None
    thumbnail: Optional[str] = None
    available: Optional[bool] = None
    stock: Optional[int] = None
    ratingAverage: Optional[float] = None
    minPurchase: Optional[int] = None
    maxPurchase: Optional[int] = None
    purchaseSteps: Optional[int] = None

class WidgetCartItem(BaseModel):
    referenceId: Union[str, float]
    label: Optional[str] = None
    productId: Optional[str] = None
    quantity: int
    unitPrice: Optional[float] = None
    totalPrice: Optional[float] = None

# Vratiti odgovor u strukturi koja odgovara Janku, ovde definisati strukture
class ChatResponse(BaseModel):
    ok: bool
    action: str
    message: str
    contextToken: Optional[str]
    data: Dict[str, Any] = {}
 
# Helper to extract headers into a simple object
class SimpleHeaderInfo():
    contextToken: Optional[str] = Field(None, description="Shopware sw-context-token if already known")
    languageId: Optional[str] = Field(None, description="sw-language-id header to localize responses")
    salesChannelId: Optional[str] = Field(None, description="Sales Channel ID from the storefront")
    userNodeUuid: Optional[str] = Field(None, description="User's node in the graph (by uuid or customerNumber). A starting node for further search and episode adding.")
    inputWasVoice: bool = Field(False, description="Indicates if the original message was voice input")
    
    def __init__(self, request: ChatRequest, user_node_uuid: Optional[str] = None, input_was_voice: bool = False):
        self.contextToken = request.contextToken
        self.languageId = request.languageId
        self.salesChannelId = request.salesChannelId
        self.userNodeUuid = user_node_uuid
        self.inputWasVoice = input_was_voice