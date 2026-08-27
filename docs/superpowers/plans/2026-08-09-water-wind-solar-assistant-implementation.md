# 水风光调度智能分析助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可在 Windows 本地启动的 Streamlit MVP，完成固定 CSV 校验与分析、带来源的专业问答和结构化 Markdown 报告下载。

**Architecture:** 使用单体 Streamlit 页面串联完整任务流；所有数值计算、图表、异常判断和知识检索都在本地完成。DeepSeek 只接收完成当前问答或报告所需的证据和结构化结果，不能计算或修改指标。

**Tech Stack:** Python 3.12、Streamlit、pandas、matplotlib、pypdf、scikit-learn、OpenAI Python SDK（连接 DeepSeek OpenAI-compatible API）、pytest。

## Global Constraints

- 只支持 `AAA_original.csv` 已确认的 12 列、GBK 编码、365 个日尺度时段；不实现任意 CSV 字段映射。
- 四个比率字段在内部保持 0-1 小数，只在界面、图表和报告中显示为百分比。
- 不重新计算弃风光率、出力不足率、弃水率和水量偏差率；这些列是模型结果。
- 功率平衡残差为 `水电出力 + 风光出力 + 负荷 × 出力不足率 - 负荷`。
- 异常规则固定为：功率平衡绝对残差 `> 0.01 MW`；出力不足率 `> 0`；弃风光率 `> 10%`；弃水率 `> 10%`；水量偏差率绝对值 `> 10%`。
- 水电出力系数 K 只做统计和趋势展示，不设置异常阈值；CSV 列名仍接受 `水电效率`，界面显示为“水电出力系数 K”。
- 知识库只使用 `knowledge_base/sources/` 中已批准的两篇公开论文；运行时不联网搜索、不上传任意 PDF。
- 中文检索标签只参与召回，不作为证据；回答引用必须来自 PDF 原文并显示资料编号和页码。
- DeepSeek 使用 `https://api.deepseek.com`、`deepseek-v4-flash`，通过 `extra_body={"thinking": {"type": "disabled"}}` 关闭思考模式；参数以 [DeepSeek 官方 Chat Completion 文档](https://api-docs.deepseek.com/api/create-chat-completion)为准。
- API 密钥只从 `DEEPSEEK_API_KEY` 环境变量读取，不写入代码、文档、截图、测试或 Git。
- 不使用 LangChain、向量数据库、Agent 框架、数据库、前后端分离或异步任务队列。
- 每个任务遵循 TDD：先写失败测试，再写最小实现；每个任务单独提交。
- 测试夹具是明确标注的人工单元测试输入，不代表真实调度数据、用户反馈或性能结果。

---

## Planned File Map

| 路径 | 单一职责 |
| --- | --- |
| `.gitignore` | 排除虚拟环境、缓存、密钥文件和本地输出 |
| `requirements.txt` | 声明 MVP 的最少运行与测试依赖 |
| `app.py` | Streamlit 页面和主流程编排 |
| `dispatch_assistant/__init__.py` | Python 包入口 |
| `dispatch_assistant/analysis.py` | CSV 契约、校验、指标和异常规则 |
| `dispatch_assistant/charts.py` | 五组固定 matplotlib 图表 |
| `dispatch_assistant/knowledge.py` | PDF 抽取、分页切块、TF-IDF 索引与检索 |
| `dispatch_assistant/llm.py` | DeepSeek 调用、问答提示词与引用校验 |
| `dispatch_assistant/report.py` | 确定性 Markdown 组装和定性解读校验 |
| `tests/test_analysis.py` | CSV、指标和异常规则测试 |
| `tests/test_charts.py` | 图表集合和子图结构测试 |
| `tests/test_knowledge.py` | 两篇论文的中文检索与拒答测试 |
| `tests/test_llm.py` | 无密钥、无证据、请求参数和引用约束测试 |
| `tests/test_report.py` | 报告数值一致性和定性解读约束测试 |
| `docs/test-results.md` | 只记录实际执行过的测试命令、结果和计时 |

---

### Task 1: 固定 CSV 契约与错误反馈

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `dispatch_assistant/__init__.py`
- Create: `dispatch_assistant/analysis.py`
- Create: `tests/test_analysis.py`

**Interfaces:**
- Consumes: GBK 编码的路径、字节流或 Streamlit UploadedFile。
- Produces: `read_dispatch_csv(source) -> pandas.DataFrame`；失败时抛出 `CsvValidationError(messages: list[str])`。

- [ ] **Step 1: 建立最小环境文件**

`.gitignore` 写入：

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.py[cod]
.env
.streamlit/secrets.toml
outputs/
```

`requirements.txt` 写入：

```text
streamlit>=1.40,<2
pandas>=2.2,<3
matplotlib>=3.9,<4
pypdf>=5,<7
scikit-learn>=1.5,<2
openai>=1.60,<3
pytest>=8,<10
```

`dispatch_assistant/__init__.py` 写入：

```python
"""水风光调度智能分析助手。"""
```

创建环境并安装依赖：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: 两条命令退出码均为 0，且不要求输入任何 API 密钥。

- [ ] **Step 2: 写 CSV 契约的失败测试**

`tests/test_analysis.py` 写入：

```python
import io

import pandas as pd
import pytest

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
        (lambda frame: frame.assign(时段序号=list(range(365, 0, -1))), "时段序号必须为连续整数 1-365"),
        (lambda frame: frame.assign(弃水率=[1.1] + [0.0] * 364), "弃水率必须位于 0-1"),
    ],
)
def test_rejects_invalid_csv(mutate, message: str) -> None:
    with pytest.raises(CsvValidationError, match=message):
        validate_dispatch_frame(mutate(make_valid_frame()))
