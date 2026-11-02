#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_leaks.py — quét rò rỉ đáp án trong instruction.md của mọi task.

Các lớp leak kiểm tra (mỗi lớp = 1 kiểu thông tin gold không được xuất hiện ở nơi agent đọc):
  A. fence_null      — block ```json``` trong instruction chứa '"value": null'
                       (bộc lộ task là bẫy refusal qua format đề).
  B. fence_period    — block schema chứa MỘT token period của gold (agent copy được kỳ đúng).
                       Chỉ quét fence: kỳ nêu trong THÂN câu hỏi là premise hợp lệ.
  C. value_leak      — số vàng (value-expect) xuất hiện trong TOÀN instruction.
  D. evidence_leak   — số bằng chứng (verdict-evidence) xuất hiện trong TOÀN instruction.
  E. bonus_leak      — refusal: bonus_numbers trong toàn bộ đề; bonus_strings (kỳ thay thế)
                       trong fence.
  F. narrative_leak  — đề chứa cụm hướng kết luận "ít nhất 1/một phiên giảm" trên task verdict.

Chạy:  python3 tools/check_leaks.py [tasks_root]
Mặc định quét tasks/pilot, tasks/smoke, tasks/main, tasks/holdout.
Exit 0 nếu 0 leak; exit 1 nếu có leak (in danh sách theo lớp).
"""
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS = ["pilot", "smoke", "main", "holdout"]


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("đ", "d")
    return re.sub(r"[^0-9a-z]+", " ", s).strip()


def num_variants(g):
    """Các dạng văn bản có thể của 1 số vàng."""
    out = set()
    try:
        g = float(g)
    except (TypeError, ValueError):
        return out
    if abs(g) < 1e-9:
        return out
    for fmt in ("%g", "%.1f", "%.2f"):
        out.add(fmt % g)
    if abs(g - round(g)) < 1e-9:
        out.add(str(int(round(g))))
    return out


def num_in_text(cand, text):
    """Tìm candidate số với biên không phải chữ số/dấu phẩy-chấm-%-/-trừ."""
    return re.search(r"(?<![0-9.,:/-])" + re.escape(cand) + r"(?![0-9.,%])", text) is not None


def scan_task(d):
    """Trả về list (class, detail) của 1 thư mục task."""
    leaks = []
    ipath = os.path.join(d, "instruction.md")
    gpath = os.path.join(d, "solution", "gold.json")
    if not (os.path.exists(ipath) and os.path.exists(gpath)):
        return leaks
    instr = open(ipath, encoding="utf-8").read()
    gold = json.load(open(gpath, encoding="utf-8"))
    m = re.search(r"```json\n(.*?)```", instr, re.S)
    fence = m.group(1) if m else ""
    nfence, ninstr = norm(fence), norm(instr)

    # A. fence_null — bất kể scoring, schema không được hiện 'value: null'
    if '"value": null' in fence:
        leaks.append(("fence_null", "schema block chứa 'value: null'"))

    scoring = gold.get("scoring", "value")

    # B. fence_period — token period của gold không được nằm trong fence
    if scoring == "value":
        for exp in gold.get("expects", []):
            if exp.get("type") == "period":
                for tok in exp.get("accept", []):
                    nt = norm(tok)
                    if nt and nt in nfence:
                        leaks.append(("fence_period", "fence chứa token kỳ %r" % tok))

    # C. value_leak — số vàng không được nằm trong đề
    if scoring == "value":
        for exp in gold.get("expects", []):
            if exp.get("type") == "value":
                for cand in num_variants(exp.get("gold")):
                    if num_in_text(re.escape(cand).replace("\\ ", " "), instr) or \
                            num_in_text(cand, instr):
                        leaks.append(("value_leak", "đề chứa số vàng %s" % cand))

    # D. evidence_leak — số bằng chứng verdict
    ev = gold.get("evidence") or {}
    for x in ev.get("numbers", []):
        for cand in num_variants(x):
            if num_in_text(cand, instr):
                leaks.append(("evidence_leak", "đề chứa số evidence %s" % cand))

    # E. bonus_leak — refusal
    if scoring == "refusal":
        for x in gold.get("bonus_numbers", []):
            for cand in num_variants(x):
                if num_in_text(cand, instr):
                    leaks.append(("bonus_leak", "đề chứa bonus_number %s" % cand))
        for s in gold.get("bonus_strings", []):
            ns = norm(s)
            if ns and ns in nfence:
                leaks.append(("bonus_leak", "fence chứa kỳ thay thế %r" % s))

    # F. narrative_leak — cụm hướng kết luận: chỉ là leak khi gold-verdict là "sai"
    # (với biến thể claim ĐÚNG, cụm "có ít nhất một phiên giảm" CHÍNH là nhận định
    #  được kiểm chứng — có trong câu hỏi là hợp lệ).
    if scoring == "verdict" and re.search(r"ít nhất (1|một) phiên giảm", instr):
        if str((gold.get("solution") or {}).get("verdict", "")).lower() != "đúng":
            leaks.append(("narrative_leak", "đề nêu hướng kết luận 'ít nhất 1 phiên giảm'"))

    return leaks


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tasks")
    by_class = {}
    n_tasks = 0
    for split in SPLITS:
        sdir = os.path.join(root, split)
        if not os.path.isdir(sdir):
            continue
        for tid in sorted(os.listdir(sdir)):
            d = os.path.join(sdir, tid)
            if not os.path.isdir(d):
                continue
            n_tasks += 1
            for cls, detail in scan_task(d):
                by_class.setdefault(cls, []).append("%s/%s: %s" % (split, tid, detail))
    print("check_leaks: %d task đã quét" % n_tasks)
    if not by_class:
        print("LEAK: 0 (toàn bộ 6 lớp sạch)")
        return 0
    total = 0
    for cls in sorted(by_class):
        items = by_class[cls]
        total += len(items)
        print("LEAK %-15s: %d" % (cls, len(items)))
        for it in items[:15]:
            print("   ", it)
        if len(items) > 15:
            print("    ... và %d nữa" % (len(items) - 15))
    print("TỔNG leak: %d" % total)
    return 1


if __name__ == "__main__":
    sys.exit(main())
