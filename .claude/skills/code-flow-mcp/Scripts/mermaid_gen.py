"""code-flow-mcp: Mermaid 流程图生成器
从 analyze.py 的结构化 JSON 生成 3 种 Mermaid 图。
支持标签清洗、去重、安全节点 ID。
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


# =========================
# 清洗工具
# =========================

def sanitize_label(text: str) -> str:
    """清洗 Mermaid 节点标签，移除箭号、引号、括号等特殊字符"""
    text = text.replace("[", "(").replace("]", ")")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace('"', "'")
    text = text.replace("->", "-")  # 避免和 Mermaid 箭头语法冲突
    text = text.replace("|", "/")   # 避免和管道语法冲突
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_node_id(text: str) -> str:
    """把任意文本转为安全的节点 ID（字母数字下划线）"""
    node_id = re.sub(r"[^A-Za-z0-9_]", "_", text)
    if not node_id:
        node_id = "node"
    if not re.match(r"^[A-Za-z_]", node_id):
        node_id = f"N_{node_id}"
    return node_id


def dedupe_lines(lines: list[str]) -> list[str]:
    """去重但保持顺序"""
    seen = set()
    result = []
    for line in lines:
        key = line.strip()
        if key and key not in seen:
            seen.add(key)
            result.append(line)
    return result


# =========================
# 图 1: 调用图 (Call Graph)
# =========================

def gen_call_graph(data: dict[str, Any]) -> str:
    """从 calls 生成调用关系图"""
    calls = data.get("calls", [])
    lines = ["flowchart TD"]
    seen = set()

    if not calls:
        lines.append('    A["No calls detected"]')
        return "\n".join(lines)

    for call in calls:
        src = call["from"]
        dst = call["to"]
        if src == "<module>":
            line_text = f'    entry(["Entry: {sanitize_label(dst)}"])'
        else:
            src_id = make_node_id(src)
            dst_id = make_node_id(dst)
            line_text = f"    {src_id} --> {dst_id}"

        if line_text not in seen:
            seen.add(line_text)
            lines.append(line_text)

    return "\n".join(lines)


# =========================
# 图 2: 类关系图 (Class Graph)
# =========================

def gen_class_graph(data: dict[str, Any]) -> str:
    """从 classes 生成类结构图"""
    classes = data.get("classes", [])
    lines = ["flowchart TD"]

    if not classes:
        lines.append('    A["No classes detected"]')
        return "\n".join(lines)

    for cls in classes:
        cls_id = make_node_id(cls["name"])
        methods = cls.get("methods", [])

        lines.append(f'    subgraph {cls_id}_sub["{sanitize_label(cls["name"])}"]')
        if methods:
            for method in methods:
                mid = make_node_id(f"{cls['name']}_{method}")
                lines.append(f'        {mid}["{sanitize_label(method)}"]')
        else:
            lines.append(f"        {cls_id}_body[\"(no methods)\"]")
        lines.append("    end")

    return "\n".join(lines)


# =========================
# 图 3: MCP 调用图 (MCP Graph)
# =========================

def gen_mcp_graph(data: dict[str, Any]) -> str:
    """从 mcp_calls 生成 MCP 调用图"""
    mcp_calls = data.get("mcp_calls", [])
    functions = data.get("functions", [])
    lines = [
        "flowchart TD",
        "    classDef mcp fill:#ff6b6b,stroke:#c0392b,color:#fff",
    ]
    seen = set()

    if not mcp_calls:
        lines.append('    A["No MCP calls"]')
        return "\n".join(lines)

    for mcp in mcp_calls:
        line_no = mcp.get("line", 0)
        keyword = mcp.get("keyword", "")

        # 找所属函数（按行号匹配）
        caller = "<module>"
        for fn in functions:
            if fn.get("line", 0) <= line_no:
                caller = fn["name"]

        caller_id = make_node_id(caller)
        tool_id = make_node_id(f"mcp_{keyword}_{line_no}")
        tool_label = sanitize_label(keyword)

        caller_line = f'    {caller_id}["{sanitize_label(caller)}"]'
        tool_line = f'    {tool_id}["{tool_label}"]:::mcp'
        edge_line = f"    {caller_id} -->|{tool_label}| {tool_id}"

        for line_text in [caller_line, tool_line, edge_line]:
            if line_text not in seen:
                seen.add(line_text)
                lines.append(line_text)

    return "\n".join(lines)


# =========================
# 图 4: 执行流程图 (Flow Chart) — 需要 LLM 数据
# =========================

def gen_flow_chart(flow_data: dict[str, Any] | None) -> str:
    """从 LLM 提取的执行步骤生成流程图"""
    lines = [
        "flowchart TD",
        "    classDef mcp fill:#ff6b6b,stroke:#c0392b,color:#fff",
        "    classDef cond fill:#fff3e0,stroke:#f57c00",
    ]

    if not flow_data:
        lines.append('    A["需要 LLM API Key 才能生成执行流程图"]')
        return "\n".join(lines)

    steps = flow_data.get("steps", [])
    if not steps:
        lines.append('    A["LLM 未返回执行步骤"]')
        return "\n".join(lines)

    seen = set()

    # 先生成所有节点定义
    for s in steps:
        sid = f"S{s['step']}"
        text = sanitize_label(s["text"])
        stype = s.get("type", "")

        if stype == "entry":
            node = f'    {sid}(["{text}"])'
        elif stype == "condition":
            node = f'    {sid}{{"{text}"}}:::cond'
        elif stype == "mcp_call":
            node = f'    {sid}["{text}"]:::mcp'
        elif stype == "return":
            node = f'    {sid}(["{text}"])'
        else:
            node = f'    {sid}["{text}"]'

        if node not in seen:
            seen.add(node)
            lines.append(node)

    # 生成连线
    for i, s in enumerate(steps):
        sid = f"S{s['step']}"
        branches = s.get("branches")

        if branches:
            for br in branches:
                nid = f"S{br['next']}"
                label = sanitize_label(br["label"])
                edge = f"    {sid} -->|{label}| {nid}"
                if edge not in seen:
                    seen.add(edge)
                    lines.append(edge)
        else:
            # 按顺序连到下一条（除非是 return）
            if s.get("type") != "return" and i + 1 < len(steps):
                nid = f"S{steps[i + 1]['step']}"
                edge = f"    {sid} --> {nid}"
                if edge not in seen:
                    seen.add(edge)
                    lines.append(edge)

    return "\n".join(lines)


# =========================
# 生成全部图
# =========================

def generate_all(
    data: dict[str, Any],
    flow_data: dict[str, Any] | None = None,
) -> dict[str, str]:
    """生成全部 4 种 Mermaid 图（流程图需 LLM 数据）"""
    diagrams = {
        "call_graph": gen_call_graph(data),
        "class_graph": gen_class_graph(data),
        "mcp_graph": gen_mcp_graph(data),
    }
    # 执行流程图单独生成（可能因无 API Key 而跳过）
    diagrams["flow_chart"] = gen_flow_chart(flow_data)
    return diagrams


def save_to_file(mermaid_text: str, filepath: str):
    """保存 Mermaid 文本到 .mmd 文件"""
    Path(filepath).write_text(mermaid_text, encoding="utf-8")
    print(f"  saved: {filepath}")


# =========================
# CLI
# =========================

def main():
    if len(sys.argv) < 2:
        print("Usage: mermaid_gen.py <output_dir> [flow_json_file]", file=sys.stderr)
        sys.exit(1)

    data = json.load(sys.stdin)

    flow_data = None
    if len(sys.argv) > 2:
        flow_path = Path(sys.argv[2])
        if flow_path.exists():
            flow_data = json.loads(flow_path.read_text())

    diagrams = generate_all(data, flow_data)
    output_dir = sys.argv[1]

    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    for name, text in diagrams.items():
        filepath = base / f"{name}.mmd"
        save_to_file(text, str(filepath))
        _, stderr_msg = f"{name}: {len(text.splitlines())} lines", None


if __name__ == "__main__":
    main()
