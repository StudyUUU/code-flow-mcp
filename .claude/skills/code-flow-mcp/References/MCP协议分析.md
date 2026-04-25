# MCP 协议分析（脚本开发者参考）

此文件供修改 `Scripts/analyze.py` 和 `Scripts/llm_flow.py` 时参考。

## analyze.py 中的 MCP 检测模式

`_extract_mcp_calls()` 使用以下正则匹配 MCP 调用：

```python
_MCP_PATTERNS = [
    r"\bcall_tool\s*\(",
    r"\buse_mcp_tool\s*\(",
    r"\bread_resource\s*\(",
    r"\blist_tools\s*\(",
    r"\bcreate_session\s*\(",
    r"\bagent\.run\s*\(",
    r"\btool\.invoke\s*\(",
    r"\bexecutor\.execute\s*\(",
]
```

## 扩展指南

如果需要添加新的 MCP 关键词：

1. 编辑 `analyze.py` 中的 `_MCP_PATTERNS` 列表
2. 按现有格式添加新的正则表达式
3. 不需要修改其他文件

## LLM 提示词中的 MCP 说明

`llm_flow.py` 中的 `SYSTEM_PROMPT` 定义了步骤类型中的 `mcp_call`。
如果 MCP 检测逻辑调整，需要同步更新 LLM 提示词，确保 `mcp_call` 类型能正确生成。
