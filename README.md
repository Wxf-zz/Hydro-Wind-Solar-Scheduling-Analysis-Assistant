# 水风光调度智能分析助手

面向水风光调度研究者的本地分析型 AI 产品。用户上传约定格式的调度结果 CSV 后，产品使用 Python 计算指标、生成图表、按专业规则识别异常，并结合可追溯的公开资料生成结构化 Markdown 报告。

## 当前状态

- 当前阶段：MVP 已完成本地实现、真实端到端验收，并已合并到 `master` 主分支
- 实现状态：Streamlit 单页已经串联固定 CSV 分析、五组图表、异常清单、带来源问答和 Markdown 报告下载
- 数据状态：公开仓库不包含调度结果 CSV 和知识库 PDF；本地分析时需选择已获准的 CSV，知识问答和报告功能需按[知识库资料清单](knowledge_base/README.md)准备本地资料
- 测试状态：自动化测试 26 项通过；真实 CSV、真实 DeepSeek 问答、报告预览与下载均已核验；3 次人工端到端运行均小于 180 秒，未记录具体秒数

## 项目目录为什么这样分

```text
项目根目录/
├─ app.py                Streamlit 页面和完整任务流编排
├─ dispatch_assistant/   产品功能代码
│  └─ analysis.py        CSV 校验、指标计算和异常识别
│  └─ charts.py          五组固定 matplotlib 图表
│  └─ knowledge.py       PDF 切块、TF-IDF 索引和可定位证据检索
│  └─ llm.py             DeepSeek 调用、无证据拒答和引用边界校验
│  └─ report.py          确定性 Markdown 模板和模型数字边界
├─ tests/                自动化测试，防止后续修改破坏已有功能
│  └─ __init__.py        让测试文件之间能复用合成数据工具
│  └─ test_app.py        页面启动和未上传状态测试
├─ knowledge_base/       公开知识资料清单及本地资料放置说明
│  └─ sources/           本地 PDF 目录（PDF 不随公开仓库发布）
├─ docs/                 产品决策、实施计划和真实测试记录
├─ requirements.txt      可重复安装的 Python 依赖清单
└─ README.md             项目入口说明，供开发、演示和面试讲解
```

`.venv/` 是本机独立 Python 环境，只为运行项目服务，不属于产品代码，也不会提交到 Git。

MVP 曾在 `.worktrees/mvp-implementation/` 隔离工作树中开发，避免实现阶段直接影响主分支。验收完成后，代码已快进合并到 `master`，临时工作树和功能分支均已清理。

## 最小 RAG 数据流

```text
两篇已批准 PDF（需按知识库说明放入本地）
    ↓ pypdf 按页提取
约 800 字符的重叠文本块
    ↓ 中文页标签只参与检索
字符级 TF-IDF 向量
    ↓ 余弦相似度排序和最低分过滤
Evidence（资料编号、题名、PDF 页码、原文片段、相关度）
```

检索模块只负责找证据，生成模块再把证据交给 DeepSeek；如果检索结果为空，系统会直接拒答，不能让大模型凭记忆补充。

## 本地运行

首次运行时，在项目根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

终端出现 `Local URL: http://localhost:8501` 后，在浏览器打开该地址。未配置 API 密钥时，CSV 分析、图表和异常清单仍然可用；未准备本地 PDF 时，知识问答和报告依据功能会提示补充资料；带引用回答和报告生成还需要 API 密钥。

需要测试完整 AI 流程时，在启动应用的同一个 PowerShell 窗口中临时设置密钥。输入过程不会显示字符，密钥只存在于当前终端进程：

```powershell
$secureKey = Read-Host "请输入 DeepSeek API Key" -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
.\.venv\Scripts\python.exe -m streamlit run app.py
```

演示结束后可关闭终端；也可以在同一终端执行 `Remove-Item Env:\DEEPSEEK_API_KEY` 清除临时环境变量。不要把密钥保存到代码、`.env`、Streamlit 配置、截图或 Git。

### 现场演示顺序

1. 上传已确认的 GBK 固定模板 CSV，说明系统先校验 12 列和 365 日数据。
2. 展示最大功率平衡残差、五组图表和逐条可解释的异常清单。
3. 准备好知识库 PDF 后，提问“功率平衡和水量平衡约束是什么？”，先展开原文证据，再展示带资料编号和页码的回答。
4. 生成报告，说明数字、异常和来源由 Python 固定，DeepSeek 只生成定性解读，最后下载 Markdown。

