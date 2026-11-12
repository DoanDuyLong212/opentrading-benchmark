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
import math
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
        try:
            number = float(v)
            return number if math.isfinite(number) else None
        except (ValueError, OverflowError):
            return None
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
        value = float(s)
        return value if math.isfinite(value) else None
    except ValueError:
        return None


# Thứ tự quan trọng: rule cụ thể (usd/oz, usd/vnd, đồng/usd, nghìn/tỷ/triệu đồng) TRƯỚC rule chung
UNIT_CANON = [
    (("usd oz", "usd ounce"), "usd_oz"),
    (("usd vnd",), "usd_per_vnd"),
    (("vnd usd", "dong usd"), "vnd_per_usd"),
    (("nghin dong", "nghin", "k dong", "ngan dong", "thousand vnd", "nghin vnd"), "nghin_dong"),
    (("ty dong", "ty", "billion vnd", "ty vnd", "ti dong"), "ty_dong"),
    (("trieu dong", "trieu", "million vnd", "trieu vnd"), "trieu_dong"),
    (("percent", "phan tram"), "pct"),
    (("usdt",), "usdt"),
    (("usd",), "usd"),
    (("dong", "vnd",), "dong"),
]


def canon_unit(u):
    if u is None:
        return ""
    raw = str(u)
    if re.search(r"\b(khong|not|without|except)\b", norm_text(raw)):
        return ""
    if re.search(r"\b(va|hoac|hay|and|or|but)\b", norm_text(raw)):
        return ""
    if "%" in raw and re.search(r"\b(usd|usdt|vnd|dong|jpy|eur|cny)\b", norm_text(raw)):
        return ""
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


def phrase_present(text, phrase):
    n, p = norm_text(text), norm_text(phrase)
    return bool(p and re.search(r"(?:^| )" + re.escape(p) + r"(?: |$)", n))


def tokens_hit(text, accept, reject=()):
    hit = [t for t in accept if phrase_present(text, t)]
    bad = [t for t in reject if phrase_present(text, t)]
    return bool(hit and not bad), hit, bad


def refusal_hit(text, accept):
    # Vietnamese passive voice does not change the availability assertion:
    # "không được tìm thấy" and "không tìm thấy" mean the same thing.
    # Restrict rewriting to availability predicates rather than deleting every
    # occurrence of "được", which could alter unrelated financial statements.
    n = norm_text(text)
    n = re.sub(r"\b(khong|chua) (?:duoc|bi) (tim thay|cong bo|phat hanh|ghi nhan)\b", r"\1 \2", n)
    hit = [t for t in accept if phrase_present(n, t)]
    bad = []
    for token in hit:
        phrase = norm_text(token)
        for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", n):
            prefix = n[:match.start()]
            if re.search(r"\b(khong|chang|not)(?: phai(?: la)?| dung| the noi rang)?\s*$", prefix):
                bad.append("negated refusal: " + token)
    # Mask the accepted negative assertions before checking an opposite claim.
    # This prevents "không tìm thấy, nhưng đã tìm thấy" from passing simply
    # because the first clause contains a refusal keyword.
    remainder = n
    for token in sorted(hit, key=lambda t: len(norm_text(t)), reverse=True):
        remainder = re.sub(r"(?<!\w)" + re.escape(norm_text(token)) + r"(?!\w)", " ", remainder)
    if re.search(r"\b(?:(?:da|van|co|duoc) (?:duoc )?(?:tim thay|cong bo|phat hanh)|(?:van|co) ton tai|(?:van|da) co (?:du lieu|so lieu))\b", remainder):
        bad.append("contradictory availability assertion")
    return bool(hit and not bad), hit, bad


def source_hit(text, accept, require_all=False):
    if not isinstance(text, str) or re.search(r"\b(khong|not|ngoai|except|without)\b", norm_text(text)):
        return False
    # source is the tool namespace; provider names belong to evidence[].source.
    expected = {norm_text(x) for x in accept}
    if not require_all:
        return norm_text(text) in expected
    parts = [norm_text(x) for x in re.split(r"[,;+|/]|\bvà\b|\bva\b|\band\b|&", text.lower()) if norm_text(x)]
    return set(parts) == expected


