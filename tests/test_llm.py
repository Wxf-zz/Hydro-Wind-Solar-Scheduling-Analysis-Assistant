import importlib
from types import SimpleNamespace

import pytest

from dispatch_assistant.knowledge import Evidence


CONFIG_ENV_NAMES = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DEEPSEEK_API_KEY",
)


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
    for name in CONFIG_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(llm.LLMError, match="LLM_API_KEY"):
        llm.answer_question("什么是功率平衡？", make_evidence(), client=None)


def test_supports_generic_openai_compatible_provider(monkeypatch) -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    for name in CONFIG_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "example-model")
    client, completions = make_client("功率平衡用于约束供需关系。[KB-002, p.10]")
    created_kwargs = {}

    def fake_openai(**kwargs):
        created_kwargs.update(kwargs)
        return client

    monkeypatch.setattr(llm, "OpenAI", fake_openai)

    answer = llm.answer_question("什么是功率平衡？", make_evidence())

    assert "[KB-002, p.10]" in answer
    assert created_kwargs == {"api_key": "test-key", "base_url": "https://example.test/v1"}
    assert completions.kwargs["model"] == "example-model"
    assert "extra_body" not in completions.kwargs
    assert "Power balance and water balance constraints." in completions.kwargs["messages"][1]["content"]


def test_deepseek_shortcut_keeps_default_settings(monkeypatch) -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    for name in CONFIG_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    client, completions = make_client("功率平衡用于约束供需关系。[KB-002, p.10]")
    monkeypatch.setattr(llm, "OpenAI", lambda **kwargs: client)

    llm.answer_question("什么是功率平衡？", make_evidence())

    assert completions.kwargs["model"] == llm.DEFAULT_DEEPSEEK_MODEL
    assert completions.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


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

    with pytest.raises(llm.LLMError, match="返回了空内容"):
        llm.answer_question("问题", make_evidence(), client=client)


def test_wraps_api_failure_without_retrying() -> None:
    llm = importlib.import_module("dispatch_assistant.llm")
    client = SimpleNamespace(chat=SimpleNamespace(completions=RaisingCompletions()))

    with pytest.raises(llm.LLMError, match="大模型 API 调用失败"):
        llm.answer_question("问题", make_evidence(), client=client)
