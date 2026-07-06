#!/usr/bin/env python3
"""Recover approximate Python source from CPython 3.10 .pyc using xdis."""
from __future__ import annotations

import argparse
import re
from typing import Any

from xdis import load_module


def fmt_const(c: Any) -> str:
    if c is None:
        return "None"
    if isinstance(c, bool):
        return "True" if c else "False"
    if isinstance(c, (int, float)):
        return repr(c)
    if isinstance(c, str):
        return repr(c)
    if isinstance(c, bytes):
        return repr(c)
    if isinstance(c, tuple):
        if not c:
            return "()"
        return "(" + ", ".join(fmt_const(x) for x in c) + ("," if len(c) == 1 else "") + ")"
    if hasattr(c, "co_name"):
        return f"<code:{c.co_name}>"
    return repr(c)


def render_function(co, indent: int = 0) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    args = list(co.co_varnames[: co.co_argcount])
    sig = ", ".join(args) if args else ""
    lines.append(f"{pad}def {co.co_name}({sig}):")
    doc = co.co_consts[0] if co.co_consts and isinstance(co.co_consts[0], str) else None
    if doc and co.co_name not in ("<module>",):
        lines.append(f'{pad}    """{doc}"""')

  # child code objects
    child_blocks: list[str] = []
    for c in co.co_consts:
        if hasattr(c, "co_name"):
            child_blocks.extend(render_function(c, indent + 4))

    # string constants used in this function (API paths, messages)
    strs = [c for c in co.co_consts if isinstance(c, str) and len(c) > 1]
    if strs:
        lines.append(f"{pad}    # recovered string constants:")
        for s in sorted(set(strs), key=len):
            if any(k in s for k in ("/api", "http", "create", "query", "setsms", "订单", "验证码", "余额", "参考")):
                lines.append(f"{pad}    # {s!r}")

    if child_blocks:
        lines.append(f"{pad}    # nested functions:")
        lines.extend(child_blocks)

    if len(lines) == 1:
        lines.append(f"{pad}    pass  # bytecode at line {co.co_firstlineno}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pyc")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    _, _, _, co, _, _, _ = load_module(args.pyc)
    out: list[str] = [
        '"""Recovered from bytecode; nested logic may be incomplete."""',
        "from __future__ import annotations",
        "",
    ]
    out.extend(render_function(co))
    text = "\n".join(out) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