def period_hit(text, accept):
    if not isinstance(text, str):
        return False
    n = norm_text(text)
    if re.search(r"\b(khong|not|except|ngoai)\b", n):
        return False
    joined = " ".join(accept)
    expected_years = set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", joined))
    actual_years = set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text))
    if actual_years and expected_years and not actual_years <= expected_years:
        return False
    def quarters(value):
        return {(int(q), int(y) + (2000 if len(y)==2 else 0))
                for q,y in re.findall(r"(?:q|quy)\s*([1-4])\s*(?:[/ .-]|nam)*\s*(20\d{2}|\d{2})(?!\d)", norm_text(value))}
    eq, aq = quarters(joined), quarters(text)
    if eq:
        return aq == eq
    def dates(value):
        found = {(int(y), int(m), int(d)) for y,m,d in re.findall(r"(?<!\d)((?:19|20)\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)", value)}
        found.update(((int(y) + 2000 if len(y)==2 else int(y)) if y else None, int(m), int(d)) for d,m,y in re.findall(
            r"(?<![\d-])(\d{1,2})[/.-](\d{1,2})(?:[/.-]((?:19|20)\d{2}|\d{2}))?(?!\d)", value))
        return {(y,m,d) for y,m,d in found if 1 <= m <= 12 and 1 <= d <= 31}
    ed, ad = dates(joined), dates(text)
    if ed:
        if expected_years and any(y is not None and str(y) not in expected_years for y,_,_ in ad):
            return False
        allowed = {(m,d) for _,m,d in ed}
        seen = {(m,d) for _,m,d in ad}
        return seen == allowed
    def months(value):
        found = {int(m) for m in re.findall(r"(?:thang|t)\s*(\d{1,2})(?:\s|$)", norm_text(value))}
        found.update(int(m) for m in re.findall(r"(?<!\d)(\d{1,2})[/.-](?:19|20)\d{2}(?!\d)", value))
        return found
    em, am = months(joined), months(text)
    short_month_years = {str(2000+int(y)) for m,y in re.findall(r"(?<!\d)(\d{1,2})[/.-](\d{2})(?!\d)",text)
                         if 1 <= int(m) <= 12 and int(y)>12}
    if em and expected_years and not short_month_years <= expected_years:
        return False
    if em and am != em:
        return False
    return tokens_hit(text, accept)[0]


