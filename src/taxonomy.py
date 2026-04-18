from __future__ import annotations

from typing import Literal

ScenarioType = Literal["affection", "stance", "intent"]
MechanismType = str
LabelType = str

SCENARIO_MECHANISM_OPTIONS: dict[ScenarioType, list[MechanismType]] = {
    "affection": [],
    "stance": [],
    "intent": [],
}

SCENARIO_LABEL_OPTIONS: dict[ScenarioType, list[LabelType]] = {
    "affection": [],
    "stance": [],
    "intent": [],
}

MECHANISM_DEFINITIONS: dict[MechanismType, str] = {}

LABEL_DEFINITIONS: dict[LabelType, str] = {}
