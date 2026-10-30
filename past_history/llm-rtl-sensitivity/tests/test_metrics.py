import itertools

import numpy as np

from rtlsens import metrics as M


def test_pass_at_1_and_run_pass():
    X = np.array([[1, 0], [1, 1], [0, 0]])
    assert M.pass_at_1(X) == 0.5
    assert np.allclose(M.run_pass(X), [2 / 3, 1 / 3])


def test_sigma_pred_hand_value():
    X = np.zeros((4, 10), dtype=int)
    X[:, :5] = 1                       # p_hat = 0.5 for all 4 problems
    v = 0.25 * 10 / 9
    assert np.isclose(M.sigma_pred(X), np.sqrt(4 * v) / 4)


def test_sigma_true():
    p = np.array([0.0, 1.0, 0.5, 0.5])
    assert np.isclose(M.sigma_true(p), np.sqrt(0.5) / 4)


def test_f_seed_matches_bruteforce():
    rng = np.random.default_rng(0)
    X = rng.integers(0, 2, size=(7, 6))
    pairs = [(a, b) for a in range(6) for b in range(6) if a != b]
    brute = np.mean([np.mean(X[:, a] != X[:, b]) for a, b in pairs])
    assert np.isclose(M.f_seed(X), brute)


def test_flips():
    A = np.array([[1, 0], [0, 0]]); B = np.array([[0, 0], [1, 0]])
    f = M.flips(A, B)
    assert f == {"gains": 0.25, "losses": 0.25, "flip": 0.5}


def test_reversal_prob_matches_bruteforce():
    A = np.array([[1, 1, 0, 1], [0, 1, 1, 0], [1, 0, 0, 0]])
    B = np.array([[0, 1, 0, 0], [1, 0, 1, 0], [0, 0, 1, 0]])
    rA, rB = A.mean(0), B.mean(0)
    s0 = np.sign(A.mean() - B.mean())
    tot = 0.0
    for a, b in itertools.product(rA, rB):
        d = a - b
        tot += 0.5 if d == 0 else float(np.sign(d) != s0)
    assert np.isclose(M.reversal_prob(A, B), tot / 16)


def test_reversal_nan_when_tied():
    A = np.array([[1, 0]]); B = np.array([[0, 1]])
    assert np.isnan(M.reversal_prob(A, B))


def test_bootstrap_is_deterministic():
    i1, i2 = M.boot_indices(10, 50, 7), M.boot_indices(10, 50, 7)
    assert (i1 == i2).all()


def test_delta_ci_zero_when_identical():
    X = np.random.default_rng(1).integers(0, 2, size=(20, 5))
    d, lo, hi = M.delta_ci(X, X, M.boot_indices(20, 200, 1))
    assert d == lo == hi == 0.0


def test_is_material_rule():
    assert M.is_material(0.07, 0.02, 0.12, 0.03)
    assert not M.is_material(0.05, 0.02, 0.08, 0.03)       # below 2*sigma
    assert not M.is_material(0.07, -0.01, 0.15, 0.03)      # CI includes 0
