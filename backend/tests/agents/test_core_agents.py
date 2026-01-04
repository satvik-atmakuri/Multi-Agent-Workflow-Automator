import pytest
from unittest.mock import MagicMock, patch
from app.agents.researcher import ResearcherAgent
from app.agents.synthesizer import SynthesizerAgent

def test_researcher_instantiation():
    with patch("app.agents.base.ChatOpenAI"), \
         patch("app.agents.researcher.DuckDuckGoSearchRun"):
        agent = ResearcherAgent()
        assert agent.name == "ResearcherAgent"
        assert agent.search_tool is not None

def test_synthesizer_instantiation():
    with patch("app.agents.base.ChatOpenAI"):
        agent = SynthesizerAgent()
        assert agent.name == "SynthesizerAgent"
