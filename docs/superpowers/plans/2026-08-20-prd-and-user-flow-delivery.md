# PRD and User Flow Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `D:\agent` 根目录生成水风光调度智能分析助手的正式 PRD 和用户流程图。

**Architecture:** PRD 负责完整描述产品背景、需求、指标和迭代边界；用户流程图负责用 Mermaid 表达主流程、判断节点与异常回路。两份文档共享同一事实来源，但各自可以独立阅读。

**Tech Stack:** UTF-8 Markdown、Mermaid、PowerShell 文本检查、Git。

## Global Constraints

- 两份文件必须保存为 `D:\agent\产品需求文档PRD.md` 和 `D:\agent\用户流程图.md`。
- PRD 必须包含用户指定的十个章节。
- 内容只使用项目代码、README、现有规格、知识库清单和真实验收记录中的可核对事实。
- 不包含 API Key、保密 CSV 内容、虚构用户反馈或未经验证的业务指标。
- 用户流程必须反映现有水风光调度助手，而不是简历求职助手。

---

### Task 1: 产品需求文档 PRD

**Files:**
- Create: `产品需求文档PRD.md`
- Reference: `README.md`
- Reference: `docs/AI产品经理简历项目交付说明.md`
- Reference: `docs/test-results.md`
- Reference: `knowledge_base/README.md`

**Interfaces:**
- Consumes: 已实现的产品功能、真实验收结果和已确认的产品边界。
- Produces: 十章节、可独立阅读的正式 PRD。

- [x] **Step 1: 编写十章节 PRD**

章节固定为项目背景、用户画像、用户痛点、产品目标、用户流程、功能架构、核心功能需求、非功能需求、产品指标和后续迭代。核心功能需求使用编号、优先级、前置条件、处理逻辑、输出与异常处理描述。

- [x] **Step 2: 校验 PRD 章节和敏感信息**

Run:

```powershell
rg -n "^## [0-9]+\." 产品需求文档PRD.md
rg -n "TBD|TODO|上传简历|模拟面试|DEEPSEEK_API_KEY=" 产品需求文档PRD.md
```

Expected: 第一条命令返回 10 个章节；第二条命令无输出。

### Task 2: 用户流程图

**Files:**
- Create: `用户流程图.md`
- Reference: `产品需求文档PRD.md`

**Interfaces:**
- Consumes: PRD 中的用户主流程、功能边界和异常处理。
- Produces: 一张 Mermaid 总流程图，以及节点和异常分支说明。

- [x] **Step 1: 编写 Mermaid 流程图**

主流程必须包含启动应用、上传 CSV、数据校验、Python 分析、图表和异常清单、专业提问、本地检索、DeepSeek 带引用回答、结构化报告、预览和下载。异常分支必须包含 CSV 校验失败、无 API Key、无检索证据和 AI 输出校验失败。

- [x] **Step 2: 校验 Mermaid 结构和跨文档一致性**

Run:

```powershell
rg -n "```mermaid|CSV 校验失败|未配置 API Key|没有足够证据|校验失败|下载 Markdown" 用户流程图.md
rg -n "上传简历|目标岗位|模拟面试|TBD|TODO" 用户流程图.md 产品需求文档PRD.md
git diff --check -- 产品需求文档PRD.md 用户流程图.md
```

Expected: 第一条命令命中全部必要节点；第二条命令无输出；第三条命令无格式错误。

### Task 3: 最终交付检查

**Files:**
- Verify: `产品需求文档PRD.md`
- Verify: `用户流程图.md`

**Interfaces:**
- Consumes: 两份已完成文档。
- Produces: 可交付且已纳入本地 Git 历史的文档版本。

- [x] **Step 1: 对照规格检查范围、事实和指标**

确认固定 CSV 范围、两篇论文、Python/DeepSeek 分工、26 项自动化测试和三次低于 180 秒的人工验收均表述准确，并明确未验证项。

- [x] **Step 2: 仅提交两份交付文档和本计划**

```powershell
git add -- 产品需求文档PRD.md 用户流程图.md docs/superpowers/plans/2026-08-20-prd-and-user-flow-delivery.md
git commit -m "docs: add PRD and user flow"
```

不得加入未跟踪的 `AAA_original.csv`。

