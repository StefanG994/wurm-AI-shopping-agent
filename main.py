import os, sys
from typing import Optional, List, Dict, Any, Tuple, Union
import logging
from logging.handlers import RotatingFileHandler
import json
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from handlers.gpt_handler import classify_multi_intent
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

# ----------------------------------------
# FastAPI app with enhanced CORS, Helmet-like and Rate Limiting security
# ----------------------------------------
from middleware_security.cors_config import setup_cors
from middleware_security.security import setup_security_headers

app = FastAPI(
    title=os.getenv("API_TITLE", "WURM Shopware AI Agent Middleware"), 
    version=os.getenv("API_VERSION", "0.3.0"),
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None,
)

# Setup security middleware (order matters!)
setup_security_headers(app)
setup_cors(app)

# Include security test routes (only in development)
if os.getenv("ENVIRONMENT", "development") == "development":
    from middleware_security.test_routes import router as security_test_router
    app.include_router(security_test_router)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded  
 
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
# Routes
# ------------------------------
@app.get("/health")
async def health():
    logger = logging.getLogger("shopware_ai.middleware")
    logger.info("Health check")
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("200/minute")
async def chat(req: ChatRequest, request: Request, response: Response):
    logging.getLogger("shopware_ai.middleware").info("REQUEST: %s", req)
    response = await classify_multi_intent(req.customerMessage)
    logging.getLogger("shopware_ai.middleware").info("Primary intent: %s", response.primary_intent)
    logging.getLogger("shopware_ai.middleware").info("Intent Steps: %s", response.intent_sequence)
    return ChatResponse(
        ok=True,
        action="response",
        message="This is a placeholder response.",
        contextToken=req.contextToken or "new-context-token",
        data={"info": "More data can be added here."}
    )

# ------------------------------
# Dev server (optional)
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)