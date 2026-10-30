"""Code extraction rules X0/X1/X2 and module-name handling N0/N1 (DESIGN.md Section 6.3)."""
from __future__ import annotations

import re

FENCE = re.compile(r"```[ \t]*[A-Za-z0-9_+-]*[ \t]*\n(.*?)```", re.S)
# A module header must continue with a port list, parameter list or semicolon, so prose lines that
# merely start with the word "module" are not mistaken for code.
MODULE_SPAN = re.compile(
    r"(?ms)^[ \t]*module[ \t]+[A-Za-z_]\w*\s*[(;#].*?^[ \t]*endmodule\b[^\n]*"
)
MODULE_DECL = re.compile(r"(?m)^[ \t]*module[ \t]+([A-Za-z_]\w*)")


def fenced_blocks(raw: str) -> list[str]:
    return [m.group(1) for m in FENCE.finditer(raw)]


def extract_code(raw: str, rule: str) -> str | None:
    """Return the code selected by `rule`, or None when no code is found."""
    if rule == "X0":
        blocks = fenced_blocks(raw)
        code = blocks[0] if blocks else None
    elif rule == "X1":
        blocks = fenced_blocks(raw)
        code = blocks[-1] if blocks else None
    elif rule == "X2":
        m = MODULE_SPAN.search(raw)
        code = m.group(0) if m else None
    else:
        raise ValueError(f"unknown extraction rule {rule!r}")
    if code is None or not code.strip():
        return None
    return code.strip("\n") + "\n"


def apply_name_rule(code: str, rule: str) -> str:
    if rule == "N0":
        return code
    if rule != "N1":
        raise ValueError(f"unknown name rule {rule!r}")
    names = MODULE_DECL.findall(code)
    if len(names) != 1 or names[0] == "TopModule":
        return code
    name = names[0]
    code = re.sub(
        rf"(?m)^([ \t]*module[ \t]+){re.escape(name)}\b", r"\1TopModule", code, count=1
    )
    code = re.sub(rf"(\bendmodule[ \t]*:[ \t]*){re.escape(name)}\b", r"\1TopModule", code)
    return code
