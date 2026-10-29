"""
Shared test helpers.

FakeRouter stands in for the real LLM router: it replays scripted replies,
so agent tests are fast, free, and give the same result every time.
"""

import pytest

from app.llm.base import LLMResponse
from app.llm.router import RouterResult


class FakeRouter:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.received: list[list] = []        # the messages sent on each call

    def generate(self, system_prompt, messages):
        self.received.append(list(messages))
        return RouterResult(LLMResponse(self.replies.pop(0), "fake", "scripted", 1))


@pytest.fixture
def fake_router():
    return FakeRouter
