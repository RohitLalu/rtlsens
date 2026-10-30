from rtlsens.evaluate import evaluate
from rtlsens.generate import run_generation
from rtlsens.manifest import build_manifest, validate_manifest


def test_oracle_and_controls_on_five_problems(make_cfg):
    cfg = make_cfg([{"name": "oracle", "backend": "oracle"}, {"name": "hdr", "backend": "empty_header"},
                    {"name": "mod", "backend": "empty_module"}, {"name": "prose", "backend": "prose"}],
                   n_problems=5, K=2)
    run_generation(cfg)
    df = evaluate(cfg, n_jobs=1)
    by = df.groupby("model")["cls"].agg(lambda s: set(s))
    assert by["oracle"] == {"PASS"}
    assert "PASS" not in by["hdr"] and "PASS" not in by["mod"]
    assert by["prose"] == {"NO_CODE"}


def test_manifest_valid(make_cfg):
    cfg = make_cfg([{"name": "oracle", "backend": "oracle"}])
    assert validate_manifest(build_manifest(cfg)) == []
