---
name: code-flow-mcp
description: >
  分析 Python 代码结构，生成调用图/类图/执行流程图/MCP 调用图（.mmd + .png），
  输出 Markdown 分析报告。支持 AST 精确分析和 LLM 语义分析两种模式。
  当用户要求"分析代码""生成流程图""看调用关系""分析 MCP""代码审计"时自动激活。
---

# code-flow-mcp：代码分析 → 流程图 → 报告

基于 Python 脚本的代码分析流水线。AI 只负责**运行脚本**和**展示结果**，不手动分析代码。

---

## 触发条件

当用户表达以下意图时，**主动激活此 Skill**，无需等待用户显式输入 `/code-flow-mcp`：

| 用户意图 | 典型说法 |
|---------|---------|
| 代码分析 | "分析一下这个文件""看看代码结构""帮我审计这段代码" |
| 流程图 | "生成流程图""画个调用图""可视化代码" |
| 调用关系 | "函数调用关系""谁调了谁""调用链" |
| MCP 分析 | "MCP 调用链""工具调用分析""agent 执行流程" |
| 代码报告 | "生成分析报告""代码总结""整理一下代码结构" |
| 类结构 | "类关系""类图""继承关系" |

---

## 核心原则

- **脚本优先**：所有分析由 `Scripts/` 下的 Python 脚本完成，AI 不自行 grep
- **一键运行**：`pipeline.py` 一次跑完 5 步
- **LLM 可选**：有 API Key 出 4 张图，没有出 3 张，不中断流程

## 一键流水线

```bash
python .claude/skills/code-flow-mcp/Scripts/pipeline.py <目标文件> [输出目录]
```

默认输出到 `diagrams/<文件名>/`，包含：

| 文件 | 说明 | 数据来源 |
|------|------|---------|
| `analysis.json` | 结构化分析数据 | AST |
| `call_graph.mmd/.png` | **调用图**：函数调用拓扑 | AST |
| `class_graph.mmd/.png` | **类图**：类结构 + 方法 | AST |
| `mcp_graph.mmd/.png` | **MCP 图**：工具调用检测 | AST |
| `flow_chart.mmd/.png` | **执行流程图**：含条件分支 | LLM（可选） |
| `report.md` | 完整 Markdown 分析报告 | 以上汇总 |

## 分步执行（调试用）

```bash
# Step 1: AST 分析
python .claude/skills/code-flow-mcp/Scripts/analyze.py <目标文件> > analysis.json

# Step 2: LLM 执行流分析（可选）
python .claude/skills/code-flow-mcp/Scripts/llm_flow.py <目标文件> analysis.json > flow.json

# Step 3: 生成 Mermaid 图
cat analysis.json | python .claude/skills/code-flow-mcp/Scripts/mermaid_gen.py <输出目录> [flow.json]

# Step 4: 渲染 PNG
python .claude/skills/code-flow-mcp/Scripts/render.py <mmd目录>

# Step 5: 生成报告
python .claude/skills/code-flow-mcp/Scripts/report.py <analysis.json> <mmd目录> [report.md]
```

## 各脚本说明

| 脚本 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `analyze.py` | AST 精确解析（函数/类/import/调用/MCP） | 文件路径 | stdout JSON |
| `llm_flow.py` | LLM 语义分析提取执行步骤 | 文件 + AST JSON | flow.json |
| `mermaid_gen.py` | 生成 4 种 Mermaid 图 + 标签清洗 | stdin JSON | .mmd 文件 |
| `render.py` | .mmd → .png 渲染 | .mmd 路径 | .png 图片 |
| `report.py` | Markdown 报告组装 | JSON + .mmd | report.md |
| `pipeline.py` | 一键串联上述 5 步 | 文件路径 | 完整输出目录 |

## 输出解读

向用户说明以下内容：

1. **统计概览**：函数数、类数、import 数、调用关系数、MCP 调用数
2. **调用图**：函数之间的静态调用拓扑（谁调了谁）
3. **类图**：类定义和其方法列表
4. **MCP 图**：检测到的 MCP 工具调用，按调用方分组
5. **执行流程图**（如有 LLM）：代码实际执行路径，含条件分支和 try-catch
6. 所有文件路径告知用户

## MCP 调用识别

检测到 MCP 调用时，列出调用链路表。识别的 MCP 关键词包括：
`call_tool` `use_mcp_tool` `read_resource` `list_tools` `create_session` `agent.run` `tool.invoke` `executor.execute`

## 参考资料 References/

`References/` 下的文件是**给开发者看的脚本文档**，不是 AI 日常运行需要的指令。

- 当用户要求**修改/扩展 Skill 功能**时（如增加新的节点形状、添加 MCP 关键词），加载对应的 References 文件了解脚本设计
- 运行流水线时不需要读取它们
- 修改脚本后，同步更新 References 中的对应文档

| 文件 | 对应脚本 | 用途 |
|------|---------|------|
| `References/Mermaid规范.md` | `mermaid_gen.py` | 节点类型说明、扩展指南 |
| `References/MCP协议分析.md` | `analyze.py` / `llm_flow.py` | MCP 关键词模式、扩展指南 |
