"""Copilot Service — orchestrates intent → retrieve → prompt → LLM → validate → log."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.args.llm.port import LlmPort, MockLlmPort
from app.args.llm.providers import build_llm_port
from app.copilot.citations import ValidationResult, citations_to_dicts, validate
from app.copilot.intent import CopilotIntent, classify
from app.copilot.lineage import lineage_summary
from app.copilot.llm_intent import llm_classify
from app.copilot.prompt_builder import build as build_prompt
from app.copilot.retriever import RetrievalContext, retrieve
from app.models.copilot import CopilotQueryLog


class CopilotService:
    def __init__(
        self,
        db: Session,
        *,
        llm: LlmPort | None = None,
    ) -> None:
        self.db = db
        self._llm = llm or self._default_llm()

    # ── Public API ────────────────────────────────────────────────────────────

    def ask(
        self,
        question: str,
        *,
        session_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> dict:
        """Process a question and return a grounded answer with citations."""
        started = time.perf_counter()

        # 1. Classify intent + extract entities (deterministic regex first).
        classification = classify(question)

        # 1b. Low-confidence (generic fallback) → let the LLM pick a better
        #     intent. Refusals are decided above and never reach this path.
        if classification.low_confidence and classification.intent != CopilotIntent.REFUSED:
            llm_intent = llm_classify(question, self._llm)
            if llm_intent is not None:
                classification.intent = llm_intent
                classification.low_confidence = False

        # 2. Short-circuit for refused questions
        if classification.intent == CopilotIntent.REFUSED:
            log = self._log(
                question=question,
                intent=CopilotIntent.REFUSED,
                entities={},
                retrieved_ids=[],
                answer=classification.refuse_reason,
                citations=[],
                model=None,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                refused=True,
                session_id=session_id,
                user_id=user_id,
                answer_hash="",
            )
            return {
                "answer": classification.refuse_reason,
                "citations": [],
                "intent": CopilotIntent.REFUSED,
                "refused": True,
                "query_log_id": str(log.id),
            }

        # 3. Retrieve context from DB
        context: RetrievalContext = retrieve(
            self.db, classification.intent, classification.entities
        )

        # 4. Build prompt
        prompt = build_prompt(question, context)

        # 5. Call LLM
        completion = self._llm.complete(system=prompt.system, user=prompt.user)

        # 6. Validate citations
        validated: ValidationResult = validate(completion.content)

        latency_ms = int((time.perf_counter() - started) * 1000)

        # 7. Log
        log = self._log(
            question=question,
            intent=classification.intent,
            entities={
                "symbol": classification.entities.symbol,
                "as_of_date": classification.entities.as_of_date.isoformat()
                if classification.entities.as_of_date
                else None,
                "strategy_name": classification.entities.strategy_name,
            },
            retrieved_ids=context.source_refs,
            answer=validated.answer,
            citations=citations_to_dicts(validated.citations),
            model=completion.model,
            prompt_tokens=completion.input_tokens,
            completion_tokens=completion.output_tokens,
            latency_ms=latency_ms,
            refused=False,
            session_id=session_id,
            user_id=user_id,
            answer_hash=validated.answer_hash,
        )

        return {
            "answer": validated.answer,
            "citations": citations_to_dicts(validated.citations),
            "uncited_claims": validated.uncited_claims,
            "intent": classification.intent,
            "refused": False,
            "model": completion.model,
            "latency_ms": latency_ms,
            "query_log_id": str(log.id),
            "lineage": lineage_summary(context.source_refs),
        }

    def get_audit_logs(
        self, limit: int = 50, *, user_id: UUID | None = None
    ) -> list[CopilotQueryLog]:
        from sqlalchemy import desc, select

        stmt = select(CopilotQueryLog)
        if user_id is not None:
            stmt = stmt.where(CopilotQueryLog.user_id == user_id)
        return list(self.db.scalars(stmt.order_by(desc(CopilotQueryLog.created_at)).limit(limit)).all())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _log(self, **kwargs) -> CopilotQueryLog:
        log = CopilotQueryLog(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **kwargs,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def _default_llm(self) -> LlmPort:
        try:
            from app.args.llm.config import ArgsLlmSettings
            from app.core.config import get_settings

            settings = get_settings()
            llm_settings = ArgsLlmSettings.from_settings(settings)
            cfg = llm_settings.for_agent("copilot")
            return build_llm_port(cfg)
        except Exception:
            return MockLlmPort()
