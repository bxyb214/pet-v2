"""级别审计工具测试：mastery 前缀 → 推断 exam。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from check_user_exam import infer_exam  # noqa: E402


def test_infer_pet_from_pet_banks():
    ids = [f"b{i}" for i in range(40)] + [f"g{i}" for i in range(10)]
    assert infer_exam(ids) == ("pet", 50, 0)


def test_infer_ket_from_ket_banks():
    ids = [f"kw{i}" for i in range(30)] + [f"kc{i}" for i in range(5)]
    assert infer_exam(ids) == ("ket", 0, 35)


def test_too_few_words_is_unknown():
    assert infer_exam([f"b{i}" for i in range(5)])[0] is None


def test_mixed_pet_ket_is_unknown():
    ids = [f"b{i}" for i in range(30)] + [f"kw{i}" for i in range(30)]
    assert infer_exam(ids)[0] is None


def test_unknown_prefixes_ignored():
    ids = [f"custom-{i}" for i in range(100)]
    assert infer_exam(ids)[0] is None