```

- [ ] **Step 3: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -q`

Expected: collection error，提示 `dispatch_assistant.analysis` 不存在。

- [ ] **Step 4: 写最小 CSV 读取与校验实现**

`dispatch_assistant/analysis.py` 写入：

```python
from __future__ import annotations

import io
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

RATIO_COLUMNS = (
    "弃风光率（=弃风光量/风光出力）",
    "出力不足率（=出力不足/负荷）",
    "弃水率",
    "水量偏差率",
)


class CsvValidationError(ValueError):
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
        raise CsvValidationError(["CSV 必须使用 GBK 编码。"] ) from exc
    except Exception as exc:
        raise CsvValidationError([f"CSV 读取失败：{exc}"]) from exc


def validate_dispatch_frame(frame: pd.DataFrame) -> None:
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

    for column in RATIO_COLUMNS:
        if not frame[column].between(0, 1, inclusive="both").all() and column != "水量偏差率":
            errors.append(f"{column}必须位于 0-1。")
    if not frame["水量偏差率"].between(-1, 1, inclusive="both").all():
        errors.append("水量偏差率必须位于 -1 到 1。")
    if errors:
        raise CsvValidationError(errors)


def read_dispatch_csv(source: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    frame = _read_source(source)
    validate_dispatch_frame(frame)
    return frame
```

- [ ] **Step 5: 运行测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -q`

Expected: `7 passed`。

- [ ] **Step 6: 提交任务**

```powershell
git add .gitignore requirements.txt dispatch_assistant tests/test_analysis.py
git commit -m "feat: validate fixed dispatch csv"
```

---

### Task 2: 指标计算、功率守恒和异常规则

**Files:**
- Modify: `dispatch_assistant/analysis.py`
- Modify: `tests/test_analysis.py`

**Interfaces:**
- Consumes: 已通过 `validate_dispatch_frame` 的 DataFrame。
- Produces: `analyze_dispatch(frame) -> AnalysisResult`，其中包含新增残差列、指标字典和逐条异常记录。

- [ ] **Step 1: 追加失败测试**

在 `tests/test_analysis.py` 追加：

```python
from dispatch_assistant.analysis import analyze_dispatch


def test_calculates_known_energy_and_shares() -> None:
    result = analyze_dispatch(make_valid_frame())
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

    result = analyze_dispatch(frame)
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -q`

Expected: import error，提示 `analyze_dispatch` 不存在。

- [ ] **Step 3: 实现确定性分析**

在 `dispatch_assistant/analysis.py` 顶部增加 `from dataclasses import dataclass`，并在文件末尾追加：

```python
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
        "power_balance_anomaly_days": int(residual.abs().gt(POWER_BALANCE_THRESHOLD_MW).sum()),
    }

    anomalies: list[Anomaly] = []
    for row_index, row in data.iterrows():
        day = int(row["时段序号"])
        checks = (
            (abs(row["功率平衡残差_MW"]) > POWER_BALANCE_THRESHOLD_MW, "功率不守恒", abs(row["功率平衡残差_MW"]), "0.01 MW", "功率平衡绝对残差超过阈值"),
            (row["出力不足率（=出力不足/负荷）"] > 0, "存在供电不足", row["出力不足率（=出力不足/负荷）"], "> 0", "模型结果显示当日存在供电不足"),
            (row["弃风光率（=弃风光量/风光出力）"] > HIGH_RATE_THRESHOLD, "高弃风光", row["弃风光率（=弃风光量/风光出力）"], "10%", "弃风光率超过 MVP 阈值"),
            (row["弃水率"] > HIGH_RATE_THRESHOLD, "高弃水", row["弃水率"], "10%", "弃水率超过 MVP 阈值"),
            (abs(row["水量偏差率"]) > HIGH_RATE_THRESHOLD, "计划执行偏差较大", abs(row["水量偏差率"]), "10%", "水量偏差率绝对值超过 MVP 阈值"),
        )
        for triggered, rule, value, threshold, reason in checks:
            if triggered:
                anomalies.append(Anomaly(day, rule, float(value), threshold, reason))

    metrics["total_anomaly_records"] = len(anomalies)
    return AnalysisResult(data, metrics, anomalies)
