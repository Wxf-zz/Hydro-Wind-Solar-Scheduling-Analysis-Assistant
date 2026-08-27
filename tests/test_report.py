import importlib
from types import SimpleNamespace

import pytest

from dispatch_assistant.analysis import analyze_dispatch
from dispatch_assistant.knowledge import Evidence
from tests.test_analysis import make_valid_frame


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        response = SimpleNamespace(message=SimpleNamespace(content=self.content))
        return SimpleNamespace(choices=[response])


def make_client(content: str):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def make_evidence() -> list[Evidence]:
    return [Evidence("KB-002", "Test Source", 10, "Power balance constraint.", 0.8)]


def test_report_uses_python_metrics_and_expected_sections() -> None:
    report_module = importlib.import_module("dispatch_assistant.report")
    result = analyze_dispatch(make_valid_frame())

    report = report_module.render_report(
        result,
        make_evidence(),
        "系统供需整体协调，水电承担调节作用。",
    )

    assert "# 水风光调度分析报告" in report
    assert "876.000 GWh" in report
    assert "613.200 GWh" in report
    assert "## 异常清单" in report
    assert "[KB-002, p.10]" in report


@pytest.mark.parametrize("commentary", ["模型自行写入了 99%。", "模型写入了百分号％。"])
def test_rejects_numbers_or_percent_symbols_generated_by_model(commentary: str) -> None:
    report_module = importlib.import_module("dispatch_assistant.report")
    result = analyze_dispatch(make_valid_frame())

    with pytest.raises(report_module.ReportValidationError, match="不得包含数字或百分号"):
        report_module.render_report(result, make_evidence(), commentary)


def test_formats_anomaly_values_with_consistent_units() -> None:
    report_module = importlib.import_module("dispatch_assistant.report")
    frame = make_valid_frame()
    frame.loc[0, "出力不足率（=出力不足/负荷）"] = 0.02
    frame.loc[0, "水电出力"] = 68.0
    frame.loc[1, "弃风光率（=弃风光量/风光出力）"] = 0.11
    frame.loc[4, "水电出力"] = 70.02
    frame.loc[5, "出力不足率（=出力不足/负荷）"] = 0.000001
    frame.loc[5, "水电出力"] = 69.9999

    report = report_module.render_report(
        analyze_dispatch(frame),
        make_evidence(),
        "系统运行特征存在差异。",
    )

    assert "| 1 | 存在供电不足 | 2.0000% | > 0 |" in report
    assert "| 2 | 高弃风光 | 11.00% | 10% |" in report
    assert "| 5 | 功率不守恒 | 0.020000 MW | 0.01 MW |" in report
    assert "| 6 | 存在供电不足 | 0.0001% | > 0 |" in report


def test_generate_report_accepts_qualitative_model_text() -> None:
    report_module = importlib.import_module("dispatch_assistant.report")
    result = analyze_dispatch(make_valid_frame())
    client, completions = make_client("系统整体供需协调。")

    report = report_module.generate_report(
        result,
        make_evidence(),
        client=client,
    )

    assert "系统整体供需协调。" in report
    assert completions.kwargs["max_tokens"] == 500
