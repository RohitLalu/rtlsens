import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rtlsens.backends import OpenAICompatBackend
from rtlsens.generate import build_jobs, load_done, run_generation
from rtlsens.util import read_names

PAYLOADS: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        PAYLOADS.append(body)
        text = f"```verilog\n// seed={body['seed']} T={body['temperature']}\nmodule TopModule(); endmodule\n```"
        out = json.dumps({"choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                          "usage": {"prompt_tokens": 5, "completion_tokens": 7}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    PAYLOADS.clear()
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()


def test_payload_carries_seed_and_sampling(server):
    b = OpenAICompatBackend(server, "m")
    r1 = b.complete("sys", "usr", temperature=0.85, top_p=0.95, max_tokens=64, seed=1001, meta={})
    r2 = b.complete("sys", "usr", temperature=0.85, top_p=0.95, max_tokens=64, seed=1002, meta={})
    p = PAYLOADS[0]
    assert (p["seed"], p["temperature"], p["top_p"], p["max_tokens"], p["model"]) == (1001, 0.85, 0.95, 64, "m")
    assert p["messages"][0] == {"role": "system", "content": "sys"}
    assert r1["text"] != r2["text"] and r1["tokens_out"] == 7 and r1["finish_reason"] == "stop"


def test_generation_job_grid_and_seeds(make_cfg, server):
    cfg = make_cfg([{"name": "m", "backend": "openai_compat", "base_url": server, "model": "m"}], n_problems=2, K=3)
    probs = read_names(cfg["subset_file"])
    jobs = build_jobs(cfg, probs)
    assert len(jobs) == 1 * 2 * (2 * 3 + 2)                 # models * problems * (variants*K + T0 pair)
    assert len({j["sample_id"] for j in jobs}) == len(jobs)  # ids are unique
    summary = run_generation(cfg)
    assert summary["generated"] == len(jobs) and summary["failed"] == 0
    main_seeds = sorted({p["seed"] for p in PAYLOADS if p["temperature"] > 0})
    t0 = [p for p in PAYLOADS if p["temperature"] == 0]
    assert main_seeds == [1000, 1001, 1002]
    assert len(t0) == 4 and all(p["seed"] == 0 and p["top_p"] == 0.01 for p in t0)


def test_resume_and_truncated_last_line(make_cfg):
    cfg = make_cfg([{"name": "o", "backend": "oracle"}], n_problems=2, K=2)
    s1 = run_generation(cfg)
    path = s1["path"]
    with open(path, "a") as f:
        f.write('{"sample_id": "broken')          # simulated kill mid-write
    assert len(load_done(path)) == s1["generated"]
    s2 = run_generation(cfg)
    assert s2["generated"] == 0 and s2["already_done"] == s1["generated"]
