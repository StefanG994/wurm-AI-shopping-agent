import os, sys
from typing import Optional, List, Dict, Any, Tuple, Union
import logging
from logging.handlers import RotatingFileHandler
import json
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import re

# ---------- Logging: rotating file + console ----------
LOG_DIR = os.getenv("LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, os.getenv("LOG_FILE", "middleware.log"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))   # 5 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

_fh = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
_fh.setFormatter(fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(fmt)

root = logging.getLogger()
root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Replace handlers to avoid duplicates on reload
root.handlers = [_fh, _sh]

# Narrow app loggers (they’ll inherit handlers above)
logging.getLogger("shopware_ai.middleware").setLevel(root.level)
logging.getLogger("shopware_ai.gpt").setLevel(root.level)
logging.getLogger("shopware_ai.shopware").setLevel(root.level)

# ------------------------------
# FastAPI app & CORS
# ------------------------------
app = FastAPI(title="WURM Shopware AI Agent Middleware", version="0.3.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Pydantic base models to define
# ------------------------------
class ChatRequest(BaseModel):
    customerMessage: str = Field(..., description="User's natural language input")
    contextToken: Optional[str] = Field(None, description="Shopware sw-context-token if already known")
    languageId: Optional[str] = Field(None, description="sw-language-id header to localize responses")
    salesChannelId: Optional[str] = Field(None, description="Sales Channel ID from the storefront")

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


# ------------------------------
# Dev server (optional)
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)