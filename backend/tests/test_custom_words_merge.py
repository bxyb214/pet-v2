"""custom_words 合并测试（服务端优先、按 word 小写并集）。"""
from app.services.merge import merge_custom_words, merge_sync_data


def test_custom_words_union_and_server_priority():
    srv = [{"id": 1, "word": "Shadow", "pos": "n.", "definition": "服务端修正版", "example_en": "", "example_cn": ""}]
    cli = [
        {"id": 9, "word": "shadow", "pos": "n.", "definition": "客户端旧版", "example_en": "", "example_cn": ""},
        {"id": 10, "word": "apple", "pos": "n.", "definition": "苹果", "example_en": "", "example_cn": ""},
    ]
    out = merge_custom_words(srv, cli)
    assert [w["word"] for w in out] == ["apple", "Shadow"]  # 排序按小写
    by_word = {w["word"].lower(): w for w in out}
    assert by_word["shadow"]["definition"] == "服务端修正版"
    assert by_word["apple"]["definition"] == "苹果"


def test_sync_data_includes_custom_words():
    srv = {"mastery": [], "mistakes": [], "progress": [], "plan": {"length": 0, "days_done": []}, "custom_words": []}
    cli = {
        "mastery": [],
        "mistakes": [],
        "progress": [],
        "plan": {"length": 0, "days_done": []},
        "custom_words": [{"id": 0, "word": "apple", "pos": "n.", "definition": "苹果", "example_en": "", "example_cn": ""}],
    }
    out = merge_sync_data(srv, cli)
    assert out["custom_words"][0]["word"] == "apple"
