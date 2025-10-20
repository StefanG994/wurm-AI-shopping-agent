# graphiti/context_builder.py
from __future__ import annotations
from typing import Any, Dict, List
from .graphiti_memory import GraphitiMemory

async def build_context_outline(mem: GraphitiMemory, user_query: str, *, limit: int = 12) -> str:
    """Hybrid search over edges + nodes, return a compact outline for prompts."""
    # Edges capture factual triples (e.g., PREFERS, WANTS), nodes add entities.
    edges_res = await mem.search_edges(user_query, limit=limit)
    nodes = await mem.search_nodes_rrf(user_query, limit=limit)

    lines: List[str] = []
    # Edges
    if hasattr(edges_res, "edges"):
        for e in edges_res.edges[:limit]:
            # e.fact often holds the extracted relation text
            lines.append(f"- EDGE[{getattr(e, 'name', 'FACT')}]: {getattr(e, 'fact', '')} (src={e.source_node_uuid}, tgt={e.target_node_uuid})")

    # Nodes
    for n in nodes[:limit]:
        nm = getattr(n, "name", "") or getattr(n, "summary", "")
        typ = getattr(n, "type", "")
        lines.append(f"- NODE[{typ}]: {nm} ({n.uuid})")

    if not lines:
        return "No prior knowledge found."

    return "Relevant knowledge (Graphiti):\n" + "\n".join(lines[:limit])
