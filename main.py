import os, sys
from typing import Optional, List, Dict, Any, Tuple, Union
import logging
from logging.handlers import RotatingFileHandler
import json
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from handlers.gpt_handlers.gpt_agents.intent_agent import IntentAgent
import re
from contextlib import asynccontextmanager
from graphiti.graphiti_memory import GraphitiMemory
from graphiti.dependencies import get_mem
from graphiti.ontology import ENTITY_TYPES, EDGE_TYPES, EDGE_TYPE_MAP
from graphiti.context_builder import build_context_outline


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
from handlers.gpt_handlers.gpt_agents.intent_agent import IntentAgent
from middleware_security.cors_config import setup_cors
from middleware_security.security import setup_security_headers

# Lifespan handler (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    mem = GraphitiMemory()
    await mem.initialize(build_indices=True)
    app.state.mem = mem
    try:
        yield
    finally:
        await app.state.mem.close()

app = FastAPI(
    title=os.getenv("API_TITLE", "WURM Shopware AI Agent Middleware"), 
    version=os.getenv("API_VERSION", "0.3.0"),
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    lifespan=lifespan,
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

# ------------------------------
# Test endpoints (dev-only)
# ------------------------------
from fastapi import Depends

#Initialize GraphitiMemory knowledge graph on startup
@app.on_event("startup")
async def startup_event():
    mem = app.state.mem
    if not mem or not mem.initialized:
        raise RuntimeError("GraphitiMemory not initialized on startup")
    logging.getLogger("shopware_ai.middleware").info("GraphitiMemory initialized and ready")

@app.post("/episodes/add")
async def add_episode_dev(payload: dict, mem: GraphitiMemory = Depends(get_mem)):
    """
    Dev helper: { "name": "foo", "text": "some content", "description": "desc" }
    """
    if "json" in payload:
        await mem.add_episode_json(
            name=payload.get("name", "dev-json"),
            payload=payload["json"],
            description=payload.get("description", "dev-json"),
            entity_types=ENTITY_TYPES,
            edge_types=EDGE_TYPES,
            edge_type_map=EDGE_TYPE_MAP,
        )
    else:
        await mem.add_episode_text(
            name=payload.get("name", "dev"),
            text=payload["text"],
            description=payload.get("description", "dev"),
            entity_types=ENTITY_TYPES, 
            edge_types=EDGE_TYPES, 
            edge_type_map=EDGE_TYPE_MAP,
        )
    return {"ok": True}

@app.get("/search")
async def search_dev(q: str, mem: GraphitiMemory = Depends(get_mem)):
    edges = await mem.search_edges(q, limit=12)
    nodes = await mem.search_nodes_rrf(q, limit=12)
    return {
        "edges": [getattr(e, "fact", None) for e in getattr(edges, "edges", [])],
        "nodes": [{"uuid": n.uuid, "name": getattr(n, "name", None)} for n in nodes],
    }

# ------------------------------
# Modify /chat to ingest & use context
# ------------------------------
from handlers.gpt_handler import _client, TestGPTResponse

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("200/minute")
async def chat(
    request: Request,
    response: Response,
    mem: GraphitiMemory = Depends(get_mem),
):
    # create chat_request from request body
    body = await request.json()
    chat_request = ChatRequest(**body)
    logging.getLogger("shopware_ai.middleware").info("REQUEST: %s", request)  # Remove in production

    # 1. Format the input request. If voice, convert to text first (TODO). If text, validate, clean and use directly.

    # 2. Use GraphitiMemory to ingest the user message as an episode (grows long-term memory)
    await mem.add_episode_text(
        name=f"user:{chat_request.languageId or 'default'}",
        text=chat_request.customerMessage,
        description="user_message",
        entity_types=ENTITY_TYPES, 
        edge_types=EDGE_TYPES, 
        edge_type_map=EDGE_TYPE_MAP,
    )

    # 3. Clarify user intent using Multi-Intent Classifier (from multi_intent.py)
    intent_agent = IntentAgent()
    response = await intent_agent.classify_multi_intent(chat_request.customerMessage)
    logging.getLogger("shopware_ai.middleware").info("Primary intent: %s", response.primary_intent)
    logging.getLogger("shopware_ai.middleware").info("Intent Steps: %s", response.intent_sequence)


    # 4. Choose the starting node and Build contextual outline from the graph (relevant products, cart items, user preferences, etc.)

    outline = await build_context_outline(mem, chat_request.customerMessage, limit=12)

    return ChatResponse(
        ok=True,
        action="response",
        message=f"(demo) Context outline:\n{outline}",
        contextToken=chat_request.contextToken or "new-context-token",
        data={"note": "Replace this with GPT tool-use logic that calls Shopware APIs."}
    )
    

# ------------------------------
# Dev server (optional)
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