```

- [ ] **Step 4: 运行分析测试**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -q`

Expected: `9 passed`。

- [ ] **Step 5: 用获准 CSV 做只读基线核验**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from dispatch_assistant.analysis import read_dispatch_csv,analyze_dispatch; r=analyze_dispatch(read_dispatch_csv('AAA_original.csv')); print(len(r.frame),r.metrics['power_balance_anomaly_days'],r.metrics['shortage_days'],r.metrics['high_curtailment_days'],r.metrics['high_water_discard_days'],r.metrics['high_water_deviation_days'])"
```

Expected: `365 0 8 15 13 30`。若不一致，停止并读取完整输出，不调整阈值来迎合预期。

- [ ] **Step 6: 提交任务**

```powershell
git add dispatch_assistant/analysis.py tests/test_analysis.py
git commit -m "feat: calculate dispatch metrics and anomalies"
```

---

### Task 3: 五组固定分析图表

**Files:**
- Create: `dispatch_assistant/charts.py`
- Create: `tests/test_charts.py`

**Interfaces:**
- Consumes: `AnalysisResult.frame`。
- Produces: `build_figures(frame) -> dict[str, matplotlib.figure.Figure]`，键固定为 `power`、`rates`、`flows`、`water`、`coefficient`。

- [ ] **Step 1: 写失败测试**

`tests/test_charts.py` 写入：

```python
import matplotlib

matplotlib.use("Agg")

from dispatch_assistant.charts import build_figures
from tests.test_analysis import make_valid_frame


def test_builds_five_expected_figures() -> None:
    figures = build_figures(make_valid_frame())
    assert set(figures) == {"power", "rates", "flows", "water", "coefficient"}
    assert len(figures["power"].axes) == 1
    assert len(figures["rates"].axes) == 2
    assert len(figures["flows"].axes) == 1
    assert len(figures["water"].axes) == 2
    assert len(figures["coefficient"].axes) == 1
```

同时创建空文件 `tests/__init__.py`，使测试辅助函数可导入。

- [ ] **Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_charts.py -q`

Expected: import error，提示 `dispatch_assistant.charts` 不存在。

- [ ] **Step 3: 实现固定图表**

`dispatch_assistant/charts.py` 写入：

```python
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _finish(fig: Figure) -> Figure:
    fig.tight_layout()
    return fig


def build_figures(frame: pd.DataFrame) -> dict[str, Figure]:
    day = frame["时段序号"]

    power, ax = plt.subplots(figsize=(10, 4))
    ax.stackplot(day, frame["水电出力"], frame["风光出力"], labels=["水电出力", "风光出力"])
    ax.plot(day, frame["负荷"], color="black", linewidth=1.2, label="负荷")
    ax.set(xlabel="日序号", ylabel="MW", title="全年出力与负荷")
    ax.legend(loc="upper right")

    rates, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(day, frame["弃风光率（=弃风光量/风光出力）"] * 100)
    axes[0].axhline(10, color="red", linestyle="--", label="10% 阈值")
    axes[0].set(ylabel="%", title="弃风光率")
    axes[0].legend()
    axes[1].plot(day, frame["出力不足率（=出力不足/负荷）"] * 100)
    axes[1].set(xlabel="日序号", ylabel="%", title="出力不足率")

    flows, ax = plt.subplots(figsize=(10, 4))
    ax.plot(day, frame["发电流量"], label="发电流量")
    ax.plot(day, frame["计划出库"], label="计划出库")
    ax.plot(day, frame["实际出库"], label="实际出库")
    ax.set(xlabel="日序号", ylabel="m³/s", title="流量过程")
    ax.legend()

    water, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(day, frame["弃水率"] * 100)
    axes[0].axhline(10, color="red", linestyle="--", label="10% 阈值")
    axes[0].set(ylabel="%", title="弃水率")
    axes[0].legend()
    axes[1].plot(day, frame["水量偏差率"] * 100)
    axes[1].axhline(10, color="red", linestyle="--")
    axes[1].axhline(-10, color="red", linestyle="--")
    axes[1].set(xlabel="日序号", ylabel="%", title="水量偏差率")

    coefficient, ax = plt.subplots(figsize=(10, 4))
    ax.plot(day, frame["水电效率"])
    ax.set(xlabel="日序号", ylabel="kW/[(m³/s)·m]", title="水电出力系数 K")

    return {
        "power": _finish(power),
        "rates": _finish(rates),
        "flows": _finish(flows),
        "water": _finish(water),
        "coefficient": _finish(coefficient),
    }
```

- [ ] **Step 4: 运行图表及全部测试**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: `10 passed`，无 GUI 窗口弹出。

- [ ] **Step 5: 提交任务**

