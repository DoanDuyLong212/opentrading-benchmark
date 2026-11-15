#!/usr/bin/env python3
"""Bounded discovery + one tiny Gemini request; never prints credentials/raw errors."""
import json
import os
from pathlib import Path
import urllib.request
import urllib.error
import sys


def request(url, headers, body=None):
    req = urllib.request.Request(url, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": "HTTP error (body withheld)"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, {"error": type(exc).__name__}


auth = json.loads((Path.home() / ".opentrading/auth.json").read_text())
out = {}
for provider, url, envvar in [
    ("google", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000", "GOOGLE_API_KEY"),
    ("nvidia", "https://integrate.api.nvidia.com/v1/models", "NVIDIA_API_KEY")]:
    key = os.environ.get(envvar) or auth.get(provider, {}).get("key")
    if not key:
        out[provider] = {"error": "credential missing"}
        continue
    headers = {"x-goog-api-key": key} if provider == "google" else {"Authorization": "Bearer " + key}
    status, body = request(url, headers)
    credential_source = "environment" if os.environ.get(envvar) else "opentrading_auth"
    fallback = auth.get(provider, {}).get("key")
    first_status = status
    if status in (401, 403) and fallback and fallback != key:
        key = fallback
        headers = {"x-goog-api-key": key} if provider == "google" else {"Authorization": "Bearer " + key}
        status, body = request(url, headers)
        credential_source = "opentrading_auth_fallback"
    ids = [m.get("name", "").removeprefix("models/") if provider == "google" else m.get("id")
           for m in body.get("models" if provider == "google" else "data", [])]
    out[provider] = {"list_status": status, "initial_status": first_status,
                     "credential_source": credential_source, "n_models": len(ids),
                     "small_candidates": [m for m in ids if m and
                        any(s in m.lower() for s in ("flash-lite", "-1b", "-3b", "-4b", "-8b", "-7b", "nano"))]}
    if provider == "google" and "gemini-3.5-flash-lite" in ids:
        status, body = request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
                               {**headers, "Content-Type": "application/json"},
                               {"contents": [{"parts": [{"text": "Reply only OK"}]}],
                                "generationConfig": {"maxOutputTokens": 16}})
        out[provider]["tiny_generation"] = {"status": status, "usage": body.get("usageMetadata"),
            "has_text": bool(body.get("candidates", [{}])[0].get("content", {}).get("parts"))}
path = Path(sys.argv[1] if len(sys.argv) > 1 else "audits/2026-11-04/provider-probe.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(2 if any(v.get("list_status") is None for v in out.values()) else 0)
