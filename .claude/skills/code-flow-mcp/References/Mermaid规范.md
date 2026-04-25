# Mermaid 规范（脚本开发者参考）

此文件供修改 `Scripts/mermaid_gen.py` 时参考。

## mermaid_gen.py 处理的节点类型

| Mermaid 语法 | 对应函数 | 用途 |
|-------------|---------|------|
| `A["text"]` | gen_call_graph / gen_flow_chart | 普通函数/步骤 |
| `A(["text"])` | gen_flow_chart (entry/return) | 入口/返回节点 |
| `A{"text"}` | gen_flow_chart (condition) | 条件分支 |
| `A["text"]:::mcp` | gen_mcp_graph / gen_flow_chart | MCP 调用节点 |

## 关键约束

- 标签中不能包含 `[` `]` `{` `}` `"` `->` `|` — `sanitize_label()` 负责清洗
- 节点 ID 只能含字母数字下划线 — `make_node_id()` 负责转换
- 子图（subgraph）内定义的节点，外部不能直接引用

## 扩展指南

如果需要添加新的节点样式（如数据库、API 等）：

1. 在对应 gen_* 函数中添加 `classDef`
2. 在 `sanitize_label()` 中添加新的特殊字符处理（如需要）
3. 修改 `render.py` 的渲染逻辑不需要动
