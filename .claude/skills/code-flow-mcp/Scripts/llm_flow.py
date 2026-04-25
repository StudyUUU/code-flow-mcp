"""code-flow-mcp: LLM 执行流分析
将源码 + AST 分析结果发给 LLM，提取执行流程图所需的结构化步骤。
可选步骤：没有 API Key 时跳过，不影响其他三张图。
"""

import json
import os
import sys
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


# =========================
# 配置
# =========================

def _get_config() -> dict:
    """从环境变量读取 LLM 配置"""
    api_key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    return {"api_key": api_key, "base_url": base_url, "model": model}


def is_available() -> bool:
    """检查是否有可用的 LLM 配置"""
    cfg = _get_config()
    return bool(cfg["api_key"]) and httpx is not None


# =========================
# LLM 调用
# =========================

SYSTEM_PROMPT = """你是一个代码执行流分析引擎。
你的任务是分析 Python 代码的执行流程，输出结构化的步骤列表。

规则：
1. 只输出一个 JSON 对象，不要解释、不要 Markdown 代码块
2. 按代码实际执行顺序列出步骤
3. 每个步骤包含：step(序号), type(步骤类型), text(简短描述)
4. 步骤类型只能是以下之一：
   - "entry" 程序/函数入口
   - "call" 函数调用
   - "condition" 条件判断 (if/elif/else/ ternary)
   - "loop" 循环 (for/while)
   - "mcp_call" MCP/工具调用 (call_tool, agent.run 等)
   - "output" 输出 (print, write 等)
   - "return" 返回值
5. 条件步骤必须有 branches 字段: [{"label": "是/否/其他", "next": 步骤号}]
6. 如果代码中有 try/except，用 condition 类型表示分支
7. text 字段要简短（10 字以内），用中文
8. 最后一步的 next 为 null

输出格式：
{
  "steps": [
    {"step": 1, "type": "entry", "text": "main入口"},
    {"step": 2, "type": "call", "text": "创建对象"},
    {"step": 3, "type": "condition", "text": "校验结果", "branches": [{"label": "通过", "next": 4}, {"label": "失败", "next": 5}]}
  ]
}
"""


def build_user_prompt(code: str, ast_info: dict) -> str:
    """构造用户提示词"""
    summary = {
        "functions": [f["name"] for f in ast_info.get("functions", [])],
        "classes": [c["name"] for c in ast_info.get("classes", [])],
        "calls": ast_info.get("calls", []),
        "mcp_calls": ast_info.get("mcp_calls", []),
    }

    return f"""分析以下 Python 代码的执行流程：

## 代码
```python
{code}
```

## AST 预分析（供参考）
{json.dumps(summary, ensure_ascii=False, indent=2)}

请按实际执行顺序输出步骤列表。"""


def call_llm(code: str, ast_info: dict, max_retries: int = 2) -> dict[str, Any]:
    """调用 LLM 获取执行流分析"""
    cfg = _get_config()
    if not cfg["api_key"]:
        return {"steps": [], "_note": "未配置 LLM API Key"}

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(code, ast_info)},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=60, trust_env=False) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

            # 尝试解析 JSON
            return _parse_llm_response(content)

        except Exception as e:
            last_error = str(e)

    return {"steps": [], "_error": f"LLM 调用失败: {last_error}"}


def _parse_llm_response(content: str) -> dict[str, Any]:
    """解析 LLM 返回的内容，提取 JSON"""
    # 去掉可能的 ```json 包装
    import re

    text = content.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {"steps": [], "_error": "LLM 返回内容不含 JSON"}

    return json.loads(text[start : end + 1])


# =========================
# CLI
# =========================

def main():
    if len(sys.argv) < 2:
        print("Usage: llm_flow.py <source_file> [ast_json_file]")
        print("  If ast_json_file is omitted, runs analyze.py first")
        sys.exit(1)

    source_file = sys.argv[1]
    source_code = open(source_file, encoding="utf-8").read()

    if len(sys.argv) > 2:
        ast_info = json.loads(open(sys.argv[2], encoding="utf-8").read())
    else:
        # 自动运行 analyze.py
        from analyze import analyze_file
        ast_info = analyze_file(source_file)

    if not is_available():
        result = {"steps": [], "_note": "LLM 不可用（未配置 API Key 或缺少 httpx）"}
    else:
        result = call_llm(source_code, ast_info)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if "_error" in result:
        print(f"[LLM Error] {result['_error']}", file=sys.stderr)
    elif result.get("steps"):
        print(f"[LLM OK] {len(result['steps'])} steps extracted", file=sys.stderr)
    else:
        print(f"[LLM Skip] {result.get('_note', '')}", file=sys.stderr)


if __name__ == "__main__":
    main()
