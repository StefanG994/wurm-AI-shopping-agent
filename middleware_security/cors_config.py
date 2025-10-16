import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def get_cors_origins() -> List[str]:
    """
    Get CORS origins based on environment
    
    Returns:
        List of allowed origins based on environment settings
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    cors_origins = os.getenv("CORS_ORIGINS", "")
    
    if env == "production":
        if cors_origins:
            origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
            # Validate that no wildcards are used in production
            for origin in origins:
                if "*" in origin and origin != "null":
                    raise ValueError(f"Wildcard origins not allowed in production: {origin}")
            return origins
        else:
            return [
                # Ovde ubaciti pravi produkcijski domen i paziti da ne sadrzi kredencijale
                "https://wurm2.px-staging.de/",
                "http://localhost:8000"
            ]
    
    elif env == "development":
        if cors_origins:
            return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        else:
            return [
                "https://wurm2.px-staging.de/",
                "http://localhost:8000"
            ]
    
    else:
        # Testing/staging
        return [
            "https://wurm2.px-staging.de/",
            "http://localhost:8000"
        ]


def setup_cors(app: FastAPI) -> None:
    """    
    Args:
        app: FastAPI application instance
    """
    origins = get_cors_origins()
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    allow_credentials = env in ["development", "production"]
    
    allowed_methods = [
        "GET",
        "POST", 
        "PUT",
        "DELETE",
        "OPTIONS",
        "HEAD"
    ]
    
    allowed_headers = [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",           # JWT tokens
        "X-Requested-With",       # AJAX requests
        "X-API-Key",             # Custom API keys
        "Cache-Control",         # Caching headers
        "sw-context-token",      
        "sw-language-id",        
    ]
    
    # Expose specific headers to the frontend
    expose_headers = [
        "X-Total-Count",         # Pagination info
        "X-Rate-Limit-Remaining", # Rate limiting info
        "sw-context-token",      # Updated Shopware token
    ]
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
        expose_headers=expose_headers,
        max_age=86400,  # Cache preflight requests for 24 hours
    )