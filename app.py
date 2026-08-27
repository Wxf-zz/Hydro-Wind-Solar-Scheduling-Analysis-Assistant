from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from dispatch_assistant.analysis import (
    AnalysisResult,
    Anomaly,
    CsvValidationError,
    analyze_dispatch,
    read_dispatch_csv,
)
from dispatch_assistant.charts import build_figures
from dispatch_assistant.knowledge import Evidence, KnowledgeIndex, build_knowledge_index
from dispatch_assistant.llm import (
    LLMError,
    GroundingError,
    answer_question,
    is_llm_configured,
)
from dispatch_assistant.report import ReportValidationError, generate_report

BASE_DIR = Path(__file__).resolve().parent
REPORT_QUERY = "水风光互补调度 功率平衡 弃风光 出力不足 弃水 水量偏差"
CHART_TITLES = {
    "power": "出力与负荷",
    "rates": "新能源消纳与供电不足",
    "flows": "流量过程",
    "water": "弃水与水量偏差",
    "coefficient": "水电出力系数 K",
}


@st.cache_resource
def get_knowledge_index() -> KnowledgeIndex | None:
    try:
        return build_knowledge_index(BASE_DIR / "knowledge_base" / "sources")
    except (FileNotFoundError, ValueError):
        return None


KNOWLEDGE_BASE_MISSING_MESSAGE = (
    "本地知识库资料尚未准备；请按 knowledge_base/README.md 放入获准使用的 PDF。"
)


def show_evidence(evidence: list[Evidence]) -> None:
    if not evidence:
        st.info("当前知识库没有检索到足够相关的原文证据。")
        return

    for item in evidence:
        label = f"{item.source_id} · p.{item.page} · 相关度 {item.score:.4f}"
        with st.expander(label):
            st.caption(item.title)
            st.write(item.quote)


def format_anomaly_value(item: Anomaly) -> str:
    if item.rule == "功率不守恒":
        return f"{item.value:.6f} MW"
    if item.rule == "存在供电不足":
        return f"{item.value:.4%}"
    return f"{item.value:.2%}"


def anomaly_frame(result: AnalysisResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "日序号": item.day,
                "规则": item.rule,
                "实际值": format_anomaly_value(item),
                "阈值": item.threshold,
                "原因": item.reason,
            }
            for item in result.anomalies
        ]
    )


st.set_page_config(page_title="水风光调度智能分析助手", layout="wide")
st.title("水风光调度智能分析助手")
st.caption("固定 CSV 校验与计算 · 本地资料检索 · 可配置大模型生成")

uploaded = st.file_uploader("上传调度结果 CSV", type=["csv"])
if uploaded is None:
    st.info("请先上传调度结果 CSV。文件应使用已确认的 GBK 固定模板，并包含 365 行日尺度数据。")
    st.stop()

try:
    result = analyze_dispatch(read_dispatch_csv(uploaded))
except CsvValidationError as exc:
    st.error("CSV 未通过校验：")
    for message in exc.messages:
        st.write(f"- {message}")
    st.stop()

st.success(f"CSV 校验通过：{len(result.frame)} 行日尺度数据。")
analysis_tab, qa_tab, report_tab = st.tabs(["调度分析", "知识问答", "分析报告"])
knowledge_index = get_knowledge_index()

with analysis_tab:
    metrics = result.metrics
    columns = st.columns(4)
    columns[0].metric("最大功率平衡绝对残差", f"{metrics['max_abs_power_balance_residual_mw']:.6f} MW")
    columns[1].metric("功率不守恒天数", f"{metrics['power_balance_anomaly_days']} 天")
    columns[2].metric("供电不足天数", f"{metrics['shortage_days']} 天")
    columns[3].metric("异常记录数", f"{metrics['total_anomaly_records']} 条")

    st.subheader("固定分析图表")
    for key, figure in build_figures(result.frame).items():
        st.markdown(f"#### {CHART_TITLES[key]}")
        st.pyplot(figure, width="stretch")
        plt.close(figure)

    st.subheader("异常清单")
    if result.anomalies:
        st.dataframe(anomaly_frame(result), width="stretch", hide_index=True)
    else:
        st.success("未发现符合当前五类固定规则的异常。")

with qa_tab:
    st.write("系统先在本地资料中检索原文，再让已配置的大模型只根据这些证据组织回答。")
    if knowledge_index is None:
        st.info(KNOWLEDGE_BASE_MISSING_MESSAGE)
    question = st.text_input(
        "请输入专业问题",
        placeholder="例如：功率平衡和水量平衡约束是什么？",
    )
    if st.button("检索并回答", type="primary"):
        if not question.strip():
            st.warning("请先输入问题。")
        elif knowledge_index is None:
            st.warning(KNOWLEDGE_BASE_MISSING_MESSAGE)
        else:
            evidence = knowledge_index.retrieve(question)
            st.subheader("检索证据")
            show_evidence(evidence)
            if not evidence:
                st.info("当前知识库没有足够依据回答这个问题。")
            elif not is_llm_configured():
                st.info("证据检索已完成；配置大模型后可生成带引用回答。")
            else:
                try:
                    st.subheader("回答")
                    st.write(answer_question(question, evidence))
                except (LLMError, GroundingError) as exc:
                    st.error(str(exc))

with report_tab:
    st.write("Python 固定报告中的数字、单位、异常和来源；大模型只补充不含数字的定性解读。")
    if knowledge_index is None:
        st.info(KNOWLEDGE_BASE_MISSING_MESSAGE)
        report_evidence = []
    else:
        report_evidence = knowledge_index.retrieve(REPORT_QUERY)
    st.subheader("报告采用的资料依据")
    show_evidence(report_evidence)

    api_available = is_llm_configured()
    if not api_available:
        st.info("未完成大模型配置：本地分析可用，带 AI 解读的报告暂不可用。")

    if st.button("生成 Markdown 报告", type="primary", disabled=not api_available):
        try:
            report = generate_report(result, report_evidence)
        except (LLMError, ReportValidationError) as exc:
            st.error(str(exc))
        else:
            st.subheader("报告预览")
            st.markdown(report)
            st.download_button(
                "下载报告",
                report,
                file_name="水风光调度分析报告.md",
                mime="text/markdown",
                on_click="ignore",
            )