```powershell
git add dispatch_assistant/charts.py tests/__init__.py tests/test_charts.py
git commit -m "feat: add fixed dispatch charts"
```

---

### Task 4: 本地 PDF 检索与可定位证据

**Files:**
- Create: `dispatch_assistant/knowledge.py`
- Create: `tests/test_knowledge.py`

**Interfaces:**
- Consumes: `knowledge_base/sources/` 中两份固定 PDF 和中文问题。
- Produces: `build_knowledge_index(source_dir) -> KnowledgeIndex`；`KnowledgeIndex.retrieve(query, top_k=4, min_score=0.05) -> list[Evidence]`。

- [ ] **Step 1: 写真实资料检索的失败测试**

`tests/test_knowledge.py` 写入：

```python
from pathlib import Path

from dispatch_assistant.knowledge import build_knowledge_index


def test_retrieves_power_and_water_balance_page() -> None:
    index = build_knowledge_index(Path("knowledge_base/sources"))
    evidence = index.retrieve("功率平衡和水量平衡约束是什么", top_k=3)
    assert any(item.source_id == "KB-002" and item.page == 10 for item in evidence)


def test_retrieves_complementarity_pages_for_chinese_query() -> None:
    index = build_knowledge_index(Path("knowledge_base/sources"))
    evidence = index.retrieve("水电怎样补偿风电和光伏波动", top_k=4)
    assert any(item.source_id == "KB-002" and item.page in {7, 9, 16} for item in evidence)


def test_returns_empty_for_unrelated_query() -> None:
    index = build_knowledge_index(Path("knowledge_base/sources"))
    assert index.retrieve("蛋白质折叠与药物分子动力学", min_score=0.05) == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge.py -q`

Expected: import error，提示 `dispatch_assistant.knowledge` 不存在。

- [ ] **Step 3: 实现分页切块、中文标签和 TF-IDF**

`dispatch_assistant/knowledge.py` 写入：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SOURCES = {
    "chen-et-al-2022-hydro-wind-solar-scheduling-survey.pdf": (
        "KB-001",
        "Power Generation Scheduling for a Hydro-Wind-Solar Hybrid System: A Systematic Survey and Prospect",
    ),
    "zhang-et-al-2018-yalong-river-operation.pdf": (
        "KB-002",
        "Short-Term Optimal Operation of a Wind-PV-Hydro Complementary Installation: Yalong River, Sichuan Province, China",
    ),
}

PAGE_TAGS = {
    ("KB-001", 4): "互补调度 研究框架 发电预测 风险管理 机组组合 多时间尺度",
    ("KB-001", 7): "弃风光 弃电 功率平衡 风险",
    ("KB-001", 8): "功率平衡 切负荷 备用容量",
    ("KB-001", 20): "失负荷 出力不足 负荷损失",
    ("KB-001", 21): "弃风光率 清洁能源消纳",
    ("KB-002", 7): "季节互补 风光冬春 水电夏秋",
    ("KB-002", 9): "日内互补 水电调节 风光波动",
    ("KB-002", 10): "功率平衡 水量平衡 流量平衡 库容 出库流量 约束",
    ("KB-002", 15): "出库流量 调节",
    ("KB-002", 16): "水电补偿 风光出力",
}


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    page: int
    quote: str
    score: float


@dataclass(frozen=True)
class _Chunk:
    source_id: str
    title: str
    page: int
    quote: str
    search_text: str


class KnowledgeIndex:
    def __init__(self, chunks: list[_Chunk]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
        self.matrix = self.vectorizer.fit_transform([chunk.search_text for chunk in chunks])

    def retrieve(self, query: str, top_k: int = 4, min_score: float = 0.05) -> list[Evidence]:
        query_vector = self.vectorizer.transform([query.strip()])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        ranked = scores.argsort()[::-1]
        results: list[Evidence] = []
        seen_pages: set[tuple[str, int]] = set()
        for index in ranked:
            score = float(scores[index])
            chunk = self.chunks[int(index)]
            page_key = (chunk.source_id, chunk.page)
            if score < min_score or page_key in seen_pages:
                continue
            results.append(Evidence(chunk.source_id, chunk.title, chunk.page, chunk.quote, score))
            seen_pages.add(page_key)
            if len(results) == top_k:
                break
        return results


def _chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    step = size - overlap
    return [cleaned[start : start + size] for start in range(0, len(cleaned), step)]


def build_knowledge_index(source_dir: Path) -> KnowledgeIndex:
    chunks: list[_Chunk] = []
    for filename, (source_id, title) in SOURCES.items():
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"知识源不存在：{path}")
        reader = PdfReader(path)
        for page_number, page in enumerate(reader.pages, start=1):
            tags = PAGE_TAGS.get((source_id, page_number), "")
            for quote in _chunk_text(page.extract_text() or ""):
                search_text = f"{title} {tags} {quote}"
                chunks.append(_Chunk(source_id, title, page_number, quote, search_text))
    if not chunks:
        raise ValueError("知识库没有可检索文本。")
    return KnowledgeIndex(chunks)
