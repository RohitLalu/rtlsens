"""Prompt construction: P0 (original) and P1 (neutral rewrite of the opening sentence)."""
from __future__ import annotations

import re
from pathlib import Path

P1_PATTERN = re.compile(
    r"I would like you to implement a module named TopModule with the following\s+interface\."
)
P1_REPLACEMENT = "Please write a SystemVerilog module named TopModule that has the following interface."


def load_system_prompt(cfg: dict) -> str:
    return Path(cfg["system_prompt_file"]).read_text().strip()


def p0(dataset_dir: str, problem: str) -> str:
    return (Path(dataset_dir) / f"{problem}_prompt.txt").read_text().strip()


def to_p1(text: str) -> str:
    new, n = P1_PATTERN.subn(P1_REPLACEMENT, text, count=1)
    if n != 1:
        raise ValueError("P1 rewrite did not match exactly once; problem is not eligible")
    return new


def build_user_prompt(dataset_dir: str, problem: str, variant: str) -> str:
    text = p0(dataset_dir, problem)
    if variant == "P0":
        return text
    if variant == "P1":
        return to_p1(text)
    raise ValueError(f"unknown prompt variant {variant!r}")
