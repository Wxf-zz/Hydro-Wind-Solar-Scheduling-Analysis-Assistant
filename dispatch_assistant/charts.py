from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "font.size": 10,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.unicode_minus": False,
        "legend.frameon": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)


def _finish(fig: Figure) -> Figure:
    fig.tight_layout()
    return fig


def build_figures(frame: pd.DataFrame) -> dict[str, Figure]:
    """使用全部日尺度数据构建五组固定分析图表。"""
    day = frame["时段序号"]

    power, ax = plt.subplots(figsize=(10, 4))
    ax.stackplot(
        day,
        frame["水电出力"],
        frame["风光出力"],
        labels=["水电出力", "风光出力"],
        colors=["#4C78A8", "#F2CF5B"],
        alpha=0.85,
    )
    ax.plot(day, frame["负荷"], color="#222222", linewidth=1.2, label="负荷")
    ax.set(xlabel="日序号", ylabel="功率（MW）", title="全年出力与负荷")
    ax.legend(loc="upper right", ncol=3)

    rates, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(day, frame["弃风光率（=弃风光量/风光出力）"] * 100, color="#4C78A8")
    axes[0].axhline(10, color="#D9534F", linestyle="--", linewidth=1, label="10% 阈值")
    axes[0].set(ylabel="比例（%）", title="弃风光率")
    axes[0].legend()
    axes[1].plot(day, frame["出力不足率（=出力不足/负荷）"] * 100, color="#D9534F")
    axes[1].set(xlabel="日序号", ylabel="比例（%）", title="出力不足率")

    flows, ax = plt.subplots(figsize=(10, 4))
    ax.plot(day, frame["发电流量"], label="发电流量", color="#4C78A8")
    ax.plot(day, frame["计划出库"], label="计划出库", color="#72B7B2")
    ax.plot(day, frame["实际出库"], label="实际出库", color="#E45756", linestyle="--")
    ax.set(xlabel="日序号", ylabel="流量（m³/s）", title="流量过程")
    ax.legend()

    water, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(day, frame["弃水率"] * 100, color="#4C78A8")
    axes[0].axhline(10, color="#D9534F", linestyle="--", linewidth=1, label="10% 阈值")
    axes[0].set(ylabel="比例（%）", title="弃水率")
    axes[0].legend()
    axes[1].plot(day, frame["水量偏差率"] * 100, color="#72B7B2")
    axes[1].axhline(10, color="#D9534F", linestyle="--", linewidth=1)
    axes[1].axhline(-10, color="#D9534F", linestyle="--", linewidth=1)
    axes[1].set(xlabel="日序号", ylabel="比例（%）", title="水量偏差率")

    coefficient, ax = plt.subplots(figsize=(10, 4))
    ax.plot(day, frame["水电效率"], color="#4C78A8")
    ax.set(
        xlabel="日序号",
        ylabel="K（kW/[(m³/s)·m]）",
        title="水电出力系数 K",
    )

    return {
        "power": _finish(power),
        "rates": _finish(rates),
        "flows": _finish(flows),
        "water": _finish(water),
        "coefficient": _finish(coefficient),
    }
