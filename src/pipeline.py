from __future__ import annotations

from typing import Any, Callable, Literal

from .prompts import (
    ANALYST_INSTRUCTIONS,
    CHECKER_INSTRUCTIONS,
    OBSERVER_INSTRUCTIONS,
    QUERY_FORMULATOR_INSTRUCTIONS,
    RETRIEVER_INSTRUCTIONS,
    STRATEGIST_INSTRUCTIONS,
)
from .schemas import (
    ConflictAnalysis,
    ConsistencyCheck,
    ContextPacket,
    ExplicitRepresentation,
    FinalReasoningResult,
    MechanismDecision,
    QueryFormulation,
    ReasoningCase,
)

StageName = Literal["stage1", "stage2", "stage3", "stage4", "stage5"]
ProgressCallback = Callable[[str], None]


class ConflictReasoningPipeline:
    def __init__(
        self,
        progress_callback: ProgressCallback | None = None,
        max_revision_rounds: int = 1,
    ) -> None:
        self.progress_callback = progress_callback
        self.max_revision_rounds = max(0, int(max_revision_rounds))
        self.prompt_trace: dict[str, str] = {}
        self.prompt_templates = {
            "stage1": OBSERVER_INSTRUCTIONS,
            "stage2_prompt1": QUERY_FORMULATOR_INSTRUCTIONS,
            "stage2_prompt2": RETRIEVER_INSTRUCTIONS,
            "stage3": ANALYST_INSTRUCTIONS,
            "stage4": STRATEGIST_INSTRUCTIONS,
            "stage5": CHECKER_INSTRUCTIONS,
        }

    async def run(self, case: ReasoningCase) -> FinalReasoningResult:
        artifacts = await self.run_stages(case=case, stop_after="stage5")
        return artifacts["final_result"]

    async def run_stages(
        self,
        case: ReasoningCase,
        stop_after: StageName = "stage5",
        resume_from: StageName = "stage1",
        seed_artifacts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del resume_from
        del seed_artifacts
        self.prompt_trace = {}
        artifacts: dict[str, Any] = {"case": case.model_dump(by_alias=True)}

        stage1_prompt = self._render_prompt(
            template=self.prompt_templates["stage1"],
            variables={
                "Text Input": case.input.text,
                "Visual Input": self._media_visual(case),
                "Audio Input": self._media_audio(case),
            },
        )
        if stage1_prompt:
            self.prompt_trace["stage1"] = stage1_prompt

        explicit = self._run_step1_explicit_perception(case)
        artifacts["stage1"] = explicit.model_dump()
        self._emit(case.case_id, "stage1")
        if stop_after == "stage1":
            return artifacts

        stage2_prompt1 = self._render_prompt(
            template=self.prompt_templates["stage2_prompt1"],
            variables={"Explicit Perception": explicit.caption},
        )
        if stage2_prompt1:
            self.prompt_trace["stage2_prompt1"] = stage2_prompt1

        query_formulation, snippets, context_packet = self._run_step2_social_context(case, explicit)

        stage2_prompt2 = self._render_prompt(
            template=self.prompt_templates["stage2_prompt2"],
            variables={
                "Social Query": self._query_to_text(query_formulation),
                "Explicit Perception": explicit.caption,
            },
        )
        if stage2_prompt2:
            self.prompt_trace["stage2_prompt2"] = stage2_prompt2

        artifacts["stage2"] = {
            "query_formulation": query_formulation.model_dump(),
            "search_snippets": snippets,
            "context_packet": context_packet.model_dump(),
        }
        self._emit(case.case_id, "stage2")
        if stop_after == "stage2":
            return artifacts

        stage3_prompt = self._render_prompt(
            template=self.prompt_templates["stage3"],
            variables={
                "Explicit Perception": explicit.caption,
                "Social Context": self._context_to_text(context_packet),
            },
        )
        if stage3_prompt:
            self.prompt_trace["stage3"] = stage3_prompt

        conflict = self._run_step3_conflict_modeling(explicit, context_packet)
        artifacts["stage3"] = conflict.model_dump()
        self._emit(case.case_id, "stage3")
        if stop_after == "stage3":
            return artifacts

        stage4_prompt = self._render_prompt(
            template=self.prompt_templates["stage4"],
            variables={
                "Context_Expectation": conflict.context_expectation,
                "Explicit_Reality": conflict.explicit_reality,
                "The_Conflict": conflict.conflict,
                "Abductive_Question": conflict.abductive_question,
                "taxonomy_reference": "",
                "mechanisms": self._join_values(case.allowed_mechanisms),
                "labels": self._join_values(case.allowed_labels),
                "options.subject": self._join_values(case.options.subject),
                "options.target": self._join_values(case.options.target),
                "Subject": case.options.subject[0] if case.options.subject else "",
                "Target": case.options.target[0] if case.options.target else "",
                "Mechanism": case.allowed_mechanisms[0] if case.allowed_mechanisms else "",
                "Label": case.allowed_labels[0] if case.allowed_labels else "",
            },
        )
        if stage4_prompt:
            self.prompt_trace["stage4"] = stage4_prompt

        mechanism = self._run_step4_abductive_reasoning(case, explicit, context_packet, conflict)
        artifacts["stage4"] = mechanism.model_dump()
        self._emit(case.case_id, "stage4")
        if stop_after == "stage4":
            return artifacts

        stage5_prompt = self._render_prompt(
            template=self.prompt_templates["stage5"],
            variables={
                "Explicit Perception": explicit.caption,
                "Social Context": self._context_to_text(context_packet),
                "The_Conflict": conflict.conflict,
                "Subject": mechanism.subject,
                "Target": mechanism.target,
                "Mechanism": mechanism.mechanism,
                "Label": mechanism.label,
            },
        )
        if stage5_prompt:
            self.prompt_trace["stage5"] = stage5_prompt

        check = self._run_step5_consistency_verification(explicit, context_packet, conflict, mechanism)
        revision_history: list[dict[str, Any]] = []
        for round_id in range(1, self.max_revision_rounds + 1):
            if check.status == "ACCEPTED":
                break
            query_formulation, snippets, context_packet = self._run_step2_social_context(
                case, explicit, refinement_hint=check.verification_note
            )
            conflict = self._run_step3_conflict_modeling(explicit, context_packet)
            mechanism = self._run_step4_abductive_reasoning(case, explicit, context_packet, conflict)
            check = self._run_step5_consistency_verification(explicit, context_packet, conflict, mechanism)
            revision_history.append(
                {
                    "round": round_id,
                    "feedback": check.verification_note,
                    "stage2": {
                        "query_formulation": query_formulation.model_dump(),
                        "search_snippets": snippets,
                        "context_packet": context_packet.model_dump(),
                    },
                    "stage3": conflict.model_dump(),
                    "stage4": mechanism.model_dump(),
                    "stage5": check.model_dump(),
                }
            )

        artifacts["stage2"] = {
            "query_formulation": query_formulation.model_dump(),
            "search_snippets": snippets,
            "context_packet": context_packet.model_dump(),
        }
        artifacts["stage3"] = conflict.model_dump()
        artifacts["stage4"] = mechanism.model_dump()
        artifacts["stage5"] = check.model_dump()
        artifacts["revision_history"] = revision_history

        final_result = FinalReasoningResult(
            case=case,
            explicit_representation=explicit,
            context_packet=context_packet,
            conflict_analysis=conflict,
            mechanism_decision=mechanism,
            consistency_check=check,
            accepted=check.status == "ACCEPTED",
            reasoning_chain=["stage1", "stage2", "stage3", "stage4", "stage5"],
            final_explanation=self._compose_final_explanation(conflict, mechanism, check),
        )
        artifacts["final_result"] = final_result
        self._emit(case.case_id, "stage5")
        return artifacts

    def _run_step1_explicit_perception(self, case: ReasoningCase) -> ExplicitRepresentation:
        media = case.input.media
        text = case.input.text.strip()
        speech = (
            media.audio_caption.strip()
            if media and isinstance(media.audio_caption, str) and media.audio_caption.strip()
            else ""
        )
        text_cues = [text] if text else []
        if speech:
            text_cues.append(speech)
        caption_parts = []
        if text:
            caption_parts.append(text)
        if speech:
            caption_parts.append(speech)
        return ExplicitRepresentation(
            text_cues=text_cues,
            static_visual_cues=[],
            temporal_visual_cues=[],
            speech_transcript=speech,
            caption="\n".join(caption_parts),
        )

    def _run_step2_social_context(
        self,
        case: ReasoningCase,
        explicit: ExplicitRepresentation,
        refinement_hint: str = "",
    ) -> tuple[QueryFormulation, list[dict[str, str]], ContextPacket]:
        del case
        del explicit
        del refinement_hint
        return (
            QueryFormulation(retrieval_questions=[]),
            [],
            ContextPacket(fact=[], connection=[], social_norm=[]),
        )

    def _run_step3_conflict_modeling(
        self, explicit: ExplicitRepresentation, context: ContextPacket
    ) -> ConflictAnalysis:
        del context
        return ConflictAnalysis(
            context_expectation="",
            explicit_reality=explicit.caption,
            conflict_statement="",
            conflict="",
            conflict_type="",
            abductive_question="",
        )

    def _run_step4_abductive_reasoning(
        self,
        case: ReasoningCase,
        explicit: ExplicitRepresentation,
        context: ContextPacket,
        conflict: ConflictAnalysis,
    ) -> MechanismDecision:
        del explicit
        del context
        del conflict
        mechanism = case.allowed_mechanisms[0] if case.allowed_mechanisms else ""
        label = case.allowed_labels[0] if case.allowed_labels else ""
        subject = case.options.subject[0] if case.options.subject else ""
        target = case.options.target[0] if case.options.target else ""
        return MechanismDecision(
            label=label,
            subject=subject,
            target=target,
            mechanism=mechanism,
            hidden_meaning="",
            counterfactual_cost=[],
            conflict_utility=[],
            out_of_frame_inference=[],
        )

    def _run_step5_consistency_verification(
        self,
        explicit: ExplicitRepresentation,
        context: ContextPacket,
        conflict: ConflictAnalysis,
        mechanism: MechanismDecision,
    ) -> ConsistencyCheck:
        del conflict
        explicit_ok = bool(explicit.caption)
        context_ok = bool(context.fact or context.connection or context.social_norm)
        mechanism_ok = bool(mechanism.mechanism and mechanism.label)
        status: Literal["ACCEPTED", "REJECTED"] = "ACCEPTED"
        note = "All checks passed."
        if not (explicit_ok and context_ok and mechanism_ok):
            status = "REJECTED"
            note = "Framework mode: detailed modules are omitted."
        return ConsistencyCheck(
            explicit_evidence_alignment=explicit_ok,
            context_alignment=context_ok,
            mechanism_alignment=mechanism_ok,
            status=status,
            verification_note=note,
        )

    def _compose_final_explanation(
        self, conflict: ConflictAnalysis, mechanism: MechanismDecision, check: ConsistencyCheck
    ) -> str:
        return (
            f"Conflict: {conflict.conflict}\n"
            f"Decision A: {{{mechanism.subject}, {mechanism.target}, {mechanism.mechanism}, {mechanism.label}}}\n"
            f"Verification: {check.status} ({check.verification_note})"
        )

    def _emit(self, case_id: str, stage: StageName) -> None:
        if self.progress_callback:
            self.progress_callback(f"[{case_id}] {stage}")

    def _render_prompt(self, template: str, variables: dict[str, str] | None = None) -> str:
        text = template
        if variables:
            for key, value in variables.items():
                text = text.replace("{" + key + "}", value)
        return text

    def _media_visual(self, case: ReasoningCase) -> str:
        media = case.input.media
        if not media:
            return ""
        if media.image_url:
            return media.image_url
        if media.video_url:
            return media.video_url
        if media.url:
            return media.url
        return ""

    def _media_audio(self, case: ReasoningCase) -> str:
        media = case.input.media
        if not media or not media.audio_caption:
            return ""
        return media.audio_caption

    def _query_to_text(self, query_formulation: QueryFormulation) -> str:
        if not query_formulation.retrieval_questions:
            return ""
        return " | ".join(q.question for q in query_formulation.retrieval_questions if q.question)

    def _context_to_text(self, context: ContextPacket) -> str:
        parts: list[str] = []
        if context.fact:
            parts.append("fact: " + " | ".join(context.fact))
        if context.connection:
            parts.append("connection: " + " | ".join(context.connection))
        if context.social_norm:
            parts.append("social_norm: " + " | ".join(context.social_norm))
        return "\n".join(parts)

    def _join_values(self, values: list[str]) -> str:
        return ", ".join(v for v in values if v)
