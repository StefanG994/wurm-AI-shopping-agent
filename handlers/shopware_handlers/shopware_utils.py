from typing import Any, Dict, Optional, Union
import httpx

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