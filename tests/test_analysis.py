import io

import pandas as pd
import pytest
import dispatch_assistant.analysis as analysis

from dispatch_assistant.analysis import (
    CSV_COLUMNS,
    CsvValidationError,
    read_dispatch_csv,
    validate_dispatch_frame,
)


def make_valid_frame() -> pd.DataFrame:
    rows = 365
    return pd.DataFrame(
        {
            "时段序号": list(range(1, rows + 1)),
            "水电出力": [70.0] * rows,
            "风光出力": [30.0] * rows,
            "弃风光率（=弃风光量/风光出力）": [0.0] * rows,
            "出力不足率（=出力不足/负荷）": [0.0] * rows,
            "负荷": [100.0] * rows,
            "水电效率": [9.3] * rows,
            "发电流量": [50.0] * rows,
            "弃水率": [0.0] * rows,
            "水量偏差率": [0.0] * rows,
            "计划出库": [55.0] * rows,
            "实际出库": [55.0] * rows,
        }
    )


def test_accepts_fixed_gbk_template() -> None:
    payload = make_valid_frame().to_csv(index=False).encode("gbk")
    loaded = read_dispatch_csv(io.BytesIO(payload))
    assert list(loaded.columns) == list(CSV_COLUMNS)
    assert len(loaded) == 365


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda frame: frame.drop(columns=["负荷"]), "CSV 列名或顺序不符合固定模板"),
        (lambda frame: frame.iloc[:-1].copy(), "CSV 必须包含 365 行日尺度数据"),
        (lambda frame: frame.assign(水电出力="错误值"), "水电出力包含非数值"),
        (lambda frame: frame.assign(负荷=[None] + [100.0] * 364), "负荷包含空值"),
        (
            lambda frame: frame.assign(时段序号=list(range(365, 0, -1))),
            "时段序号必须为连续整数 1-365",
        ),
        (lambda frame: frame.assign(弃水率=[1.1] + [0.0] * 364), "弃水率必须位于 0-1"),
    ],
)
def test_rejects_invalid_csv(mutate, message: str) -> None:
    with pytest.raises(CsvValidationError, match=message):
        validate_dispatch_frame(mutate(make_valid_frame()))


def test_calculates_known_energy_and_shares() -> None:
    result = analysis.analyze_dispatch(make_valid_frame())
    assert result.metrics["load_energy_gwh"] == pytest.approx(876.0)
    assert result.metrics["hydro_energy_gwh"] == pytest.approx(613.2)
    assert result.metrics["wind_solar_energy_gwh"] == pytest.approx(262.8)
    assert result.metrics["hydro_share"] == pytest.approx(0.7)
    assert result.metrics["wind_solar_share"] == pytest.approx(0.3)
    assert result.metrics["max_abs_power_balance_residual_mw"] == pytest.approx(0.0)


def test_detects_all_confirmed_rules_without_recomputing_rates() -> None:
    frame = make_valid_frame()
    frame.loc[0, "出力不足率（=出力不足/负荷）"] = 0.02
    frame.loc[0, "水电出力"] = 68.0
    frame.loc[1, "弃风光率（=弃风光量/风光出力）"] = 0.11
    frame.loc[2, "弃水率"] = 0.11
    frame.loc[3, "水量偏差率"] = -0.11
    frame.loc[4, "水电出力"] = 70.02

    result = analysis.analyze_dispatch(frame)
    rules = {(item.day, item.rule) for item in result.anomalies}
    assert (1, "存在供电不足") in rules
    assert (2, "高弃风光") in rules
    assert (3, "高弃水") in rules
    assert (4, "计划执行偏差较大") in rules
    assert (5, "功率不守恒") in rules
    assert result.metrics["shortage_days"] == 1
    assert result.metrics["high_curtailment_days"] == 1
    assert result.metrics["high_water_discard_days"] == 1
    assert result.metrics["high_water_deviation_days"] == 1
    assert result.metrics["power_balance_anomaly_days"] == 1
