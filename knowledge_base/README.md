# 知识库资料清单

本目录只保存用户已批准、来源清晰且可用于本地演示的公开资料。当前资料用于回答专业问题和解释 CSV 分析结果，不用于替代正式调度规程或工程审查。

公开仓库只提交本清单，不提交 CSV 和 PDF 原文。若要启用知识问答及带资料依据的报告，请从下方公开页面取得允许本地使用的文件，并按原文件名放入 `sources/`；缺少本地资料时，应用仍可使用 CSV 分析功能，但会提示无法进行知识检索。

## 已批准资料

### KB-001 水风光调度综述

- 题名：Power Generation Scheduling for a Hydro-Wind-Solar Hybrid System: A Systematic Survey and Prospect
- 作者：Chaoyang Chen, Hualing Liu, Yong Xiao, Fagen Zhu, Li Ding, Fuwen Yang
- 出版信息：Energies, 2022, 15(22), 8747
- DOI：<https://doi.org/10.3390/en15228747>
- 公开页面：<https://www.mdpi.com/1996-1073/15/22/8747>
- 需自行放入的本地文件：`sources/chen-et-al-2022-hydro-wind-solar-scheduling-survey.pdf`
- 主要用途：解释水风光互补机理、预测不确定性、风险管理、多时间尺度调度、弃电和失负荷等概念。
- 重点页：第 3-8、14、17-21 页。
- 局限：属于综述，适合提供研究背景和概念框架，不作为具体异常阈值或强制性规则的依据。

### KB-002 雅砻江水风光短期运行案例

- 题名：Short-Term Optimal Operation of a Wind-PV-Hydro Complementary Installation: Yalong River, Sichuan Province, China
- 作者：Xinshuo Zhang, Guangwen Ma, Weibin Huang, Shijun Chen, Shuai Zhang
- 出版信息：Energies, 2018, 11(4), 868
- DOI：<https://doi.org/10.3390/en11040868>
- 公开页面：<https://www.mdpi.com/1996-1073/11/4/868>
- 需自行放入的本地文件：`sources/zhang-et-al-2018-yalong-river-operation.pdf`
- 主要用途：解释季节和日内互补特性，以及功率平衡、水量平衡、流量、库容和出库约束。
- 重点页：第 7-10、15-17 页；其中第 10 页给出功率平衡和水电约束。
- 局限：案例是特定流域的短期调度，不能直接证明其他流域的数值阈值或长期运行结论。

## 暂不纳入

- Wan 等（2025）：网页正文与项目字段高度相关，但自动下载 PDF 时被出版社拒绝访问；在获得合法、完整且可定位页码的文件前不纳入。
- NB/T 11883-2025：官方平台可核验标准名称、状态和适用范围，但未获得公开合法的标准全文；不根据目录或二手摘要生成规范性结论。
- 行业报告：当前 MVP 不需要宏观装机规模或市场趋势，暂不增加低相关资料。

## 引用与回答规则

1. 专业结论必须显示资料编号、题名和 PDF 页码。
2. 检索不到充分证据时，明确回答“当前知识库没有足够依据”。
3. CSV 数值和异常计数由 Python 计算；大模型不得自行计算或修改。
4. `0.01 MW`、`10%` 等异常阈值属于已确认的 MVP 分析规则，不冒充论文结论或行业强制标准。
5. 不以论文参考文献列表代替被引用论文的正文证据。