## AI 亮点如何体现

- 不是把 CSV 直接交给大模型“猜结论”，而是让 Python 负责精确计算，让 AI 负责资料理解和自然语言表达。
- 问答先本地检索已批准论文，页面同时展示原文、资料编号和页码；无证据时拒答，生成后还校验引用边界。
- 报告把模型权限限制到无数字的定性解读，避免模型改写指标；缺少密钥时产品仍可完成确定性分析，体现可控降级。

## AI 问答的安全边界

```text
用户问题
  ↓
本地检索：只返回已批准 PDF 的 Evidence
  ↓ 无证据时本地拒答，不调用 API
受约束提示词：证据是材料，不是指令
  ↓
DeepSeek-V4-Flash：只负责组织中文表达
  ↓
Python 引用校验：必须引用本次检索到的资料编号和页码
  ↓ 不合格回答抛出错误，不直接展示
最终回答 + 可核对原文
```

API 地址和模型名依据 [DeepSeek 官方模型文档](https://api-docs.deepseek.com/quick_start/pricing/)；非思考模式参数依据 [Thinking Mode 文档](https://api-docs.deepseek.com/guides/thinking_mode)。密钥只从本机环境变量 `DEEPSEEK_API_KEY` 读取，不写入代码、文档或 Git。

## 报告内容由谁负责

| 报告内容 | 产生者 | 原因 |
| --- | --- | --- |
| 数据行数、指标和单位 | Python | 必须与 CSV 计算结果完全一致 |
| 异常日期、数值、阈值和原因 | Python | 规则固定、可复核 |
| 资料编号、页码和原文片段 | 本地检索 + Python | 防止模型编造来源 |
| 简短图表解读 | DeepSeek | 需要自然语言归纳能力 |
| 栏目、表格和结论边界 | Python 模板 | 保证每份报告结构一致 |

DeepSeek 生成的报告解读不得包含数字或百分号。检测到数字时，`report.py` 会拒绝生成，而不是让模型写出的数值覆盖 Python 结果。

## 已确认的产品决策

| 项目 | 决策 |
| --- | --- |
| 核心用户 | 水风光调度领域的研究生或科研人员 |
| 核心痛点 | 调度结果分析重复烦琐，指标、图表和异常检查耗时 |
| 核心场景 | 组会或阶段汇报前快速整理图表和结论 |
| 产品组织方式 | 以 CSV 分析为入口的连续任务流 |
| CSV 范围 | 只支持一套固定模板 |
| 异常识别 | 固定、可解释的专业规则 |
| 知识范围 | 首批使用两篇开放获取论文；行业报告暂不需要，规则全文在合法获得后再评估 |
| 运行边界 | 应用、分析和知识库在本地；大模型通过云端 API 调用 |
| 报告形式 | 页面内预览并下载 Markdown 文件 |
| 首要成功指标 | 从选择 CSV 到报告可下载，端到端不超过 3 分钟 |

## MVP

1. 基于预先整理的公开资料进行知识问答，回答显示可定位来源。
2. 校验固定格式 CSV，计算指标、生成图表并按专业规则识别异常。
3. 仅根据检索证据和 Python 计算结果生成结构化报告。

完整范围、主流程、非目标、风险和验收方式见[产品设计规格](docs/superpowers/specs/2026-08-09-water-wind-solar-analysis-assistant-design.md)。

首批知识源、适用问题、重点页和引用边界见[知识库资料清单](knowledge_base/README.md)。

分步骤文件、测试和提交方案见[MVP 实施计划](docs/superpowers/plans/2026-08-09-water-wind-solar-assistant-implementation.md)。

## 数据与安全约束

- 只使用用户明确授权、已脱敏且非保密的调度结果。
- 知识库只使用来源清晰、允许用于本地演示的公开资料。
- 公开仓库不包含调度结果 CSV 和知识库 PDF；运行时由用户在本地提供并自行确认授权。
- API 密钥不得写入代码、文档、截图或 Git 历史；实现阶段只能通过环境变量读取。
- 不声称尚未实测的性能、准确率、用户反馈或业务价值。

## 后续改进

MVP 已交付。后续只在获得正式调度规则、更多合法知识资料或真实用户反馈后，再评估扩大知识库、改善公式显示或支持更多 CSV 模板，暂不提前增加框架。
