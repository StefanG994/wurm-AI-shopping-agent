from __future__ import annotations
from fastapi import Request
from .graphiti_memory import GraphitiMemory

def get_mem(request: Request) -> GraphitiMemory:
    mem = getattr(request.app.state, "mem", None)
    if mem is None:
        raise RuntimeError("Graphiti memory not available on app.state.mem")
    return mem