```

- [ ] **Step 4: 运行检索测试**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge.py -q`

Expected: `3 passed`。若中文查询未命中指定页，只调整对应页的中文标签或最低分数，并保留“不相关问题返回空列表”的测试。

- [ ] **Step 5: 提交任务**

```powershell
git add dispatch_assistant/knowledge.py tests/test_knowledge.py
git commit -m "feat: add local cited knowledge retrieval"
```

---

### Task 5: DeepSeek 受约束问答

**Files:**
- Create: `dispatch_assistant/llm.py`
- Create: `tests/test_llm.py`

**Interfaces:**
- Consumes: 用户问题和 `list[Evidence]`。
- Produces: `answer_question(question, evidence, client=None) -> str`；无证据时本地拒答，不调用 API。

- [ ] **Step 1: 写无真实 API 调用的失败测试**

`tests/test_llm.py` 写入：

```python
from types import SimpleNamespace

import pytest

from dispatch_assistant.knowledge import Evidence
from dispatch_assistant.llm import DeepSeekError, GroundingError, answer_question


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_client(content: str):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def make_evidence() -> list[Evidence]:
    return [Evidence("KB-002", "Test Source", 10, "Power balance and water balance constraints.", 0.8)]


def test_abstains_without_evidence_and_does_not_call_api() -> None:
    assert answer_question("无依据问题", [], client=None) == "当前知识库没有足够依据回答这个问题。"


def test_requires_environment_key_when_evidence_exists(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(DeepSeekError, match="DEEPSEEK_API_KEY"):
        answer_question("什么是功率平衡？", make_evidence(), client=None)


def test_calls_current_deepseek_model_with_thinking_disabled() -> None:
    client, completions = make_client("功率平衡用于约束供需关系。[KB-002, p.10]")
    answer = answer_question("什么是功率平衡？", make_evidence(), client=client)
    assert "[KB-002, p.10]" in answer
    assert completions.kwargs["model"] == "deepseek-v4-flash"
    assert completions.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


def test_rejects_unretrieved_citation() -> None:
    client, _ = make_client("结论。[KB-001, p.4]")
    with pytest.raises(GroundingError, match="未检索到的来源"):
        answer_question("问题", make_evidence(), client=client)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm.py -q`

Expected: import error，提示 `dispatch_assistant.llm` 不存在。

- [ ] **Step 3: 实现密钥边界、调用和引用校验**

`dispatch_assistant/llm.py` 写入：

```python
from __future__ import annotations

import os
import re

from openai import OpenAI

from dispatch_assistant.knowledge import Evidence

MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"
NO_EVIDENCE_MESSAGE = "当前知识库没有足够依据回答这个问题。"
CITATION_PATTERN = re.compile(r"\[(KB-\d{3}),\s*p\.(\d+)\]")


class DeepSeekError(RuntimeError):
    pass


class GroundingError(ValueError):
    pass


def call_deepseek(system_prompt: str, user_prompt: str, client=None, max_tokens: int = 800) -> str:
    if client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise DeepSeekError("未检测到 DEEPSEEK_API_KEY 环境变量。")
        client = OpenAI(api_key=api_key, base_url=BASE_URL)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            extra_body={"thinking": {"type": "disabled"}},
        )
    except Exception as exc:
        raise DeepSeekError(f"DeepSeek API 调用失败：{exc}") from exc
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise DeepSeekError("DeepSeek API 返回了空内容。")
    return content.strip()


def _format_evidence(evidence: list[Evidence]) -> str:
    return "\n\n".join(
        f"[{item.source_id}, p.{item.page}] {item.title}\n{item.quote}"
        for item in evidence
    )


def _validate_citations(answer: str, evidence: list[Evidence]) -> None:
    citations = {(source, int(page)) for source, page in CITATION_PATTERN.findall(answer)}
    allowed = {(item.source_id, item.page) for item in evidence}
    if not citations:
        raise GroundingError("回答没有按要求显示来源。")
    if not citations.issubset(allowed):
        raise GroundingError("回答引用了未检索到的来源。")


def answer_question(question: str, evidence: list[Evidence], client=None) -> str:
    if not evidence:
        return NO_EVIDENCE_MESSAGE
    system_prompt = (
        "你是水风光调度分析助手。只能根据用户消息中的证据回答，不得补充证据之外的事实。"
        "每个关键结论后必须使用形如 [KB-002, p.10] 的引用。"
        "证据不足时只回答：当前知识库没有足够依据回答这个问题。"
    )
    user_prompt = f"问题：{question}\n\n证据：\n{_format_evidence(evidence)}"
    answer = call_deepseek(system_prompt, user_prompt, client=client)
    _validate_citations(answer, evidence)
    return answer
```

