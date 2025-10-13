"""
Utility for retrieving system prompts in multiple languages with variable substitution.

Usage:
    from get_translated_prompt import get_translated_prompt
    prompt = get_translated_prompt("ROUTER_SYSTEM", language_id="it-IT",
                                   variables={"SEARCH_TOOLS": [...], "CART_TOOLS": [...], "COMM_TOOLS": [...]} )
"""

from __future__ import annotations
import json
from typing import Any, Dict, Optional
from string import Template

# ---------------------------
# Public API
# ---------------------------

__all__ = ["get_translated_prompt", "AVAILABLE_LANGS", "PROMPT_KEYS"]

AVAILABLE_LANGS = ("en", "it", "es", "pt", "zh", "id", "de", "nl", "fr")
PROMPT_KEYS = ("OUTLINE_SYSTEM", "ROUTER_SYSTEM", "SEARCH_SYSTEM", "CART_SYSTEM", "COMM_SYSTEM", "ORDER_SYSTEM")

# ##### Mapping of the language-id to the language-key
# {
#     '2fbb5fe2e29a4d70aa5854ce7ce3e20b': "de",
#     '084a93e951724a22bdd1cf7f723a0b43': "de",
#     '028ef8a4e2b14f50b3d92fc5998e618f': "it",
#     '3a5d46e063ae41cd8afa317b08039387': "en",
#     '704bb3d0d1b94fffbca47bb9d09befc7': "es",
#     '777c3dadc7a74fd9bc13db9a3091dfbe': "nl",
#     'eb7b825fcdab409a97ee2da691f954b4': "de",
#     'f9976804849247b3844fdeeb2c0a8066': "fr",
# }


def get_translated_prompt(prompt_key: str,
                          language_id: Optional[str] = None,
                          variables: Optional[Dict[str, Any]] = None) -> str:
    """
    Return the translated system prompt for `prompt_key`, localized by `language_id`,
    with `${VARNAME}` placeholders filled from `variables`.

    - prompt_key: one of PROMPT_KEYS
    - language_id: ISO locale (e.g., 'en-GB', 'it-IT', 'pt-BR', 'zh-CN', 'id-ID') or language code ('en','it',...)
                   Unknown values fall back to 'en'.
    - variables: dict of values to inject; non-strings are JSON-encoded.

    Example:
        get_translated_prompt("SEARCH_SYSTEM", "es-ES", {"SEARCH_TOOLS": tools})
    """
    key = prompt_key.strip().upper()
    if key not in PROMPT_KEYS:
        raise KeyError(f"Unknown prompt_key '{prompt_key}'. Valid: {', '.join(PROMPT_KEYS)}")

    lang = _resolve_lang(language_id)
    # Fallback to English if translation is missing
    if lang not in _PROMPTS or key not in _PROMPTS[lang]:
        lang = "en"

    raw_template = _PROMPTS[lang][key]
    render_vars = _normalize_vars(variables or {})
    # Safe substitution: leaves unknown ${VAR} intact rather than raising
    text = Template(raw_template).safe_substitute(render_vars)
    return text


# ---------------------------
# Helpers
# ---------------------------

def _resolve_lang(language_id: Optional[str]) -> str:
    """Map languageId/locale to internal code: en/it/es/pt/zh/id (default: en)."""
    if not language_id:
        return "en"

    # locale aliases
    if language_id == '3a5d46e063ae41cd8afa317b08039387':
        return "en"
    if language_id == '028ef8a4e2b14f50b3d92fc5998e618f':
        return "it"
    if language_id == '704bb3d0d1b94fffbca47bb9d09befc7':
        return "es"
    if language_id == '2fbb5fe2e29a4d70aa5854ce7ce3e20b' or language_id == '084a93e951724a22bdd1cf7f723a0b43' or language_id == 'eb7b825fcdab409a97ee2da691f954b4':
        return "de"
    if language_id == 'f9976804849247b3844fdeeb2c0a8066':
        return "fr"
    if language_id == '777c3dadc7a74fd9bc13db9a3091dfbe':
        return "nl"

    # Unknown (e.g., Shopware GUID) -> default
    return "en"


def _normalize_vars(vars_in: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert all values to strings; dicts/lists -> compact JSON.
    This lets you pass Python objects directly (schemas, tool specs, etc.).
    """
    out: Dict[str, str] = {}
    for k, v in vars_in.items():
        if isinstance(v, (dict, list, tuple)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = str(v)
    return out


# ---------------------------
# Prompt Catalog
# Keep ${PLACEHOLDERS} as-is; they are substituted at runtime.
# ---------------------------

_PROMPTS: Dict[str, Dict[str, str]] = {
    "en": {
    },

    # ------------------ German ------------------
    "de": {
    },

    # ------------------ French ------------------
    "fr": {
    },

    # ------------------ Dutch (Netherlands) ------------------
    "nl": {
    },

    # ------------------ Italian ------------------
    "it": {
    },

    # ------------------ Spanish ------------------
    "es": {
    },

    # ------------------ Portuguese ------------------
    "pt": {
    },

    # ------------------ Chinese (Simplified) ------------------
    "zh": {
    },

    # ------------------ Indonesian ------------------
    "id": {
    },
}
