from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_starts_and_waits_for_csv() -> None:
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run(timeout=30)

    assert len(app.exception) == 0
    assert app.title[0].value == "水风光调度智能分析助手"
    assert any("请先上传调度结果 CSV" in item.value for item in app.info)
