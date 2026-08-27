import importlib

import matplotlib

matplotlib.use("Agg")

from tests.test_analysis import make_valid_frame


def test_builds_five_expected_figures() -> None:
    charts = importlib.import_module("dispatch_assistant.charts")
    figures = charts.build_figures(make_valid_frame())

    assert set(figures) == {"power", "rates", "flows", "water", "coefficient"}
    assert len(figures["power"].axes) == 1
    assert len(figures["rates"].axes) == 2
    assert len(figures["flows"].axes) == 1
    assert len(figures["water"].axes) == 2
    assert len(figures["coefficient"].axes) == 1
