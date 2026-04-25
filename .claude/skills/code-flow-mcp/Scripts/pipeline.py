"""code-flow-mcp: 全流程流水线
analyze.py → [llm_flow.py] → mermaid_gen.py → render.py → report.py
LLM 步骤可选，无 API Key 时自动跳过。
"""

import json
import subprocess
import sys
from pathlib import Path


def run_pipeline(target_file: str, output_dir: str = "diagrams") -> dict:
    """对目标文件跑完整分析流水线"""
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    target = Path(target_file)
    stem = target.stem
    result_dir = base_dir / stem
    result_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).parent

    # ── Step 1: AST 分析 ──
    print(f"[1/5] AST 代码分析...")
    analyze_result = subprocess.run(
        [sys.executable, str(script_dir / "analyze.py"), str(target)],
        capture_output=True, text=True, check=True,
    )
    analysis = json.loads(analyze_result.stdout)

    json_path = result_dir / "analysis.json"
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2))
    print(f"  → {analysis['meta']['functions']} 函数, "
          f"{analysis['meta']['calls']} 调用, "
          f"{analysis['meta']['mcp_calls']} MCP")

    if "error" in analysis:
        print(f"  ⚠ {analysis['error']}")
        return {"status": "error", "error": analysis["error"]}

    # ── Step 2: [可选] LLM 执行流分析 ──
    flow_path = result_dir / "flow.json"
    has_llm = False

    print(f"[2/5] LLM 执行流分析 (可选)...")
    # 先检查 llm_flow 是否可用
    check_llm = subprocess.run(
        [sys.executable, "-c", (
            "import sys; sys.path.insert(0, '.'); "
            "from llm_flow import is_available; "
            "exit(0 if is_available() else 1)"
        )],
        capture_output=True, text=True, cwd=script_dir,
    )

    if check_llm.returncode == 0:
        llm_result = subprocess.run(
            [sys.executable, str(script_dir / "llm_flow.py"),
             str(target), str(json_path)],
            capture_output=True, text=True, timeout=120,
        )
        if llm_result.stdout:
            flow_data = json.loads(llm_result.stdout)
            flow_path.write_text(json.dumps(flow_data, ensure_ascii=False, indent=2))

            steps = flow_data.get("steps", [])
            if steps:
                print(f"  → LLM 提取了 {len(steps)} 个执行步骤")
                has_llm = True
            else:
                note = flow_data.get("_note", flow_data.get("_error", "无步骤"))
                print(f"  → LLM 跳过: {note}")
        else:
            print(f"  → LLM 无返回")
    else:
        print(f"  → LLM 不可用（未配置 API Key），跳过")

    # ── Step 3: 生成 Mermaid 图 ──
    print(f"[3/5] 生成 Mermaid 图...")
    mermaid_args = [sys.executable, str(script_dir / "mermaid_gen.py"), str(result_dir)]
    if has_llm:
        mermaid_args.append(str(flow_path))

    mermaid_proc = subprocess.run(
        mermaid_args,
        input=json.dumps(analysis),
        capture_output=True, text=True, check=True,
    )
    for line in mermaid_proc.stdout.strip().split("\n"):
        if line.strip():
            print(f"  {line.strip()}")

    # 收集生成的 .mmd 文件
    mmd_files = list(result_dir.glob("*.mmd"))
    diagrams = {}
    for f in mmd_files:
        diagrams[f.stem] = f.read_text()

    # ── Step 4: 渲染 PNG ──
    print(f"[4/5] 渲染 PNG 图片...")
    render_proc = subprocess.run(
        [sys.executable, str(script_dir / "render.py"), str(result_dir)],
        capture_output=True, text=True, timeout=120,
    )
    for line in render_proc.stdout.strip().split("\n"):
        if line.strip():
            print(f"  {line.strip()}")

    # ── Step 5: 生成报告 ──
    print(f"[5/5] 生成报告...")
    report_path = result_dir / "report.md"
    subprocess.run(
        [sys.executable, str(script_dir / "report.py"),
         str(json_path), str(result_dir), str(report_path)],
        check=True,
    )

    # ── 完成 ──
    type_names = {"call_graph": "调用图", "class_graph": "类图",
                  "mcp_graph": "MCP 图", "flow_chart": "执行流程图"}

    print(f"\n✅ 完成！所有文件在: {result_dir}/")
    print(f"  - analysis.json  (结构化数据)")
    for f in sorted(result_dir.glob("*.mmd")):
        name = f.stem
        label = type_names.get(name, name)
        print(f"  - {f.name}  ({label})")
    for f in sorted(result_dir.glob("*.png")):
        name = f.stem
        label = type_names.get(name, name)
        if name == "flow_chart" and not has_llm:
            continue
        print(f"  - {f.name}  ({label})")
    print(f"  - report.md  (Markdown 报告)")

    if not has_llm:
        print(f"\n💡 提示：设置 DEEPSEEK_API_KEY 可启用执行流程图")

    return {"status": "ok", "output_dir": str(result_dir)}


def main():
    if len(sys.argv) < 2:
        print("用法: python pipeline.py <目标文件> [输出目录]", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "diagrams"

    result = run_pipeline(target, output_dir)
    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
