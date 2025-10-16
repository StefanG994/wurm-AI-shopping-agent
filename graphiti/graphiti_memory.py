from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType, EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_NODE_DISTANCE,
)
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.search.models import RawEpisode

# ---- Optional LLM client imports (use what you need) ----
# OpenAI (default)
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

@dataclass
class GraphDBConfig:
    """Database connection config for Graphiti."""
    uri: str = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.environ.get("NEO4J_USER", "neo4j")
    password: str = os.environ.get("NEO4J_PASSWORD", "password")


@dataclass
class LLMBackend:
    """Simple selector for LLM/embedding/cross-encoder backends.

    backends:
      - "openai" (default)
    """
    name: str = "openai"
    # general knobs
    model: str | None = None
    small_model: str | None = None
    embedding_model: str | None = None
    api_key: str | None = None


class GraphitiMemory:
    """High-level, asyncio wrapper around Graphiti for agent memory."""

    def __init__(
        self,
        db: GraphDBConfig | None = None,
        llm: LLMBackend | None = None,
        semaphore_limit: int | None = None,
        telemetry_enabled: Optional[bool] = None,
    ) -> None:
        self.db = db or GraphDBConfig()
        self.llm = llm or LLMBackend(name="openai")
        if semaphore_limit is not None:
            os.environ["SEMAPHORE_LIMIT"] = str(semaphore_limit)  # ingestion concurrency
        if telemetry_enabled is not None:
            os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "true" if telemetry_enabled else "false"

        # Filled in by initialize()
        self.client: Optional[Graphiti] = None

    # ------------------- lifecycle -------------------

    async def initialize(self, build_indices: bool = True) -> None:
        """Connect and (optionally) build indices/constraints (one-time)."""
        self.client = self._make_graphiti_client()
        if build_indices:
            await self.client.build_indices_and_constraints()  # one-time setup
        # Note: close connection with .close()

    async def close(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None

    # ------------------- ingestion: episodes -------------------

    async def add_episode_text(
        self,
        name: str,
        text: str,
        *,
        description: str | None = None,
        reference_time: datetime | None = None,
        entity_types: Optional[Mapping[str, Any]] = None,
        edge_types: Optional[Mapping[str, Any]] = None,
        edge_type_map: Optional[Mapping[tuple[str, str], list[str]]] = None,
        excluded_entity_types: Optional[list[str]] = None,
    ) -> None:
        """Add a TEXT episode (provenance-aware ingestion)."""
        g = self._need()
        await g.add_episode(
            name=name,
            episode_body=text,
            source=EpisodeType.text,
            source_description=description or "",
            reference_time=(reference_time or datetime.now(timezone.utc)),
            entity_types=entity_types,
            edge_types=edge_types,
            edge_type_map=edge_type_map,
            excluded_entity_types=excluded_entity_types,
        )

    async def add_episode_message(
        self,
        name: str,
        conversation_text: str,
        *,
        description: str | None = None,
        reference_time: datetime | None = None,
        **kw: Any,
    ) -> None:
        """Add a MESSAGE episode; `conversation_text` must be 'speaker: text' pairs."""
        g = self._need()
        await g.add_episode(
            name=name,
            episode_body=conversation_text,
            source=EpisodeType.message,
            source_description=description or "",
            reference_time=(reference_time or datetime.now(timezone.utc)),
            **kw,
        )

    async def add_episode_json(
        self,
        name: str,
        payload: Mapping[str, Any],
        *,
        description: str | None = None,
        reference_time: datetime | None = None,
        **kw: Any,
    ) -> None:
        """Add a JSON episode (structured import)."""
        g = self._need()
        # Graphiti accepts dict directly for JSON episodes per docs.
        await g.add_episode(
            name=name,
            episode_body=payload,
            source=EpisodeType.json,
            source_description=description or "",
            reference_time=(reference_time or datetime.now(timezone.utc)),
            **kw,
        )

    async def add_episodes_bulk(
        self,
        bulk: Iterable[dict | RawEpisode],
    ) -> None:
        """High-throughput bulk ingestion. Use only when invalidation is not required."""
        g = self._need()
        prepared: list[RawEpisode] = []
        for item in bulk:
            if isinstance(item, RawEpisode):
                prepared.append(item)
            else:
                # Accepts dicts like {"name":..., "content":..., "source":..., "source_description":..., "reference_time":...}
                prepared.append(
                    RawEpisode(
                        name=item["name"],
                        content=item["content"] if isinstance(item["content"], str) else json.dumps(item["content"]),
                        source=item.get("source", EpisodeType.json),
                        source_description=item.get("source_description", ""),
                        reference_time=item.get("reference_time", datetime.now(timezone.utc)),
                    )
                )
        await g.add_episode_bulk(prepared)

    # ------------------- search -------------------

    async def search_edges(
        self,
        query: str,
        *,
        center_node_uuid: str | None = None,
        limit: int | None = None,
    ):
        """Hybrid search over edges; optionally rerank by graph distance to a focal node."""
        g = self._need()
        if center_node_uuid:
            return await g.search(query, center_node_uuid=center_node_uuid)
        return await g.search(query, limit=limit)

    async def search_nodes_rrf(self, query: str, *, limit: int = 25):
        """Node search using predefined RRF recipe."""
        g = self._need()
        cfg = NODE_HYBRID_SEARCH_RRF(limit)
        results = await g._search(query, cfg)
        return results.nodes

    # ------------------- CRUD helpers (entity nodes/edges) -------------------

    async def get_entity_by_uuid(self, uuid: str) -> EntityNode:
        """Fetch an Entity node by UUID (thin wrapper)."""
        g = self._need()
        # Graphiti exposes class methods like get_by_uuid; we call via our DB driver through underlying client.
        driver = g.neo4j._driver  # access underlying AsyncDriver
        return await EntityNode.get_by_uuid(driver, uuid)  # type: ignore[attr-defined]

    async def save_entity_node(
        self,
        node: EntityNode,
    ) -> Any:
        """Create/update an Entity node."""
        g = self._need()
        driver = g.neo4j._driver
        return await node.save(driver)  # type: ignore[attr-defined]

    async def delete_entity_node(self, node: EntityNode) -> Any:
        """Hard delete an Entity node (DETACH DELETE)."""
        g = self._need()
        driver = g.neo4j._driver
        return await node.delete(driver)  # type: ignore[attr-defined]

    async def save_entity_edge(self, edge: EntityEdge) -> Any:
        """Create/update an Entity edge."""
        g = self._need()
        driver = g.neo4j._driver
        return await edge.save(driver)  # type: ignore[attr-defined]

    async def delete_entity_edge(self, edge: EntityEdge) -> Any:
        """Hard delete an Entity edge."""
        g = self._need()
        driver = g.neo4j._driver
        return await edge.delete(driver)  # type: ignore[attr-defined]

    # ------------------- explicit fact triples -------------------

    async def add_fact_triple(
        self,
        *,
        source_uuid: str,
        source_name: str,
        target_uuid: str,
        target_name: str,
        edge_name: str,
        fact_text: str,
        group_id: str = "",
        created_at: Optional[datetime] = None,
    ) -> None:
        """Add (or de-dupe & upsert) an (EntityNode)─[EntityEdge]→(EntityNode) triple."""
        g = self._need()
        src = EntityNode(uuid=source_uuid, name=source_name, group_id=group_id)
        tgt = EntityNode(uuid=target_uuid, name=target_name, group_id=group_id)
        edge = EntityEdge(
            group_id=group_id,
            source_node_uuid=source_uuid,
            target_node_uuid=target_uuid,
            created_at=(created_at or datetime.now(timezone.utc)),
            name=edge_name,
            fact=fact_text,
        )
        await g.add_triplet(src, edge, tgt)

    # ------------------- internals -------------------

    def _need(self) -> Graphiti:
        if not self.client:
            raise RuntimeError("GraphitiMemory not initialized. Call .initialize() first.")
        return self.client

    def _make_graphiti_client(self) -> Graphiti:
        """Instantiate Graphiti with the chosen LLM/embedder/reranker stack."""
        name = (self.llm.name or "openai").lower()

        if name == "openai":
            llm_cfg = LLMConfig(model=self.llm.model or "gpt-4.1-mini",
                                small_model=self.llm.small_model or "gpt-4.1-nano")
            embedder = OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    embedding_model=self.llm.embedding_model or "text-embedding-3-small"
                )
            )
            cross = OpenAIRerankerClient(config=LLMConfig(model=llm_cfg.small_model))
            return Graphiti(self.db.uri, self.db.user, self.db.password,
                            llm_client=OpenAIClient(config=llm_cfg),
                            embedder=embedder,
                            cross_encoder=cross)

        raise ValueError(f"Unknown LLM backend: {self.llm.name}")


# --------------- quick smoke example ---------------

async def _example():
    mem = GraphitiMemory(
        db=GraphDBConfig(),
        llm=LLMBackend(name="openai"),
        semaphore_limit=int(os.environ.get("SEMAPHORE_LIMIT", "10")),
    )
    await mem.initialize(build_indices=True)

    # Add a text episode
    await mem.add_episode_text(
        name="example_doc",
        text="Kamala Harris served as Attorney General of California.",
        description="podcast transcript",
        reference_time=datetime.now(timezone.utc),
    )

    # Search edges (hybrid)
    edges = await mem.search_edges("Who was the California Attorney General?")
    for e in edges:
        print(e.uuid, e.fact)

    await mem.close()


if __name__ == "__main__":
    asyncio.run(_example())
