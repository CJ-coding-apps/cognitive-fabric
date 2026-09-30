"""Dream service: distills episodic memory (Context) into semantic Decisions.

Gathers recent Context nodes, asks an LLM to extract architectural decisions,
and writes Decision nodes + JUSTIFIES edges to the affected symbols. Degrades
gracefully (status="skipped") when no LLM provider is configured.
"""

import datetime
import json
import re
from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.llm import (
    LlmNotConfiguredError,
    get_llm_client,
    get_model_name,
)
from cognitive_fabric.types.entities import DecisionInput, DecisionStatus
from cognitive_fabric.utils.id_utils import format_graph_unique_id

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger("DreamService")

DREAM_DISTILLER_PROMPT = (
    "You are a software architect distilling a coding session into durable "
    "architectural decisions. Given recent session events, extract the key "
    "decisions. Respond ONLY with a JSON object of the form: "
    '{"decisions": [{"id": "dec-...", "name": "...", "rationale": "...", '
    '"affected_symbols": ["file:symbol", ...]}]}. Use short kebab-case ids.'
)


class DreamService:
    """Distills episodic Context into semantic Decisions via an LLM."""

    def __init__(self, container: "ServiceContainer") -> None:
        self._container = container

    async def trigger_dream(
        self,
        repository: str,
        branch: str = "main",
        *,
        llm_client: Optional[Any] = None,
        max_events: int = 20,
    ) -> dict[str, Any]:
        """Run one distillation cycle. Returns a status summary."""
        logger.info("trigger_dream", repository=repository, branch=branch)
        kuzu = await self._container.get_kuzu_client()

        # 1. Gather recent episodic memory. (LIMIT is inlined as a sanitized int;
        #    kuzu does not accept a parameter in the LIMIT clause.)
        limit = max(1, int(max_events))
        rows = kuzu.fetch_all(
            f"""
            MATCH (c:Context)
            WHERE c.repository = $repository AND c.branch = $branch
            RETURN c.summary AS summary, c.observation AS observation,
                   c.iso_date AS iso_date
            ORDER BY c.iso_date DESC
            LIMIT {limit}
            """,
            {"repository": repository, "branch": branch},
        )
        if not rows:
            return {
                "status": "skipped",
                "reason": "no_episodic_memory",
                "distilled_decisions": 0,
            }

        # 2. Resolve the LLM client (degrade gracefully if unconfigured).
        if llm_client is None:
            try:
                llm_client = get_llm_client()
            except LlmNotConfiguredError as e:
                logger.warning("dream skipped: llm not configured", reason=str(e))
                return {
                    "status": "skipped",
                    "reason": "llm_not_configured",
                    "message": str(e),
                    "distilled_decisions": 0,
                }

        # 3. Distill.
        context_text = "\n".join(
            f"[{r.get('iso_date')}] {r.get('summary') or ''}: "
            f"{r.get('observation') or ''}"
            for r in rows
        )
        distillation = self._distill(llm_client, context_text)
        decisions = (
            distillation.get("decisions", [])
            if isinstance(distillation, dict)
            else []
        )

        # 4. Persist Decision nodes + JUSTIFIES edges.
        entity = await self._container.get_entity_service()
        today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        distilled = 0
        for dec in decisions:
            dec_id = dec.get("id")
            if not dec_id:
                continue
            await entity.create_decision(
                repository,
                DecisionInput(
                    id=str(dec_id),
                    name=str(dec.get("name") or dec_id),
                    date=today,
                    rationale=dec.get("rationale"),
                    status=DecisionStatus.ACCEPTED,
                    branch=branch,
                ),
            )
            distilled += 1
            for symbol_id in dec.get("affected_symbols", []) or []:
                self._link_justifies(
                    kuzu, repository, branch, str(dec_id), str(symbol_id)
                )

        logger.info("dream complete", distilled_decisions=distilled)
        return {"status": "success", "distilled_decisions": distilled}

    def _distill(self, llm_client: Any, context_text: str) -> dict[str, Any]:
        """Call the LLM (duck-typed) and parse a JSON distillation."""
        prompt = (
            "Review the following session history and extract new architectural "
            f"decisions:\n\n{context_text}"
        )
        model = get_model_name()
        if hasattr(llm_client, "chat"):  # openai-style
            resp = llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": DREAM_DISTILLER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            text = resp.choices[0].message.content
        elif hasattr(llm_client, "messages"):  # anthropic-style
            resp = llm_client.messages.create(
                model=model,
                max_tokens=2000,
                system=DREAM_DISTILLER_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
        else:
            raise ValueError("Unsupported LLM client type")
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse a JSON object from an LLM response (tolerant of surrounding prose)."""
        if not text:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def _link_justifies(
        kuzu: Any, repository: str, branch: str, decision_id: str, symbol_id: str
    ) -> None:
        dec_gid = format_graph_unique_id(repository, branch, decision_id)
        sym_gid = format_graph_unique_id(repository, branch, symbol_id)
        kuzu.execute_query(
            """
            MATCH (d:Decision {graph_unique_id: $dec})
            MATCH (s:Symbol {graph_unique_id: $sym})
            MERGE (d)-[:JUSTIFIES]->(s)
            """,
            {"dec": dec_gid, "sym": sym_gid},
        )
