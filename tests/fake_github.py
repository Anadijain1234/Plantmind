"""A tiny in-memory stand-in for the GitHub contents API, used by tests/test_backup.py."""
import json, base64, os, hashlib
from types import SimpleNamespace as NS
STORE = os.environ.get("FAKE_GITHUB_FILE", "/tmp/fakegh.json")
def load(): return json.load(open(STORE)) if os.path.exists(STORE) else {"branches": {"main": "abc"}, "files": {}}
def save(d): json.dump(d, open(STORE, "w"))
class R:
    def __init__(self, code, data=None, content=b""): self.status_code, self._d, self.content, self.text = code, data, content, json.dumps(data)
    def json(self): return self._d
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f"HTTP {self.status_code}")
DOWN = {"v": False}
CALLS = []
def api(method, url, **kw):
    CALLS.append((method, url))
    if DOWN["v"]: return R(500, {"message": "down"})
    d = load(); repo = "/repos/me/repo"
    if url == f"{repo}/branches/ustaad-data": return R(200 if "ustaad-data" in d["branches"] else 404, {})
    if url == repo: return R(200, {"default_branch": "main"})
    if url == f"{repo}/git/ref/heads/main": return R(200, {"object": {"sha": d["branches"]["main"]}})
    if url == f"{repo}/git/refs" and method == "POST":
        d["branches"]["ustaad-data"] = kw["json"]["sha"]; save(d); return R(201, {})
    if url == f"{repo}/contents/ustaad-backup.json":
        f = d["files"].get("ustaad-data")
        if method == "GET":
            return R(200, {"sha": f["sha"], "content": f["content"]}) if f else R(404, {})
        if method == "PUT":
            if "ustaad-data" not in d["branches"]: return R(404, {})
            if f and kw["json"].get("sha") != f["sha"]: return R(409, {})
            sha = hashlib.sha1(kw["json"]["content"].encode()).hexdigest()
            d["files"]["ustaad-data"] = {"sha": sha, "content": kw["json"]["content"]}; save(d)
            return R(200, {"content": {"sha": sha}})
    return R(404, {})
