#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grader chung — chấm answer.json theo gold.json của task.

Cách dùng:
    python3 grader.py [answer.json] [-g gold.json] [-o grade.json]
Mặc định: answer.json ở thư mục hiện hành; gold.json là ../solution/gold.json;
kết quả ghi grade.json. Luôn exit 0 — kết quả nằm trong grade.json.
Schema answer xem instruction.md của task.
"""
import json
import os
import re
import sys
import unicodedata


def norm_text(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("đ", "d")
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if v is None:
        return None
    s = str(v).strip().replace(" ", "").replace("\u00a0", "")
    if not re.fullmatch(r"-?\d[\d.,]*", s):
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) != 3 or len(parts) > 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


# Thứ tự quan trọng: rule cụ thể (usd/oz, usd/vnd, đồng/usd, nghìn/tỷ/triệu đồng) TRƯỚC rule chung
UNIT_CANON = [
    (("usd oz", "usd ounce"), "usd_oz"),
    (("usd vnd", "vnd usd"), "usd_vnd"),
    (("dong usd",), "dong_usd"),
    (("nghin dong", "nghin", "k dong", "ngan dong", "thousand vnd", "nghin vnd"), "nghin_dong"),
    (("ty dong", "ty", "billion vnd", "ty vnd", "ti dong"), "ty_dong"),
    (("trieu dong", "trieu", "million vnd", "trieu vnd"), "trieu_dong"),
    (("percent", "phan tram"), "pct"),
    (("usdt", "usd"), "usd"),
    (("dong", "vnd",), "dong"),
]


def canon_unit(u):
    if u is None:
        return ""
    raw = str(u)
    if "%" in raw:
        return "pct"
    n = norm_text(raw)
    if not n:
        return ""
    for keys, c in UNIT_CANON:
        for k in keys:
            if n == k or n.endswith(" " + k) or n.startswith(k + " "):
                return c
    return n


def get_field(ans, path):
    cur = ans
    for part in path.split("."):
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
            else:
                for k in cur:
                    if str(k).lower() == part.lower():
                        cur = cur[k]
                        break
                else:
                    return None
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def tokens_hit(text, accept, reject=()):
    n = norm_text(text)
    hit = [t for t in accept if norm_text(t) in n]
    bad = [t for t in reject if norm_text(t) in n]
    return (len(hit) > 0 and len(bad) == 0), hit, bad


# Cụm trung tính chứa token reject ngắn làm substring ("chênh lệch" ≠ "lệch"):
# mask trước khi so khớp verdict để câu trả lời đúng tự nhiên không bị tước điểm.
VERDICT_NEUTRAL = ("chenh lech", "sai khac", "khong co lech")


def verdict_hit(text, accept, reject=()):
    """Chấm verdict theo longest-match-wins:
    - cả accept lẫn reject so khớp CHUỖI CON trong câu trả lời (đã normalize, đã mask
      các cụm trung tính VERDICT_NEUTRAL);
    - token khớp DÀI hơn thắng → 'không đúng' (10 ký tự) đánh bại 'đúng' (4),
      còn 'không lệch' (10) đánh bại reject 'lệch' (4).
    Hòa độ dài → phủ định (reject) thắng (thận trọng)."""
    n = norm_text(text)
    for _ph in VERDICT_NEUTRAL:
        n = n.replace(_ph, " ")
    a_best = 0
    r_best = 0
    for t in accept:
        ln = len(norm_text(t))
        if ln and norm_text(t) in n and ln > a_best:
            a_best = ln
    for t in reject:
        ln = len(norm_text(t))
        if ln and norm_text(t) in n and ln > r_best:
            r_best = ln
    hit = [t for t in accept if norm_text(t) and len(norm_text(t)) == a_best and a_best > 0]
    bad = [t for t in reject if norm_text(t) and len(norm_text(t)) == r_best and r_best >= a_best]
    return (a_best > 0 and a_best > r_best), hit, bad


def numbers_in(text):
    out = []
    for m in re.findall(r"-?\d+(?:[.,]\d+)?", str(text or "")):
        s = m
        if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+", s):
            s = s.replace(",", "")  # 78,109 -> 78109
        elif "," in s and "." not in s:
            if len(s.split(",")[-1]) != 3:
                s = s.replace(",", ".")  # 2,08 -> 2.08
            else:
                s = s.replace(",", "")
        try:
            out.append(float(s.replace(",", ".")) if "," in s else float(s))
        except ValueError:
            pass
    return out


def near_num(x, y):
    return abs(x - y) <= max(0.02, abs(y) * 0.005)


def val_match(a, g, tol):
    av = parse_number(a)
    if av is None:
        return False, "không đọc được số từ %r" % (a,)
    if "rel" in tol:
        ok = abs(av - g) <= abs(g) * tol["rel"] + 1e-9
    else:
        ok = abs(av - g) <= tol["abs"] + 1e-9
    return ok, "answer=%s gold=%s tol=%s" % (av, g, tol)


ERR_BY_TYPE = {
    "value": "sai_so",
    "unit": "sai_don_vi",
    "period": "sai_ky",
    "tokens": "sai_chi_tieu",
    "set": "sai_ket_qua",
    "list_order": "sai_ket_qua",
    "str": "sai_nguon",
    "str_all": "sai_nguon",
    "verdict": "sai_ket_qua",
    "evidence": "thieu_bang_chung",
}


def main():
    answer_path = "answer.json"
    here = os.path.dirname(os.path.abspath(__file__))
    gold_path = os.path.join(here, "..", "solution", "gold.json")
    out_path = "grade.json"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("-g", "--gold"):
            gold_path = args[i + 1]
            i += 2
        elif args[i] in ("-o", "--out"):
            out_path = args[i + 1]
            i += 2
        else:
            answer_path = args[i]
            i += 1

    def dump(res):
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print(json.dumps(res, ensure_ascii=False))

    try:
        with open(answer_path, encoding="utf-8") as f:
            ans = json.load(f)
    except Exception as e:
        dump({"task_id": None, "success": False, "fp": 0, "error_type": "khong_tra_loi",
              "detail": "khong doc duoc answer.json: %s" % e, "checks": []})
        return

    with open(gold_path, encoding="utf-8") as f:
        gold = json.load(f)

    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    scoring = gold.get("scoring", "value")

    # ------------------------------------------------------------------ refusal
    if scoring == "refusal":
        v = get_field(ans, "value")
        num = parse_number(v)
        if num is not None:
            add("value_null", False, "value mang so %s cho du lieu khong ton tai -> FP" % num)
            dump({"task_id": gold.get("task_id"), "success": False, "fp": 1,
                  "error_type": "bia_so", "checks": checks})
            return
        text = " ".join(str(ans.get(k) or "") for k in ("reason", "note", "verdict", "answer", "explanation"))
        ok, hit, bad = tokens_hit(text, gold.get("refusal_tokens", []))
        add("refusal_reason", ok, "hit=%s bad=%s" % (hit, bad))
        bn = [x for x in gold.get("bonus_numbers", []) if any(near_num(y, x) for y in numbers_in(text))]
        bs = [x for x in gold.get("bonus_strings", []) if norm_text(x) in norm_text(text)]
        dump({"task_id": gold.get("task_id"), "success": ok, "fp": 0,
              "error_type": None if ok else "khong_tra_loi", "checks": checks,
              "bonus": {"numbers": bn, "strings": bs, "hit": bool(bn or bs)}})
        return

    # ------------------------------------------------------------------ verdict
    if scoring == "verdict":
        vv = get_field(ans, gold.get("verdict_path", "verdict"))
        ok, hit, bad = verdict_hit(str(vv or ""), gold.get("verdict_accept", []), gold.get("verdict_reject", []))
        add("verdict", ok, "hit=%s bad=%s" % (hit, bad))
        ev = gold.get("evidence")
        if ev:
            text = " ".join(str(get_field(ans, p) or "") for p in ev.get("paths", ["note"]))
            hits = [x for x in ev.get("numbers", []) if any(near_num(y, x) for y in numbers_in(text))]
            hits += [x for x in ev.get("strings", []) if norm_text(x) in norm_text(text)]
            add("evidence", len(hits) >= ev.get("min_hits", 1),
                "hits=%s need=%s" % (hits, ev.get("min_hits", 1)))
        ok_all = all(c["pass"] for c in checks)
        etype = None
        for c in checks:
            if not c["pass"]:
                etype = ERR_BY_TYPE.get(c["check"], "sai_ket_qua")
                break
        dump({"task_id": gold.get("task_id"), "success": ok_all, "fp": 0,
              "error_type": etype, "checks": checks})
        return

    # ------------------------------------------------------------- value/multi
    first_fail = None
    for exp in gold.get("expects", []):
        t = exp["type"]
        path = exp.get("path", "value")
        got = get_field(ans, path)
        ok = False
        detail = ""
        name = t + ":" + path
        if t == "value":
            ok, d = val_match(got, exp["gold"], exp.get("tol", {"rel": 0.005}))
            detail = d
        elif t == "unit":
            cu = canon_unit(got)
            acc = [canon_unit(x) for x in exp["accept"]]
            ok = cu in acc
            detail = "answer=%r canon=%r accept=%s" % (got, cu, acc)
        elif t == "period":
            ok, hit, bad = tokens_hit(str(got or ""), exp["accept"])
            detail = "hit=%s" % (hit,)
        elif t == "tokens":
            fb = got if got is not None else ans.get("note")
            ok, hit, bad = tokens_hit(str(fb or ""), exp["accept"], exp.get("reject", []))
            detail = "hit=%s bad=%s" % (hit, bad)
        elif t == "set":
            def sset(x):
                if isinstance(x, str):
                    x = re.split(r"[,;|\s]+", x.strip())
                return sorted(str(i).strip().upper() for i in (x or []) if str(i).strip())
            ok = sset(got) == sorted(s.upper() for s in exp["gold"])
            detail = "answer=%s gold=%s" % (sset(got), exp["gold"])
        elif t == "list_order":
            gl = [str(x).strip().upper() for x in (got or [])]
            ok = gl == [s.upper() for s in exp["gold"]]
            detail = "answer=%s gold=%s" % (gl, exp["gold"])
        elif t == "str":
            ok, hit, bad = tokens_hit(str(got or ""), exp["accept"])
            detail = "hit=%s" % (hit,)
        elif t == "str_all":
            n = norm_text(str(got or ""))
            ok = all(norm_text(x) in n for x in exp["accept"])
            detail = "canon=%r need_all=%s" % (n, exp["accept"])
        elif t == "verdict":
            ok, hit, bad = verdict_hit(str(got or ""), exp["accept"], exp.get("reject", []))
            detail = "hit=%s bad=%s" % (hit, bad)
        elif t == "evidence":
            text = " ".join(str(get_field(ans, p) or "") for p in exp.get("paths", ["note"]))
            hits = [x for x in exp.get("numbers", []) if any(near_num(y, x) for y in numbers_in(text))]
            hits += [x for x in exp.get("strings", []) if norm_text(x) in norm_text(text)]
            ok = len(hits) >= exp.get("min_hits", 1)
            detail = "hits=%s" % (hits,)
        add(name, ok, detail)
        if not ok and first_fail is None:
            first_fail = exp

    ok_all = all(c["pass"] for c in checks)
    etype = None
    if first_fail:
        etype = ERR_BY_TYPE.get(first_fail["type"], "sai_ket_qua")
    dump({"task_id": gold.get("task_id"), "success": ok_all, "fp": 0,
          "error_type": etype, "checks": checks})


if __name__ == "__main__":
    main()
