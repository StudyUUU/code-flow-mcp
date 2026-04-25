"""code-flow-mcp: Markdown 报告生成器
将分析结果组装为可读的 Markdown 报告。
"""

import json
import sys
from pathlib import Path
from typing import Any


def generate_report(data: dict[str, Any], diagrams: dict[str, str]) -> str:
    """生成完整的 Markdown 分析报告"""
    sections = [_build_header(data)]

    sections.append(_build_overview(data))
    sections.append(_build_functions(data))
    sections.append(_build_classes(data))
    sections.append(_build_imports(data))
    sections.append(_build_calls(data))
    sections.append(_build_mcp_calls(data))
    sections.append(_build_diagrams(diagrams))

    sections.append("---\n*报告由 code-flow-mcp 自动生成*")
    return "\n\n".join(sections)


def _build_header(data: dict[str, Any]) -> str:
    meta = data.get("meta", {})
    return (
        f"# 代码分析报告\n\n"
        f"- **文件**: {meta.get('file', '未知')}\n"
        f"- **函数数**: {meta.get('functions', 0)}\n"
        f"- **类数**: {meta.get('classes', 0)}\n"
        f"- **调用关系**: {meta.get('calls', 0)} 条\n"
        f"- **MCP 调用**: {meta.get('mcp_calls', 0)} 处\n"
    )


def _build_overview(data: dict[str, Any]) -> str:
    meta = data.get("meta", {})
    if meta.get("error"):
        return f"## 分析失败\n\n{meta['error']}"
    return f"## 概览\n\n" + _overview_table(meta)


def _overview_table(meta: dict) -> str:
    return (
        "| 指标 | 数值 |\n"
        "|------|------|\n"
        f"| 函数 | {meta.get('functions', 0)} |\n"
        f"| 类 | {meta.get('classes', 0)} |\n"
        f"| 引用 | {meta.get('imports', 0)} |\n"
        f"| 调用关系 | {meta.get('calls', 0)} |\n"
        f"| MCP 调用 | {meta.get('mcp_calls', 0)} |\n"
    )


def _build_functions(data: dict[str, Any]) -> str:
    funcs = data.get("functions", [])
    if not funcs:
        return "## 函数\n\n无"

    lines = ["## 函数\n", "| 名称 | 行号 | 参数 |", "|------|------|------|"]
    for fn in funcs:
        args = ", ".join(fn.get("args", []))
        lines.append(f"| `{fn['name']}` | {fn['line']} | `{args}` |")
    return "\n".join(lines)


def _build_classes(data: dict[str, Any]) -> str:
    classes = data.get("classes", [])
    if not classes:
        return "## 类\n\n无"

    lines = ["## 类\n"]
    for cls in classes:
        methods = cls.get("methods", [])
        if methods:
            method_list = ", ".join(f"`{m}`" for m in methods)
            lines.append(f"- **{cls['name']}** (行 {cls['line']}): {method_list}")
        else:
            lines.append(f"- **{cls['name']}** (行 {cls['line']}): 无方法")
    return "\n".join(lines)


def _build_imports(data: dict[str, Any]) -> str:
    imports = data.get("imports", [])
    if not imports:
        return "## 引用\n\n无"

    lines = ["## 引用\n", "| 类型 | 模块 | 导入项 |", "|------|------|--------|"]
    for imp in imports:
        if imp["type"] == "import":
            alias = f" as {imp['alias']}" if imp["alias"] else ""
            lines.append(f"| import | `{imp['module']}{alias}` | — |")
        else:
            alias = f" as {imp['alias']}" if imp["alias"] else ""
            lines.append(f"| from | `{imp['module']}` | `{imp['name']}{alias}` |")
    return "\n".join(lines)


def _build_calls(data: dict[str, Any]) -> str:
    calls = data.get("calls", [])
    if not calls:
        return "## 调用关系\n\n无"

    lines = ["## 调用关系\n", "| 调用方 | 被调用方 |", "|--------|----------|"]
    for call in calls:
        src = call["from"] if call["from"] != "<module>" else "**模块级**"
        lines.append(f"| `{src}` → | `{call['to']}` |")
    return "\n".join(lines)


def _build_mcp_calls(data: dict[str, Any]) -> str:
    mcp = data.get("mcp_calls", [])
    if not mcp:
        return "## MCP 调用\n\n无"

    lines = ["## MCP 调用\n", "| 行号 | 关键词 | 代码 |", "|------|--------|------|"]
    for call in mcp:
        code = call.get("code", "")
        lines.append(f"| {call.get('line', '')} | `{call.get('keyword', '')}` | `{code[:60]}` |")
    return "\n".join(lines)


def _build_diagrams(diagrams: dict[str, str]) -> str:
    if not diagrams:
        return "## 图表\n\n未生成"

    lines = ["## Mermaid 图表\n"]
    for name, text in diagrams.items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"```mermaid\n{text}\n```")
        lines.append("")
    return "\n".join(lines)


# =========================
# CLI
# =========================

def main():
    # 用法: python report.py <data.json> [diagrams_dir]
    if len(sys.argv) < 2:
        print("用法: python report.py <analysis.json> [diagrams_dir] [output.md]",
              file=sys.stderr)
        sys.exit(1)

    data_path = Path(sys.argv[1])
    data = json.loads(data_path.read_text(encoding="utf-8"))

    diagrams_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    diagrams = {}
    if Path(diagrams_dir).exists():
        for mmd_file in sorted(Path(diagrams_dir).glob("*.mmd")):
            diagrams[mmd_file.stem] = mmd_file.read_text(encoding="utf-8")

    report = generate_report(data, diagrams)

    if len(sys.argv) > 3:
        out_path = Path(sys.argv[3])
        out_path.write_text(report, encoding="utf-8")
        print(f"报告已保存: {out_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
