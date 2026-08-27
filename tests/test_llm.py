import importlib
from types import SimpleNamespace

import pytest

from dispatch_assistant.knowledge import Evidence


class FakeCompletions:
    def __init__(self, content: str | None):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class RaisingCompletions:
    def create(self, **kwargs):
        raise ConnectionError("模拟网络故障")


def make_client(content: str | None):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def make_evidence() -> list[Evidence]:
    return [
        Evidence(
            "KB-002",
            "Test Source",
            10,
            "Power balance and water balance constraints.",
            0.8,
        )
    ]


def test_abstains_without_evidence_and_does_not_call_api() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client, completions = make_client("不应被使用")

    answer = llm.answer_question("无依据问题", [], client=client)

    assert answer == "当前知识库没有足够依据回答这个问题。"
    assert completions.kwargs is None


def test_requires_environment_key_when_evidence_exists(monkeypatch) -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(llm.DeepSeekError, match="DEEPSEEK_API_KEY"):
        llm.answer_question("什么是功率平衡？", make_evidence(), client=None)


def test_calls_current_deepseek_model_with_thinking_disabled() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client, completions = make_client("功率平衡用于约束供需关系。[KB-002, p.10]")

    answer = llm.answer_question("什么是功率平衡？", make_evidence(), client=client)

    assert "[KB-002, p.10]" in answer
    assert llm.BASE_URL == "https://api.deepseek.com"
    assert completions.kwargs["model"] == "deepseek-v4-flash"
    assert completions.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "Power balance and water balance constraints." in completions.kwargs["messages"][1]["content"]


def test_rejects_unretrieved_citation() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client, _ = make_client("结论。[KB-001, p.4]")

    with pytest.raises(llm.GroundingError, match="未检索到的来源"):
        llm.answer_question("问题", make_evidence(), client=client)


def test_rejects_answer_without_citation() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client, _ = make_client("这是一个没有来源的结论。")

    with pytest.raises(llm.GroundingError, match="没有按要求显示来源"):
        llm.answer_question("问题", make_evidence(), client=client)


def test_rejects_empty_model_content() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client, _ = make_client(None)

    with pytest.raises(llm.DeepSeekError, match="返回了空内容"):
        llm.answer_question("问题", make_evidence(), client=client)


def test_wraps_api_failure_without_retrying() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client = SimpleNamespace(chat=SimpleNamespace(completions=RaisingCompletions()))

    with pytest.raises(llm.DeepSeekError, match="DeepSeek API 调用失败"):
        llm.answer_question("问题", make_evidence(), client=client)
