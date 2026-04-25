"""code-flow-mcp: Mermaid 渲染器
将 .mmd 文件渲染为 .png 图片。
"""

import subprocess
import sys
from pathlib import Path


def render_mmd(mmd_path: str, output_path: str | None = None) -> str:
    """渲染单个 .mmd 文件为 .png"""
    mmd = Path(mmd_path)
    if not mmd.exists():
        return f"[跳过] 文件不存在: {mmd_path}"

    if output_path is None:
        output_path = mmd.with_suffix(".png")

    # 创建 puppeteer 配置避免沙盒问题
    pptr_cfg = "/tmp/puppeteer-config.json"
    pptr_content = '{"args": ["--no-sandbox", "--disable-setuid-sandbox"]}'
    Path(pptr_cfg).write_text(pptr_content, encoding="utf-8")

    # 检查 mmdc 是否可用
    try:
        subprocess.run(
            ["npx", "--yes", "@mermaid-js/mermaid-cli",
             "-i", str(mmd),
             "-o", str(output_path),
             "-p", pptr_cfg],
            capture_output=True, text=True, timeout=60,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip()
        if "No usable sandbox" in stderr:
            return f"[渲染失败] Chrome 沙盒限制，尝试手动安装: pip install mermaid-cli"
        return f"[渲染失败] {stderr[:200]}"
    except FileNotFoundError:
        return "[渲染失败] 未找到 npx，请安装 Node.js"
    except subprocess.TimeoutExpired:
        return "[渲染失败] 渲染超时 (60s)"

    # 验证输出
    out = Path(output_path)
    if out.exists() and out.stat().st_size > 1024:
        return f"[成功] {out.name} ({out.stat().st_size // 1024}KB)"
    else:
        return f"[警告] 图片已生成但文件过小 ({out.stat().st_size} bytes)"


def render_all(input_dir: str, output_dir: str | None = None) -> list[str]:
    """批量渲染目录下所有 .mmd 文件"""
    base = Path(input_dir)
    if not base.exists():
        return [f"[错误] 目录不存在: {input_dir}"]

    out_base = Path(output_dir) if output_dir else base

    results = []
    for mmd_file in sorted(base.glob("*.mmd")):
        out_path = out_base / mmd_file.with_suffix(".png").name
        result = render_mmd(str(mmd_file), str(out_path))
        results.append(f"  {mmd_file.name} → {result}")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="渲染 Mermaid 图表为 PNG")
    parser.add_argument("input", help=".mmd 文件或包含 .mmd 文件的目录")
    parser.add_argument("-o", "--output", help="输出路径（可选）")
    args = parser.parse_args()

    path = Path(args.input)
    if path.is_dir():
        results = render_all(args.input, args.output)
        print(f"渲染 {path.name}/:")
        for r in results:
            print(r)
    else:
        result = render_mmd(args.input, args.output)
        print(result)
