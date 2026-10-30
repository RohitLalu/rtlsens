from rtlsens.extract import apply_name_rule, extract_code, fenced_blocks

DUT = "module TopModule(input a, output b);\n  assign b = a;\nendmodule\n"


def test_single_fence_all_rules():
    raw = f"Sure:\n```verilog\n{DUT}```\nDone."
    assert extract_code(raw, "X0") == DUT
    assert extract_code(raw, "X1") == DUT
    assert extract_code(raw, "X2") == DUT


def test_two_fences_first_vs_last():
    tb = "module tb;\nendmodule\n"
    raw = f"```verilog\n{DUT}```\ntext\n```systemverilog\n{tb}```\n"
    assert extract_code(raw, "X0") == DUT
    assert extract_code(raw, "X1") == tb
    assert extract_code(raw, "X2") == DUT


def test_no_fence():
    raw = f"Here you go:\n{DUT}\nThis module is simple."
    assert extract_code(raw, "X0") is None
    assert extract_code(raw, "X1") is None
    assert extract_code(raw, "X2") == DUT


def test_x2_ignores_prose_mentioning_module():
    raw = "This module does X.\nmodule is a keyword.\n" + DUT
    assert extract_code(raw, "X2") == DUT


def test_unclosed_fence_is_no_code():
    raw = "```verilog\nmodule TopModule(); assign"
    assert extract_code(raw, "X0") is None


def test_empty_block_is_no_code():
    assert extract_code("```verilog\n\n```", "X0") is None


def test_fence_without_language_tag():
    assert fenced_blocks(f"```\n{DUT}```") == [DUT]


def test_rename_single_module():
    code = DUT.replace("TopModule", "top_module") .replace("endmodule", "endmodule : top_module")
    out = apply_name_rule(code, "N1")
    assert "module TopModule(" in out and "endmodule : TopModule" in out
    assert "top_module" not in out


def test_rename_keeps_signal_names():
    code = "module foo(input foo_in, output foo_out);\nassign foo_out = foo_in;\nendmodule\n"
    out = apply_name_rule(code, "N1")
    assert "foo_in" in out and "foo_out" in out and out.startswith("module TopModule(")


def test_no_rename_for_two_modules_or_correct_name_or_N0():
    two = "module a();\nendmodule\nmodule b();\nendmodule\n"
    assert apply_name_rule(two, "N1") == two
    assert apply_name_rule(DUT, "N1") == DUT
    wrong = DUT.replace("TopModule", "x")
    assert apply_name_rule(wrong, "N0") == wrong
