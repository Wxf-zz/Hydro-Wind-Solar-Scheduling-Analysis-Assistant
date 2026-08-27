from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

CSV_COLUMNS = (
    "时段序号",
    "水电出力",
    "风光出力",
    "弃风光率（=弃风光量/风光出力）",
    "出力不足率（=出力不足/负荷）",
    "负荷",
    "水电效率",
    "发电流量",
    "弃水率",
    "水量偏差率",
    "计划出库",
    "实际出库",
)

ZERO_TO_ONE_RATIO_COLUMNS = (
    "弃风光率（=弃风光量/风光出力）",
    "出力不足率（=出力不足/负荷）",
    "弃水率",
)


class CsvValidationError(ValueError):
    """CSV 无法读取或不符合固定模板。"""

    def __init__(self, messages: list[str]):
        self.messages = messages
        super().__init__("；".join(messages))


def _read_source(source: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    if isinstance(source, bytes):
        source = io.BytesIO(source)
    if hasattr(source, "seek"):
        source.seek(0)

    try:
        return pd.read_csv(source, encoding="gbk")
    except UnicodeDecodeError as exc:
        raise CsvValidationError(["CSV 必须使用 GBK 编码。"]) from exc
    except Exception as exc:
        raise CsvValidationError([f"CSV 读取失败：{exc}"]) from exc


def validate_dispatch_frame(frame: pd.DataFrame) -> None:
    """校验固定列、365 个日序、数值完整性和比例范围。"""
    if list(frame.columns) != list(CSV_COLUMNS):
        raise CsvValidationError(
            [
                "CSV 列名或顺序不符合固定模板。"
                f"期望：{list(CSV_COLUMNS)}；实际：{list(frame.columns)}"
            ]
        )
    if len(frame) != 365:
        raise CsvValidationError([f"CSV 必须包含 365 行日尺度数据，实际为 {len(frame)} 行。"])

    errors: list[str] = []
    for column in CSV_COLUMNS:
        if frame[column].isna().any():
            errors.append(f"{column}包含空值。")
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.isna().any():
            errors.append(f"{column}包含非数值。")
            continue
        frame[column] = converted

    if errors:
        raise CsvValidationError(errors)

    expected_days = list(range(1, 366))
    days = frame["时段序号"]
    if not (days.mod(1).eq(0).all() and days.astype(int).tolist() == expected_days):
        raise CsvValidationError(["时段序号必须为连续整数 1-365。"])

    for column in ZERO_TO_ONE_RATIO_COLUMNS:
        if not frame[column].between(0, 1, inclusive="both").all():
            errors.append(f"{column}必须位于 0-1。")
    if not frame["水量偏差率"].between(-1, 1, inclusive="both").all():
        errors.append("水量偏差率必须位于 -1 到 1。")
    if errors:
        raise CsvValidationError(errors)


def read_dispatch_csv(source: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    """按 GBK 读取 CSV，并返回通过固定模板校验的数据。"""
    frame = _read_source(source)
    validate_dispatch_frame(frame)
    return frame


POWER_BALANCE_THRESHOLD_MW = 0.01
HIGH_RATE_THRESHOLD = 0.10


@dataclass(frozen=True)
class Anomaly:
    day: int
    rule: str
    value: float
    threshold: str
    reason: str


@dataclass(frozen=True)
class AnalysisResult:
    frame: pd.DataFrame
    metrics: dict[str, float | int]
    anomalies: list[Anomaly]


def analyze_dispatch(frame: pd.DataFrame) -> AnalysisResult:
    """计算固定指标、功率平衡残差和已确认的五类异常。"""
    validate_dispatch_frame(frame)
    data = frame.copy()
    deficit = data["出力不足率（=出力不足/负荷）"]
    curtailment = data["弃风光率（=弃风光量/风光出力）"]
    water_discard = data["弃水率"]
    water_deviation = data["水量偏差率"]
    residual = (
        data["水电出力"]
        + data["风光出力"]
        + data["负荷"] * deficit
        - data["负荷"]
    )
    data["功率平衡残差_MW"] = residual

    hydro_energy = float(data["水电出力"].sum() * 24 / 1000)
    wind_solar_energy = float(data["风光出力"].sum() * 24 / 1000)
    grid_energy = hydro_energy + wind_solar_energy
    metrics: dict[str, float | int] = {
        "load_energy_gwh": float(data["负荷"].sum() * 24 / 1000),
        "hydro_energy_gwh": hydro_energy,
        "wind_solar_energy_gwh": wind_solar_energy,
        "hydro_share": hydro_energy / grid_energy,
        "wind_solar_share": wind_solar_energy / grid_energy,
        "shortage_energy_gwh": float((data["负荷"] * deficit).sum() * 24 / 1000),
        "shortage_days": int(deficit.gt(0).sum()),
        "max_shortage_rate": float(deficit.max()),
        "mean_curtailment_rate": float(curtailment.mean()),
        "max_curtailment_rate": float(curtailment.max()),
        "high_curtailment_days": int(curtailment.gt(HIGH_RATE_THRESHOLD).sum()),
        "mean_water_discard_rate": float(water_discard.mean()),
        "max_water_discard_rate": float(water_discard.max()),
        "high_water_discard_days": int(water_discard.gt(HIGH_RATE_THRESHOLD).sum()),
        "mean_hydro_coefficient": float(data["水电效率"].mean()),
        "mean_generation_flow": float(data["发电流量"].mean()),
        "mean_planned_outflow": float(data["计划出库"].mean()),
        "mean_actual_outflow": float(data["实际出库"].mean()),
        "mean_water_deviation_rate": float(water_deviation.mean()),
        "max_abs_water_deviation_rate": float(water_deviation.abs().max()),
        "high_water_deviation_days": int(water_deviation.abs().gt(HIGH_RATE_THRESHOLD).sum()),
        "max_abs_power_balance_residual_mw": float(residual.abs().max()),
        "power_balance_anomaly_days": int(
            residual.abs().gt(POWER_BALANCE_THRESHOLD_MW).sum()
        ),
    }

    anomalies: list[Anomaly] = []
    for _, row in data.iterrows():
        day = int(row["时段序号"])
        checks = (
            (
                abs(row["功率平衡残差_MW"]) > POWER_BALANCE_THRESHOLD_MW,
                "功率不守恒",
                abs(row["功率平衡残差_MW"]),
                "0.01 MW",
                "功率平衡绝对残差超过阈值",
            ),
            (
                row["出力不足率（=出力不足/负荷）"] > 0,
                "存在供电不足",
                row["出力不足率（=出力不足/负荷）"],
                "> 0",
                "模型结果显示当日存在供电不足",
            ),
            (
                row["弃风光率（=弃风光量/风光出力）"] > HIGH_RATE_THRESHOLD,
                "高弃风光",
                row["弃风光率（=弃风光量/风光出力）"],
                "10%",
                "弃风光率超过 MVP 阈值",
            ),
            (
                row["弃水率"] > HIGH_RATE_THRESHOLD,
                "高弃水",
                row["弃水率"],
                "10%",
                "弃水率超过 MVP 阈值",
            ),
            (
                abs(row["水量偏差率"]) > HIGH_RATE_THRESHOLD,
                "计划执行偏差较大",
                abs(row["水量偏差率"]),
                "10%",
                "水量偏差率绝对值超过 MVP 阈值",
            ),
        )
        for triggered, rule, value, threshold, reason in checks:
            if triggered:
                anomalies.append(Anomaly(day, rule, float(value), threshold, reason))

    metrics["total_anomaly_records"] = len(anomalies)
    return AnalysisResult(data, metrics, anomalies)