def valid_json_shape(value):
    if isinstance(value, float) and not math.isfinite(value):
        return False
    if isinstance(value, dict):
        return all(isinstance(k, str) and valid_json_shape(v) for k,v in value.items())
    if isinstance(value, list):
        return all(valid_json_shape(v) for v in value)
    return value is None or isinstance(value, (str, int, float, bool))


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def provenance_checks(ans, gold):
    contract = gold.get("provenance_contract")
    if not contract:
        return []
    evidence = ans.get("evidence")
    valid = isinstance(evidence, list) and bool(evidence)
    expected_hash = gold.get("payload_sha256")
    identity = ("tool", "source", "as_of", "matched_entry_id", "response_sha256")
    required = identity + ("call_id", "payload_sha256")
    if valid:
        valid = all(isinstance(row, dict) and all(isinstance(row.get(k), str) and row[k].strip() for k in required)
                    and row["payload_sha256"] == expected_hash for row in evidence)
    if valid:
        required_responses = {tuple(row[k] for k in identity) for row in contract}
        allowed = {tuple(row[k] for k in identity) for row in gold.get("provenance_catalog", contract)}
        seen = {tuple(row[k] for k in identity) for row in evidence}
        valid = required_responses <= seen <= allowed
    return [{"check": "provenance", "pass": bool(valid),
             "detail": "recorded response identity/provider/as_of coverage and snapshot hash; call IDs independently verified by driver"}]


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
    # Opposite assertions in another clause cannot be hidden behind a longer
    # accepted negation (e.g. "không đúng, nhưng đúng").
    remainder = n
    for phrase in sorted({norm_text(t) for t in accept}, key=len, reverse=True):
        if phrase:
            remainder = re.sub(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", " ", remainder)
    contradictory = any(phrase_present(remainder, t) for t in reject)
    negated_accept = any(phrase_present(n, prefix + " " + norm_text(t))
                         and prefix + " " + norm_text(t) not in {norm_text(a) for a in accept}
                         for t in accept for prefix in ("khong", "not"))
    hit = [t for t in accept if norm_text(t) and len(norm_text(t)) == a_best and a_best > 0]
    bad = [t for t in reject if norm_text(t) and len(norm_text(t)) == r_best and r_best >= a_best]
    return (a_best > 0 and a_best > r_best and not contradictory and not negated_accept), hit, bad


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
        rows = res.get("checks", [])
        res["schema_valid"] = not any(c.get("check") == "schema" and not c.get("pass") for c in rows) and res.get("error_type") not in ("invalid_schema", "khong_tra_loi")
        res["provenance_correctness"] = all(c.get("pass", False) for c in rows if c.get("check") == "provenance")
        semantic = [c for c in rows if c.get("check") not in ("schema", "provenance")]
        res["semantic_correctness"] = bool(semantic) and all(c.get("pass", False) for c in semantic)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print(json.dumps(res, ensure_ascii=False))

    try:
        with open(answer_path, encoding="utf-8") as f:
            ans = json.load(f, object_pairs_hook=unique_json_object,
                            parse_constant=lambda s: (_ for _ in ()).throw(ValueError("nonfinite JSON: " + s)))
    except Exception as e:
        dump({"task_id": None, "success": False, "fp": 0, "error_type": "khong_tra_loi",
              "detail": "khong doc duoc answer.json: %s" % e, "checks": []})
        return

    with open(gold_path, encoding="utf-8") as f:
        gold = json.load(f)

    if not isinstance(ans, dict) or not valid_json_shape(ans):
        dump({"task_id": gold.get("task_id"), "success": False, "fp": 0,
              "error_type": "invalid_schema", "checks": [{"check":"schema", "pass":False}]})
        return

    checks = provenance_checks(ans, gold)

    def add(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    scoring = gold.get("scoring", "value")

    # ------------------------------------------------------------------ refusal
    if scoring == "refusal":
        v = get_field(ans, "value")
        num = parse_number(v)
        if "value" not in ans or v is not None:
            add("value_null", False, "refusal requires a present JSON null value")
            dump({"task_id": gold.get("task_id"), "success": False, "fp": int(v is not None),
                  "error_type": "bia_so" if v is not None else "invalid_schema", "checks": checks})
            return
        text = " ".join(str(ans.get(k) or "") for k in ("reason", "note", "verdict", "answer", "explanation"))
        ok, hit, bad = refusal_hit(text, gold.get("refusal_tokens", []))
        add("refusal_reason", ok, "hit=%s bad=%s" % (hit, bad))
        bn = [x for x in gold.get("bonus_numbers", []) if any(near_num(y, x) for y in numbers_in(text))]
        bs = [x for x in gold.get("bonus_strings", []) if norm_text(x) in norm_text(text)]
        ok = ok and all(c["pass"] for c in checks)
        dump({"task_id": gold.get("task_id"), "success": ok, "fp": 0,
              "error_type": None if ok else "khong_tra_loi", "checks": checks,
              "bonus": {"numbers": bn, "strings": bs, "hit": bool(bn or bs)}})
        return

    # ------------------------------------------------------------------ verdict
    if scoring == "verdict":
        vv = get_field(ans, gold.get("verdict_path", "verdict"))
        ok, hit, bad = verdict_hit(vv if isinstance(vv, str) else "", gold.get("verdict_accept", []), gold.get("verdict_reject", []))
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
            cu = canon_unit(got) if isinstance(got, str) else ""
            acc = [canon_unit(x) for x in exp["accept"]]
            ok = cu in acc
            detail = "answer=%r canon=%r accept=%s" % (got, cu, acc)
        elif t == "period":
            ok = period_hit(got, exp["accept"])
            detail = "period=%r accept=%s" % (got, exp["accept"])
        elif t == "tokens":
            fb = got if got is not None else ans.get("note")
            ok, hit, bad = tokens_hit(fb if isinstance(fb, str) else "", exp["accept"], exp.get("reject", []))
            if path == "line" and isinstance(fb, str) and re.search(r"\b(khong|not|without|except)\b", norm_text(fb)):
                ok = False
            detail = "hit=%s bad=%s" % (hit, bad)
        elif t == "set":
            def sset(x):
                if isinstance(x, str):
                    x = re.split(r"[,;|\s]+", x.strip())
                return sorted(str(i).strip().upper() for i in (x or []) if str(i).strip())
            ok = isinstance(got, (str, list)) and sset(got) == sorted(s.upper() for s in exp["gold"])
            detail = "answer=%s gold=%s" % (sset(got), exp["gold"])
        elif t == "list_order":
            gl = [str(x).strip().upper() for x in got] if isinstance(got, list) else []
            ok = gl == [s.upper() for s in exp["gold"]]
            detail = "answer=%s gold=%s" % (gl, exp["gold"])
        elif t == "str":
            if path == "source" or path.endswith(".source"):
                ok = source_hit(got, exp["accept"])
            elif any(re.search(r"(?:Q|quý)\s*[1-4]", str(x), re.I) for x in exp["accept"]):
                ok = period_hit(got, exp["accept"])
            else:
                ok = isinstance(got, str) and tokens_hit(got, exp["accept"])[0]
            detail = "answer=%r accept=%s" % (got, exp["accept"])
        elif t == "str_all":
            ok = source_hit(got, exp["accept"], require_all=True)
            detail = "answer=%r need_all=%s" % (got, exp["accept"])
        elif t == "verdict":
            ok, hit, bad = verdict_hit(got if isinstance(got, str) else "", exp["accept"], exp.get("reject", []))
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
    if not ok_all:
        etype = ERR_BY_TYPE.get(first_fail["type"], "sai_ket_qua") if first_fail else "thieu_bang_chung"
    dump({"task_id": gold.get("task_id"), "success": ok_all, "fp": 0,
          "error_type": etype, "checks": checks})


if __name__ == "__main__":
    main()