- [ ] **Step 4: 运行问答及全部测试**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: `17 passed`，测试过程不访问 DeepSeek 网络且不需要 API 密钥。

- [ ] **Step 5: 提交任务**

```powershell
git add dispatch_assistant/llm.py tests/test_llm.py
git commit -m "feat: add grounded DeepSeek question answering"
```

---

### Task 6: 确定性 Markdown 报告

**Files:**
- Create: `dispatch_assistant/report.py`
- Create: `tests/test_report.py`

**Interfaces:**
- Consumes: `AnalysisResult`、检索证据和 DeepSeek 生成的纯定性解读。
- Produces: `generate_report(result, evidence, client=None) -> str`。指标表、异常表和来源列表全部由 Python 组装。

- [ ] **Step 1: 写报告一致性失败测试**

`tests/test_report.py` 写入：

```python
from types import SimpleNamespace

import pytest

from dispatch_assistant.analysis import analyze_dispatch
from dispatch_assistant.knowledge import Evidence
from dispatch_assistant.report import ReportValidationError, generate_report, render_report
from tests.test_analysis import make_valid_frame


def make_client(content: str):
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    completions = SimpleNamespace(create=lambda **kwargs: response)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def make_evidence() -> list[Evidence]:
    return [Evidence("KB-002", "Test Source", 10, "Power balance constraint.", 0.8)]


def test_report_uses_python_metrics_and_expected_sections() -> None:
    result = analyze_dispatch(make_valid_frame())
    report = render_report(result, make_evidence(), "系统供需整体协调，水电承担调节作用。")
    assert "# 水风光调度分析报告" in report
    assert "876.000 GWh" in report
    assert "613.200 GWh" in report
    assert "## 异常清单" in report
    assert "[KB-002, p.10]" in report


def test_rejects_numbers_generated_by_model() -> None:
    result = analyze_dispatch(make_valid_frame())
    with pytest.raises(ReportValidationError, match="不得包含数字"):
        render_report(result, make_evidence(), "模型自行写入了 99%。")


def test_generate_report_accepts_qualitative_model_text() -> None:
    result = analyze_dispatch(make_valid_frame())
    report = generate_report(result, make_evidence(), client=make_client("系统整体供需协调。"))
    assert "系统整体供需协调。" in report
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_report.py -q`

Expected: import error，提示 `dispatch_assistant.report` 不存在。

- [ ] **Step 3: 实现受约束解读和确定性报告组装**

`dispatch_assistant/report.py` 写入：

```python
from __future__ import annotations

import json
import re

from dispatch_assistant.analysis import AnalysisResult
from dispatch_assistant.knowledge import Evidence
from dispatch_assistant.llm import call_deepseek


class ReportValidationError(ValueError):
    pass


METRIC_ROWS = (
    ("年负荷电量", "load_energy_gwh", "{:.3f} GWh"),
    ("年水电电量", "hydro_energy_gwh", "{:.3f} GWh"),
    ("年风光上网电量", "wind_solar_energy_gwh", "{:.3f} GWh"),
    ("水电占比", "hydro_share", "{:.2%}"),
    ("风光占比", "wind_solar_share", "{:.2%}"),
    ("供电不足电量", "shortage_energy_gwh", "{:.6f} GWh"),
    ("供电不足天数", "shortage_days", "{} 天"),
    ("最大出力不足率", "max_shortage_rate", "{:.4%}"),
    ("平均弃风光率", "mean_curtailment_rate", "{:.2%}"),
    ("最大弃风光率", "max_curtailment_rate", "{:.2%}"),
    ("平均弃水率", "mean_water_discard_rate", "{:.2%}"),
    ("最大弃水率", "max_water_discard_rate", "{:.2%}"),
    ("平均水电出力系数 K", "mean_hydro_coefficient", "{:.4f}"),
    ("最大功率平衡绝对残差", "max_abs_power_balance_residual_mw", "{:.6f} MW"),
)


def _check_commentary(commentary: str) -> None:
    if re.search(r"[0-9０-９]", commentary):
        raise ReportValidationError("大模型定性解读不得包含数字；所有数值必须由 Python 写入。")


def render_report(result: AnalysisResult, evidence: list[Evidence], commentary: str) -> str:
    _check_commentary(commentary)
    metric_lines = ["| 指标 | 数值 |", "| --- | --- |"]
    for label, key, template in METRIC_ROWS:
        metric_lines.append(f"| {label} | {template.format(result.metrics[key])} |")

    anomaly_lines = ["| 日序号 | 规则 | 实际值 | 阈值 | 原因 |", "| --- | --- | ---: | --- | --- |"]
    if result.anomalies:
        anomaly_lines.extend(
            f"| {item.day} | {item.rule} | {item.value:.6f} | {item.threshold} | {item.reason} |"
            for item in result.anomalies
        )
    else:
        anomaly_lines.append("| - | 未发现符合当前规则的异常 | - | - | - |")

    evidence_lines = [
        f"- [{item.source_id}, p.{item.page}] {item.title}：{item.quote[:240]}"
        for item in evidence
    ] or ["- 当前知识库未检索到可用于本报告的资料依据。"]

    return "\n".join(
        [
            "# 水风光调度分析报告",
            "",
            "## 数据概况",
            "",
            f"- 时间尺度：日",
            f"- 数据行数：{len(result.frame)}",
            "",
            "## 关键指标",
            "",
            *metric_lines,
            "",
            "## 图表解读",
            "",
            commentary,
            "",
            "## 异常清单",
            "",
            *anomaly_lines,
            "",
            "## 资料依据",
            "",
            *evidence_lines,
            "",
            "## 结论边界",
            "",
            "本报告中的数值由 Python 根据上传 CSV 计算；专业解释仅基于上列检索证据。",
        ]
    )


def generate_report(result: AnalysisResult, evidence: list[Evidence], client=None) -> str:
    system_prompt = (
        "你是水风光调度分析助手。根据结构化结果和证据写一段简短中文定性解读。"
        "不得出现阿拉伯数字、全角数字、百分号、页码或新增事实；不要写标题和引用。"
    )
    payload = {
        "metrics": result.metrics,
        "anomalies": [item.__dict__ for item in result.anomalies],
        "evidence": [item.__dict__ for item in evidence],
    }
    commentary = call_deepseek(system_prompt, json.dumps(payload, ensure_ascii=False), client=client, max_tokens=500)
    return render_report(result, evidence, commentary)
```

