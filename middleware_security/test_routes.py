"""
Security testing endpoints
"""
from fastapi import APIRouter, Response
from typing import Dict, Any

router = APIRouter(prefix="/security", tags=["Security Testing"])

@router.get("/headers")
async def test_security_headers(response: Response) -> Dict[str, Any]:
    """
    Test endpoint to verify security headers are being applied
    Check the response headers in browser dev tools or curl
    """
    return {
        "message": "Check the response headers to verify security configuration",
        "instructions": [
            "Open browser dev tools (F12)",
            "Go to Network tab",
            "Make this request",
            "Check response headers for:",
            "- Content-Security-Policy",
            "- X-Frame-Options",
            "- X-Content-Type-Options", 
            "- Referrer-Policy",
            "- X-XSS-Protection"
        ]
    }

@router.get("/cors-test")
async def test_cors() -> Dict[str, Any]:
    """
    Test CORS configuration
    Make this request from your frontend to verify CORS works
    """
    return {
        "message": "CORS test successful",
        "origin_allowed": True,
        "timestamp": "2025-01-13T12:00:00Z"
    }