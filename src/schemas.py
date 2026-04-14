from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ScenarioType = Literal["affection", "intent", "stance"]
MechanismType = str
LabelType = str

SCENARIO_MECHANISM_OPTIONS: dict[ScenarioType, list[MechanismType]] = {
    "affection": [],
    "intent": [],
    "stance": [],
}

SCENARIO_LABEL_OPTIONS: dict[ScenarioType, list[LabelType]] = {
    "affection": [],
    "intent": [],
    "stance": [],
}


@dataclass
class MediaPayload:
    url: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    description: str | None = None
    audio_caption: str | None = None

    @classmethod
    def model_validate(cls, data: dict[str, Any] | None) -> "MediaPayload":
        if not isinstance(data, dict):
            return cls()
        return cls(
            url=data.get("url") if isinstance(data.get("url"), str) else None,
            image_url=data.get("image_url") if isinstance(data.get("image_url"), str) else None,
            video_url=data.get("video_url") if isinstance(data.get("video_url"), str) else None,
            description=data.get("description") if isinstance(data.get("description"), str) else None,
            audio_caption=data.get("audio_caption") if isinstance(data.get("audio_caption"), str) else None,
        )

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class CaseInput:
    scenario: ScenarioType
    text: str
    media: MediaPayload | None = None

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "CaseInput":
        if not isinstance(data, dict):
            raise ValueError("input must be an object")
        scenario = data.get("scenario")
        if scenario not in ("affection", "intent", "stance"):
            raise ValueError("scenario must be affection, intent, or stance")
        text = data.get("text") if isinstance(data.get("text"), str) else ""
        return cls(scenario=scenario, text=text, media=MediaPayload.model_validate(data.get("media")))

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return {
            "scenario": self.scenario,
            "text": self.text,
            "media": self.media.model_dump() if self.media else None,
        }


@dataclass
class CandidateOptions:
    subject: list[str] = field(default_factory=list)
    target: list[str] = field(default_factory=list)

    @classmethod
    def model_validate(cls, data: dict[str, Any] | None) -> "CandidateOptions":
        if not isinstance(data, dict):
            return cls()
        subject = data.get("subject") if isinstance(data.get("subject"), list) else []
        target = data.get("target") if isinstance(data.get("target"), list) else []
        return cls(
            subject=[x for x in subject if isinstance(x, str)],
            target=[x for x in target if isinstance(x, str)],
        )

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class GroundTruth:
    subject: str | None = None
    target: str | None = None
    mechanism: str | None = None
    label: str | None = None

    @classmethod
    def model_validate(cls, data: dict[str, Any] | None) -> "GroundTruth":
        if not isinstance(data, dict):
            return cls()
        return cls(
            subject=data.get("subject") if isinstance(data.get("subject"), str) else None,
            target=data.get("target") if isinstance(data.get("target"), str) else None,
            mechanism=data.get("mechanism") if isinstance(data.get("mechanism"), str) else None,
            label=data.get("label") if isinstance(data.get("label"), str) else None,
        )

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class ReasoningCase:
    case_id: str
    input: CaseInput
    options: CandidateOptions = field(default_factory=CandidateOptions)
    ground_truth: GroundTruth | None = None

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "ReasoningCase":
        if not isinstance(data, dict):
            raise ValueError("case must be an object")
        case_id = data.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("id must be a non-empty string")
        return cls(
            case_id=case_id,
            input=CaseInput.model_validate(data.get("input", {})),
            options=CandidateOptions.model_validate(data.get("options")),
            ground_truth=GroundTruth.model_validate(data.get("ground_truth")),
        )

    @property
    def allowed_mechanisms(self) -> list[MechanismType]:
        return SCENARIO_MECHANISM_OPTIONS[self.input.scenario]

    @property
    def allowed_labels(self) -> list[LabelType]:
        return SCENARIO_LABEL_OPTIONS[self.input.scenario]

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        payload = {
            "id": self.case_id,
            "input": self.input.model_dump(),
            "options": self.options.model_dump(),
            "ground_truth": self.ground_truth.model_dump() if self.ground_truth else None,
        }
        if by_alias:
            return payload
        return {
            "case_id": self.case_id,
            "input": self.input.model_dump(),
            "options": self.options.model_dump(),
            "ground_truth": self.ground_truth.model_dump() if self.ground_truth else None,
        }


@dataclass
class ExplicitRepresentation:
    text_cues: list[str] = field(default_factory=list)
    static_visual_cues: list[str] = field(default_factory=list)
    temporal_visual_cues: list[str] = field(default_factory=list)
    speech_transcript: str = ""
    caption: str = ""

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class RetrievalQuestion:
    question: str
    source_preference: Literal["model_prior", "web_search", "hybrid"] = "hybrid"

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class QueryFormulation:
    retrieval_questions: list[RetrievalQuestion] = field(default_factory=list)

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return {"retrieval_questions": [q.model_dump() for q in self.retrieval_questions]}


@dataclass
class SearchSnippet:
    query: str = ""
    title: str = ""
    url: str = ""
    snippet: str = ""

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class ContextPacket:
    fact: list[str] = field(default_factory=list)
    connection: list[str] = field(default_factory=list)
    social_norm: list[str] = field(default_factory=list)

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class ConflictAnalysis:
    context_expectation: str = ""
    explicit_reality: str = ""
    conflict_statement: str = ""
    conflict: str = ""
    conflict_type: str = ""
    abductive_question: str = ""

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class MechanismDecision:
    label: LabelType = ""
    subject: str = ""
    target: str = ""
    mechanism: MechanismType = ""
    hidden_meaning: str = ""
    counterfactual_cost: list[str] = field(default_factory=list)
    conflict_utility: list[str] = field(default_factory=list)
    out_of_frame_inference: list[str] = field(default_factory=list)

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class ConsistencyCheck:
    explicit_evidence_alignment: bool = True
    context_alignment: bool = True
    mechanism_alignment: bool = True
    status: Literal["ACCEPTED", "REJECTED"] = "ACCEPTED"
    verification_note: str = ""

    @property
    def failed_checks(self) -> list[str]:
        failed: list[str] = []
        if not self.explicit_evidence_alignment:
            failed.append("explicit_evidence_alignment")
        if not self.context_alignment:
            failed.append("context_alignment")
        if not self.mechanism_alignment:
            failed.append("mechanism_alignment")
        return failed

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return asdict(self)


@dataclass
class FinalReasoningResult:
    case: ReasoningCase
    explicit_representation: ExplicitRepresentation
    context_packet: ContextPacket
    conflict_analysis: ConflictAnalysis
    mechanism_decision: MechanismDecision
    consistency_check: ConsistencyCheck
    accepted: bool = True
    reasoning_chain: list[str] = field(default_factory=list)
    final_explanation: str = ""

    def model_dump(self, by_alias: bool = False) -> dict[str, Any]:
        del by_alias
        return {
            "case": self.case.model_dump(by_alias=True),
            "explicit_representation": self.explicit_representation.model_dump(),
            "context_packet": self.context_packet.model_dump(),
            "conflict_analysis": self.conflict_analysis.model_dump(),
            "mechanism_decision": self.mechanism_decision.model_dump(),
            "consistency_check": self.consistency_check.model_dump(),
            "accepted": self.accepted,
            "reasoning_chain": self.reasoning_chain,
            "final_explanation": self.final_explanation,
        }
