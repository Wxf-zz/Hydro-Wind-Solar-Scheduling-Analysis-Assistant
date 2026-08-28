# 水风光调度智能分析助手

一个面向水风光调度研究和汇报场景的本地分析工具。上传调度结果 CSV 后，助手会自动完成数据校验、指标计算、图表生成和异常识别；准备本地知识资料并配置大模型后，还可以进行带页码依据的专业问答和生成 Markdown 分析报告。

## 它可以做什么

- 校验固定格式的调度结果 CSV，识别列名、行数、编码、空值和比例范围问题。
- 计算水电、风光、负荷、供电不足、弃风光、弃水和水量偏差等指标。
- 生成五组调度分析图表，帮助快速观察出力、负荷、流量和消纳情况。
- 按固定、可解释的规则列出功率不守恒、供电不足、高弃风光、高弃水和计划执行偏差。
- 从本地 PDF 知识资料中检索原文，并展示资料编号、题名和页码。
- 调用大模型API生成带引用问答和定性分析报告。
- 没有 API 密钥或本地 PDF 时，CSV 分析功能仍然可以独立运行。

## 快速开始

### 运行环境

- Windows
- Python 3.12
- 首次安装依赖需要网络连接

### 运行方式1：从 GitHub Release 使用

1. 在本仓库的 [Releases](https://github.com/Wxf-zz/Hydro-Wind-Solar-Scheduling-Analysis-Assistant/releases) 页面下载最新 ZIP 文件。
2. 解压到本地文件夹。
3. 双击 `start.bat`。
4. 等待依赖安装完成，在浏览器打开 `http://localhost:8501`。
5. 上传符合要求的调度结果 CSV，开始分析。

### 运行方式2：手动启动

在项目根目录打开 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 使用方法

1. 在“调度分析”页面上传 CSV。
2. 查看数据校验结果、关键指标、五组图表和异常清单。
3. 如果已经准备本地知识资料，可在“知识问答”页面检索专业问题。
4. 如果已经配置大模型，可在“分析报告”页面生成并下载 Markdown 报告。

完整操作步骤、输入格式和常见问题见[使用说明](使用说明.md)。

### 通用配置（推荐）

```powershell
$env:LLM_API_KEY = "你的大模型 API Key"
$env:LLM_BASE_URL = "https://你的服务地址/v1"
$env:LLM_MODEL = "你的模型名称"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 知识库说明

CSV 和 PDF 原文不会随公开仓库或 Release 发布。这样可以避免把用户数据或未经确认授权的文件公开到互联网。

如果需要启用知识问答和带资料依据的报告，请按照[知识库资料清单](knowledge_base/README.md)取得允许本地使用的资料，并使用指定文件名放入 `knowledge_base/sources/`。缺少这些文件时，应用会明确提示，CSV 分析仍可使用。

## 输入文件要求

- 文件格式：CSV
- 编码：GBK
- 数据行数：365 行
- 第一行必须包含固定的 12 列，具体列名见[使用说明](使用说明.md)
- 数据应经过脱敏，并确认可以用于本地分析

## 运行边界

- 指标、图表、异常和报告中的数值由 Python 计算或写入。
- 大模型只负责在检索证据和结构化结果范围内生成文字。
- 不提供正式调度规程、工程审查或投资决策结论。
- 项目不会自动上传用户 CSV；大模型请求是否包含业务内容取决于用户实际操作和所选服务。