- [ ] **Step 4: 运行报告及全部测试**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: `20 passed`。

- [ ] **Step 5: 提交任务**

```powershell
git add dispatch_assistant/report.py tests/test_report.py
git commit -m "feat: generate deterministic markdown reports"
```

---

### Task 7: Streamlit 单页闭环

**Files:**
- Create: `app.py`
- Modify: `README.md`
- Create: `docs/test-results.md`

**Interfaces:**
- Consumes: 用户上传的固定 CSV、问题文本和本机环境变量。
- Produces: 页面指标、五组图表、异常表、证据问答、报告预览和 Markdown 下载。

- [ ] **Step 1: 创建页面主流程**

`app.py` 写入：

```python
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from dispatch_assistant.analysis import CsvValidationError, analyze_dispatch, read_dispatch_csv
from dispatch_assistant.charts import build_figures
from dispatch_assistant.knowledge import build_knowledge_index
from dispatch_assistant.llm import DeepSeekError, GroundingError, answer_question
from dispatch_assistant.report import ReportValidationError, generate_report

BASE_DIR = Path(__file__).resolve().parent
REPORT_QUERY = "水风光互补调度 功率平衡 弃风光 出力不足 弃水 水量偏差"


@st.cache_resource
def get_knowledge_index():
    return build_knowledge_index(BASE_DIR / "knowledge_base" / "sources")


def show_evidence(evidence) -> None:
    for item in evidence:
        with st.expander(f"{item.source_id} · 第 {item.page} 页 · 相似度 {item.score:.3f}"):
            st.write(item.title)
            st.caption(item.quote)


st.set_page_config(page_title="水风光调度智能分析助手", layout="wide")
st.title("水风光调度智能分析助手")
st.caption("固定 CSV 分析 · 可解释异常 · 有来源问答 · Markdown 报告")

uploaded = st.file_uploader("上传 GBK 编码的固定格式 CSV", type=["csv"])
if uploaded is None:
    st.info("请先上传调度结果 CSV。")
    st.stop()

try:
    frame = read_dispatch_csv(uploaded)
    result = analyze_dispatch(frame)
except CsvValidationError as exc:
    st.error("CSV 校验未通过")
    for message in exc.messages:
        st.write(f"- {message}")
    st.stop()

st.success("CSV 校验通过：365 行日尺度数据。")
analysis_tab, qa_tab, report_tab = st.tabs(["结果分析", "知识问答", "分析报告"])

with analysis_tab:
    summary = [
        ("年负荷电量", f"{result.metrics['load_energy_gwh']:.3f} GWh"),
        ("年水电电量", f"{result.metrics['hydro_energy_gwh']:.3f} GWh"),
        ("年风光上网电量", f"{result.metrics['wind_solar_energy_gwh']:.3f} GWh"),
        ("最大功率平衡绝对残差", f"{result.metrics['max_abs_power_balance_residual_mw']:.6f} MW"),
    ]
    columns = st.columns(4)
    for column, (label, value) in zip(columns, summary):
        column.metric(label, value)

    for title, figure in build_figures(result.frame).items():
        st.pyplot(figure, use_container_width=True)

    st.subheader("异常清单")
    if result.anomalies:
        st.dataframe(pd.DataFrame([item.__dict__ for item in result.anomalies]), use_container_width=True)
    else:
        st.info("未发现符合当前规则的异常。")

with qa_tab:
    question = st.text_input("请输入与水风光互补调度相关的问题")
    if st.button("检索并回答", disabled=not question.strip()):
        evidence = get_knowledge_index().retrieve(question)
        show_evidence(evidence)
        try:
            st.markdown(answer_question(question, evidence))
        except (DeepSeekError, GroundingError) as exc:
            st.error(str(exc))

with report_tab:
    report_evidence = get_knowledge_index().retrieve(REPORT_QUERY, top_k=6)
    show_evidence(report_evidence)
    if not os.getenv("DEEPSEEK_API_KEY"):
        st.info("本地分析可正常使用；设置 DEEPSEEK_API_KEY 后可生成问答和报告。")
    if st.button("生成分析报告"):
        try:
            report = generate_report(result, report_evidence)
            st.markdown(report)
            st.download_button(
                "下载 Markdown 报告",
                data=report.encode("utf-8"),
                file_name="水风光调度分析报告.md",
                mime="text/markdown",
            )
        except (DeepSeekError, ReportValidationError) as exc:
            st.error(str(exc))
```

