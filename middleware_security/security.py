import os
from typing import Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    Python equivalent to Helmet.js for Node.js/Express
    !!!!!! Change line 98 to "self" when using voice input
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.config = self._get_security_config(**kwargs)
    
    def _get_security_config(self, **kwargs) -> Dict[str, any]:
        config = {
            # Prevents XSS attacks
            "content_security_policy": {
                "enabled": kwargs.get("csp_enabled", True),
                "policy": kwargs.get("csp_policy") or self._get_default_csp()
            },
            
            # HTTP Strict Transport Security - Forces HTTPS connections (only for production)
            "hsts": {
                "enabled": kwargs.get("hsts_enabled", self.environment == "production"),
                "max_age": kwargs.get("hsts_max_age", 31536000),  # 1 year
                "include_subdomains": kwargs.get("hsts_include_subdomains", True),
                "preload": kwargs.get("hsts_preload", False)
            },
            
            # Prevents clickjacking attacks
            "frame_options": {
                "enabled": kwargs.get("frame_options_enabled", True),
                "policy": kwargs.get("frame_options", "DENY")  # DENY, SAMEORIGIN, or specific URL
            },
            
            # Prevents MIME sniffing
            "content_type_options": {
                "enabled": kwargs.get("content_type_options_enabled", True)
            },
            
            # X-XSS-Protection - Browser XSS filter (legacy but still useful)
            "xss_protection": {
                "enabled": kwargs.get("xss_protection_enabled", True),
                "mode": kwargs.get("xss_protection_mode", "1; mode=block")
            },
            
            # Controls referrer information
            "referrer_policy": {
                "enabled": kwargs.get("referrer_policy_enabled", True),
                "policy": kwargs.get("referrer_policy", "strict-origin-when-cross-origin")
            },
            
            # Controls browser features
            "permissions_policy": {
                "enabled": kwargs.get("permissions_policy_enabled", True),
                "policy": kwargs.get("permissions_policy") or self._get_default_permissions_policy()
            }
        }
        
        return config
    
    def _get_default_csp(self) -> str:
        # CSP - Content Security Policy
        if self.environment == "development":
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:*; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' localhost:* ws://localhost:* wss://localhost:*; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )
        else:
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'"
            )
    
    def _get_default_permissions_policy(self) -> str:
        return (
            "camera=(), "
            "microphone=(), " # this have to be set to self when using voice input
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "payment=(), "
            "usb=()"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Overridden method from BaseHTTPMiddleware
        Process the request and add security headers to response
        """
        response = await call_next(request)
        
        # Prevents XSS (Cross-Site Scripting or malicious scripts)
        if self.config["content_security_policy"]["enabled"]:
            response.headers["Content-Security-Policy"] = self.config["content_security_policy"]["policy"]
        
        if (self.config["hsts"]["enabled"] and 
            (request.url.scheme == "https" or self.environment == "production")):
            hsts_value = f"max-age={self.config['hsts']['max_age']}"
            if self.config["hsts"]["include_subdomains"]:
                hsts_value += "; includeSubDomains"
            if self.config["hsts"]["preload"]:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # Prevents clickjacking
        if self.config["frame_options"]["enabled"]:
            response.headers["X-Frame-Options"] = self.config["frame_options"]["policy"]

        # Prevents MIME sniffing
        if self.config["content_type_options"]["enabled"]:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevents cross-site scripting attacks
        if self.config["xss_protection"]["enabled"]:
            response.headers["X-XSS-Protection"] = self.config["xss_protection"]["mode"]
        
        if self.config["referrer_policy"]["enabled"]:
            response.headers["Referrer-Policy"] = self.config["referrer_policy"]["policy"]
        
        if self.config["permissions_policy"]["enabled"]:
            response.headers["Permissions-Policy"] = self.config["permissions_policy"]["policy"]
        
        response.headers["X-API-Version"] = "v1"
        response.headers["X-Powered-By"] = "WURM AI Agent"  # Custom branding
        
        # Remove potentially sensitive headers which can leak server info
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


def setup_security_headers(app, **kwargs):
    """
    Args:
        app: FastAPI application
        **kwargs: Configuration options for security headers
    """
    print("Setting up security headers middleware...")
    app.add_middleware(SecurityHeadersMiddleware, **kwargs)