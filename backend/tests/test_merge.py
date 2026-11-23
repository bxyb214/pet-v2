"""合并语义测试（红线不变量）。"""
from app.services.merge import (
    merge_mastery,
    merge_mistakes,
    merge_progress,
    merge_plan,
    merge_sync_data,
    merge_custom_sentences,
)


def test_mastery_union():
    srv = [{"word_id": "w1", "mastered_dims": ["spell"]}]
    cli = [{"word_id": "w1", "mastered_dims": ["w2m"]}, {"word_id": "w2", "mastered_dims": []}]
    out = merge_mastery(srv, cli)
    assert {r["word_id"]: sorted(r["mastered_dims"]) for r in out} == {
        "w1": ["spell", "w2m"],
        "w2": [],
    }


def test_mistake_takes_more_owed():
    srv = [{"word_id": "w1", "dims": ["spell"], "stage": 3, "due_at": "2026-12-01", "repeats": 2}]
    cli = [{"word_id": "w1", "dims": ["w2m"], "stage": 1, "due_at": "2026-11-25", "repeats": 0}]
    out = merge_mistakes(srv, cli)
    assert out[0]["dims"] == ["spell", "w2m"]
    assert out[0]["stage"] == 1
    assert out[0]["due_at"] == "2026-11-25"
    assert out[0]["repeats"] == 0


def test_mistake_single_side_kept():
    srv = [{"word_id": "w1", "dims": ["spell"], "stage": 2, "due_at": "2026-12-01", "repeats": 1}]
    cli = [{"word_id": "w2", "dims": [], "stage": 0, "due_at": "", "repeats": 0}]
    out = merge_mistakes(srv, cli)
    assert {r["word_id"] for r in out} == {"w1", "w2"}


def test_progress_union_and_max_idx():
    srv = [{"key": "reading-t101", "seen": ["q1", "q2"], "idx": 3}]
    cli = [{"key": "reading-t101", "seen": ["q2", "q3"], "idx": 5}]
    out = merge_progress(srv, cli)
    assert out[0]["seen"] == ["q1", "q2", "q3"]
    assert out[0]["idx"] == 5


def test_plan_union():
    srv = {"length": 30, "days_done": ["1", "2"], "reading_length": 0, "reading_days_done": []}
    cli = {"length": 30, "days_done": ["2", "3"], "reading_length": 20, "reading_days_done": ["1"]}
    out = merge_plan(srv, cli)
    assert out == {
        "length": 30,
        "days_done": ["1", "2", "3"],
        "reading_length": 20,
        "reading_days_done": ["1"],
        "reading_books": [],
        "plan_updated_at": 0,
        "reading_updated_at": 0,
    }


def test_plan_delete_wins_with_new_timestamp():
    """删除计划：时间戳更新的一方覆盖旧计划，不能再次并回来。"""
    srv = {"length": 30, "days_done": ["1", "2"], "plan_updated_at": 100}
    cli = {"length": 0, "days_done": [], "plan_updated_at": 200}
    out = merge_plan(srv, cli)
    assert out["length"] == 0
    assert out["days_done"] == []
    assert out["plan_updated_at"] == 200


def test_plan_create_resets_old_days():
    srv = {"length": 30, "days_done": ["1", "2"], "plan_updated_at": 100}
    cli = {"length": 45, "days_done": [], "plan_updated_at": 300}
    out = merge_plan(srv, cli)
    assert out["length"] == 45
    assert out["days_done"] == []


def test_plan_delete_keeps_reading_plan():
    srv = {
        "length": 30, "days_done": ["1"], "reading_length": 20,
        "reading_days_done": ["1"], "reading_books": ["t1"],
        "plan_updated_at": 100, "reading_updated_at": 100,
    }
    cli = {"length": 0, "days_done": [], "plan_updated_at": 200}
    out = merge_plan(srv, cli)
    assert out["length"] == 0
    assert out["reading_length"] == 20
    assert out["reading_days_done"] == ["1"]
    assert out["reading_books"] == ["t1"]


def test_plan_reading_books_client_wins():
    """教材选择是同一份计划的属性，不做并集：客户端非空即以客户端为准。"""
    srv = {"reading_length": 20, "reading_books": ["t1", "t2"]}
    cli = {"reading_length": 20, "reading_books": ["t1"]}
    assert merge_plan(srv, cli)["reading_books"] == ["t1"]
    # 客户端没带（老版本 / 首次合并）→ 保留服务端
    assert merge_plan(srv, {"reading_length": 20})["reading_books"] == ["t1", "t2"]


def test_custom_sentences_union():
    srv = [{"sid": "a", "book": "t2", "test_no": 1, "part": 1, "en": "Server side.", "cn": "", "key": "", "note": ""}]
    cli = [
        {"sid": "a", "book": "t2", "test_no": 1, "part": 1, "en": "Client side.", "cn": "", "key": "", "note": ""},
        {"sid": "b", "book": "t2", "test_no": 1, "part": 2, "en": "Only client.", "cn": "", "key": "", "note": ""},
    ]
    out = merge_custom_sentences(srv, cli)
    assert [r["sid"] for r in out] == ["a", "b"]
    assert out[0]["en"] == "Server side."  # 服务端优先


def test_sync_data_entry():
    srv = {"mastery": [], "mistakes": [], "progress": [], "plan": {"length": 0, "days_done": []}}
    cli = {
        "mastery": [{"word_id": "w1", "mastered_dims": ["spell"]}],
        "mistakes": [{"word_id": "w9", "dims": ["w2m"], "stage": 0, "due_at": "", "repeats": 0}],
        "progress": [{"key": "k", "seen": [], "idx": 0}],
        "plan": {"length": 40, "days_done": ["1"]},
    }
    out = merge_sync_data(srv, cli)
    assert out["mastery"][0]["word_id"] == "w1"
    assert out["mistakes"][0]["word_id"] == "w9"
    assert out["plan"]["length"] == 40
