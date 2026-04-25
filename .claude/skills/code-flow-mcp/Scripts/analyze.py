"""code-flow-mcp: 代码分析引擎
读取 Python 文件，输出结构化 JSON 分析结果。
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def analyze_file(filepath: str) -> dict[str, Any]:
    """分析单个 Python 文件，返回结构化结果"""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"文件不存在: {filepath}"}
    if path.suffix != ".py":
        return {"error": f"不支持的文件类型: {path.suffix}"}

    source = path.read_text(encoding="utf-8")
    return analyze_source(source, str(path))


def analyze_source(source: str, name: str = "<unknown>") -> dict[str, Any]:
    """分析 Python 源码字符串，返回结构化结果"""
    # 用 ast 做精确解析
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"语法错误: {e}"}

    # 提取结构
    funcs = _extract_functions(tree)
    classes = _extract_classes(tree)
    imports = _extract_imports(tree)
    calls = _extract_calls(tree)
    mcp_calls = _extract_mcp_calls(source)

    return {
        "meta": {
            "file": name,
            "functions": len(funcs),
            "classes": len(classes),
            "imports": len(imports),
            "calls": len(calls),
            "mcp_calls": len(mcp_calls),
        },
        "functions": funcs,
        "classes": classes,
        "imports": imports,
        "calls": calls,
        "mcp_calls": mcp_calls,
    }


def _extract_functions(tree: ast.AST) -> list[dict[str, Any]]:
    """提取所有函数定义"""
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs.append({
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
            })
    return funcs


def _extract_classes(tree: ast.AST) -> list[dict[str, Any]]:
    """提取所有类定义"""
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
            })
    return classes


def _extract_imports(tree: ast.AST) -> list[dict[str, Any]]:
    """提取所有 import 语句"""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname or "",
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname or "",
                })
    return imports


def _extract_calls(tree: ast.AST) -> list[dict[str, str]]:
    """提取函数调用关系"""
    calls = []
    seen = set()

    # 先找所有函数定义和它们的函数体
    func_defs: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_defs[node.name] = node

    # 从每个函数体中提取对本文件内其他函数的调用
    for func_name, func_node in func_defs.items():
        for child in ast.walk(func_node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                callee = child.func.id
                if callee in func_defs and (func_name, callee) not in seen:
                    calls.append({"from": func_name, "to": callee})
                    seen.add((func_name, callee))

    # 提取模块级调用（不在任何函数内的直接调用）
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                callee = node.value.func.id
                if callee in func_defs and ("<module>", callee) not in seen:
                    calls.append({"from": "<module>", "to": callee})
                    seen.add(("<module>", callee))

    return calls


# MCP 调用的关键词模式
_MCP_PATTERNS = [
    re.compile(r"\bcall_tool\s*\("),
    re.compile(r"\buse_mcp_tool\s*\("),
    re.compile(r"\bread_resource\s*\("),
    re.compile(r"\blist_tools\s*\("),
    re.compile(r"\bcreate_session\s*\("),
    re.compile(r"\bagent\.run\s*\("),
    re.compile(r"\btool\.invoke\s*\("),
    re.compile(r"\bexecutor\.execute\s*\("),
]


def _extract_mcp_calls(source: str) -> list[dict[str, Any]]:
    """用行匹配提取 MCP 相关调用"""
    calls = []
    for line_no, line in enumerate(source.split("\n"), 1):
        stripped = line.strip()
        # 排除函数定义和类定义行
        if stripped.startswith("def ") or stripped.startswith("class "):
            continue
        for pattern in _MCP_PATTERNS:
            m = pattern.search(stripped)
            if m:
                calls.append({
                    "line": line_no,
                    "code": stripped,
                    "keyword": m.group(0).rstrip("("),
                })
                break
    return calls


# =========================
# CLI
# =========================

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze.py <目标文件>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    result = analyze_file(filepath)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 输出摘要到 stderr
    if "error" in result:
        print(f"[错误] {result['error']}", file=sys.stderr)
    else:
        meta = result["meta"]
        print(f"[摘要] {meta['functions']} 个函数, {meta['classes']} 个类, "
              f"{meta['calls']} 条调用, {meta['mcp_calls']} 个 MCP 调用",
              file=sys.stderr)


if __name__ == "__main__":
    main()