- [ ] **Step 2: 执行静态导入和全部测试**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall app.py dispatch_assistant
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: compileall 退出码为 0；pytest 显示 `20 passed`。

- [ ] **Step 3: 更新 README 的本地运行说明**

在 `README.md` 增加以下章节：

```markdown
## 本地运行

1. 使用 Python 3.12 创建虚拟环境并安装 `requirements.txt`。
2. 在本机 PowerShell 中设置 `DEEPSEEK_API_KEY` 环境变量；不要把密钥写入文件或发到聊天中。
3. 运行 `.\.venv\Scripts\python.exe -m streamlit run app.py`。
4. 浏览器打开 Streamlit 提供的本地地址，上传固定格式 CSV。

没有 API 密钥或网络不可用时，本地 CSV 校验、指标、图表和异常识别仍可使用；知识问答和报告生成会明确提示不可用。
```

- [ ] **Step 4: 运行本地页面并按主流程验证**

Run: `.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true`

Expected: 终端显示本地访问地址；上传 `AAA_original.csv` 后显示 365 行校验通过、五组图表、异常表和功率平衡结果。未设置 API 密钥时，页面仍保留本地分析并提示问答和报告不可用。

- [ ] **Step 5: 在本机设置密钥并验证问答与报告**

用户在自己的 PowerShell 输入真实密钥，聊天、代码、截图和 Git 中均不出现密钥值：

```powershell
$env:DEEPSEEK_API_KEY="<仅在本机终端输入真实值>"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

验证问题：`水电为什么能够补偿风电和光伏的波动？`

Expected: 回答至少显示一个实际检索到的 `[KB-xxx, p.x]` 引用；报告可预览并下载 Markdown；报告表格中的数值与页面指标一致。若 API 返回错误，只记录完整错误并保留本地分析结果。

- [ ] **Step 6: 记录实际测试结果，不预填性能结论**

创建 `docs/test-results.md`，只写入本次实际执行的日期、环境、命令、通过数、真实 CSV 基线、问答引用检查、报告一致性检查以及三次端到端计时。未执行的项目明确写“未执行”，不得写“通过”。

- [ ] **Step 7: 连续三次验证演示路径**

每次从选择 CSV 开始计时，到 Markdown 下载按钮可用为止。把三个真实耗时写入 `docs/test-results.md`；只有三次均无阻塞且每次不超过 3 分钟，才能声明成功指标达成。

- [ ] **Step 8: 最终回归与提交**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git status --short
```

Expected: pytest 全部通过；`git diff --check` 退出码为 0；Git 状态不包含 `.env`、`.streamlit/secrets.toml` 或任何密钥文件。

```powershell
git add app.py README.md docs/test-results.md
git commit -m "feat: complete local dispatch analysis MVP"
```

---

## Self-Review Result

- Spec coverage: CSV 校验、确定性指标、五组图表、五条异常规则、本地引用检索、无依据拒答、DeepSeek 失败降级、结构化报告、Markdown 下载和三分钟验证均有对应任务。
- Deliberate simplifications: 单页 Streamlit、内存 TF-IDF、两篇固定 PDF、页级中文标签、同步 API 调用；未加入 LangChain、向量数据库、Agent、账户、云存储或额外导出格式。
- Type consistency: `AnalysisResult`、`Evidence`、`KnowledgeIndex.retrieve`、`answer_question` 和 `generate_report` 的输入输出在各任务间保持一致。
- Evidence boundary: 中文标签只用于检索；问答引用由检索集合校验；报告数字全部由 Python 模板写入，大模型生成文本不得含数字。
- Known ceiling: 两篇英文 PDF 的关键词召回适合现场演示，但同义表达覆盖有限；只有实际测试证明召回不足时，才考虑增加人工页标签或多语种嵌入模型。
