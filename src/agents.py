from dataclasses import dataclass


@dataclass
class AgentSpec:
    name: str
    instructions: str


def build_observer_agent() -> AgentSpec:
    return AgentSpec(name="Observer", instructions="appendix")


def build_query_formulator_agent() -> AgentSpec:
    return AgentSpec(name="QueryFormulator", instructions="appendix")


def build_retriever_agent() -> AgentSpec:
    return AgentSpec(name="Retriever", instructions="appendix")


def build_analyst_agent() -> AgentSpec:
    return AgentSpec(name="Analyst", instructions="appendix")


def build_strategist_agent() -> AgentSpec:
    return AgentSpec(name="Strategist", instructions="appendix")


def build_checker_agent() -> AgentSpec:
    return AgentSpec(name="Checker", instructions="appendix")
