from pathlib import Path

import pytest

from rtlsens.prompts import P1_PATTERN, P1_REPLACEMENT, build_user_prompt, p0, to_p1
from rtlsens.util import read_names


def test_p1_applies_to_every_subset_problem_and_changes_only_the_opening(base_cfg):
    d = base_cfg["dataset_dir"]
    for prob in read_names(base_cfg["subset_file"]):
        a, b = p0(d, prob), build_user_prompt(d, prob, "P1")
        assert a != b
        m = P1_PATTERN.search(a)
        assert m is not None
        assert a[: m.start()] + P1_REPLACEMENT + a[m.end():] == b


def test_p0_is_verbatim_stripped(base_cfg):
    d = base_cfg["dataset_dir"]
    raw = (Path(d) / "Prob005_notgate_prompt.txt").read_text()
    assert build_user_prompt(d, "Prob005_notgate", "P0") == raw.strip()


def test_p1_rejects_nonstandard_prompt():
    with pytest.raises(ValueError):
        to_p1("Consider the following adder-subtractor with a zero flag:")


def test_unknown_variant(base_cfg):
    with pytest.raises(ValueError):
        build_user_prompt(base_cfg["dataset_dir"], "Prob005_notgate", "P9")
