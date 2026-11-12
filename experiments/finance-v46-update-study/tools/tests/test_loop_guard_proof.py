"""OpenTrading native LoopGuard denial is an accounting proof only (main amendment 2026-11-10)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v46_rejection_proof import loop_guard_count

MSG = ('Người dùng dừng vòng lặp: bạn đã gọi calculate với cùng tham số 3 lần liên tiếp. '
       'Đừng gọi lại lời gọi này; đổi cách khác hoặc trả lời bằng dữ liệu đã có.')


def test_exact_native_sentence_and_tool_name():
    assert loop_guard_count(MSG, 'calculate') == 3
    assert loop_guard_count('Error: ' + MSG, 'calculate') == 3
    assert loop_guard_count(MSG, 'calculator') is None
    assert loop_guard_count(MSG.replace('3 lần', '2 lần'), 'calculate') is None
    assert loop_guard_count('{"benchmark_evidence":{}} ' + MSG, 'calculate') is None
    assert loop_guard_count(None, 'calculate') is None
