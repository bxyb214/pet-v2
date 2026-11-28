"""英语内容模板与校验共用的表结构（单一来源）。

生成器 tools/make_content_templates.py 和校验器 tools/check_content.py 都从这里
读取工作表/列/枚举/书目预设，避免两边列名漂移。

约定：
- 级别由文件路径决定（data-src/english/<exam>/<module>.xlsx），表里不填级别。
- 第一页固定「说明」，校验器忽略；其后每页第 1 行是表头。
- 答案在 Excel 里用 1 基（1–4 / 1–3），构建时再转 0 基。
"""
from __future__ import annotations

import re
from typing import Any

EXAMS = ["ket", "pet", "fce"]
EXAM_NAMES = {"ket": "KET", "pet": "PET", "fce": "FCE"}
MODULES = ["words", "reading", "grammar", "listening", "speaking"]
MODULE_NAMES = {
    "words": "单词",
    "reading": "阅读",
    "grammar": "语法",
    "listening": "听力",
    "speaking": "口语",
}

# 级别 → 5 本书（书目页预填；书名/简介可改，book_id 建议不改）
BOOKS: dict[str, list[tuple[str, str, str]]] = {
    "pet": [
        ("t1", "Trainer 1", "2020 改版官方真题训练 1（现有数据）"),
        ("t2", "Trainer 2", "官方真题训练 2（现有数据）"),
        ("teen1", "青少年 1", "待录入"),
        ("teen2", "青少年 2", "待录入"),
        ("teen3", "青少年 3", "待录入"),
    ],
    "ket": [
        ("k-t1", "Trainer 1", "KET 官方真题训练 1（待录入）"),
        ("k-t2", "Trainer 2", "KET 官方真题训练 2（待录入）"),
        ("k-teen1", "青少年 1", "待录入"),
        ("k-teen2", "青少年 2", "待录入"),
        ("k-teen3", "青少年 3", "待录入"),
    ],
    "fce": [
        ("f-t1", "Trainer 1", "FCE 官方真题训练 1（待录入）"),
        ("f-t2", "Trainer 2", "FCE 官方真题训练 2（待录入）"),
        ("f-teen1", "青少年 1", "待录入"),
        ("f-teen2", "青少年 2", "待录入"),
        ("f-teen3", "青少年 3", "待录入"),
    ],
}

# 工作表 → 列（顺序即模板列顺序）
COLUMNS: dict[str, dict[str, list[str]]] = {
    "words": {
        "必默": ["分组", "英文", "中文", "音标", "词性", "英文例句", "例句中文", "用法/辨析", "音频"],
        "高频": ["分组", "英文", "中文", "音标", "词性", "英文例句", "例句中文", "用法/辨析", "音频"],
        "固搭": ["分组", "英文", "中文", "音标", "词性", "英文例句", "例句中文", "用法/辨析", "音频"],
        "同义": ["分组", "原短语", "原短语中文", "同义短语", "同义短语中文", "音频"],
    },
    "reading": {
        "书目": ["book_id", "书名", "简介"],
        "套题": ["book_id", "test_no", "标题", "备注"],
        "Part": ["book_id", "test_no", "part", "题型", "重点"],
        "句子": [
            "book_id", "test_no", "part", "句子ID", "英文", "中文",
            "关键信息", "题型", "考点", "考点标签", "解析", "时态",
        ],
        "成分": ["句子ID", "成分", "文本"],
        "语法点": ["句子ID", "考点编号", "考点名称", "说明"],
        "语法题": ["句子ID", "题干", "A", "B", "C", "D", "答案", "解析", "考点编号"],
    },
    "grammar": {
        "语法体系": ["天", "天名称", "考点编号", "考点名称"],
        "例句": ["句子ID", "英文", "中文", "考点编号", "考点名称", "说明"],
        "成分": ["句子ID", "成分", "文本"],
        "语法题": ["句子ID", "题干", "A", "B", "C", "D", "答案", "解析", "考点编号"],
    },
    "listening": {
        "书目": ["book_id", "书名", "简介"],
        "套题": ["book_id", "test_no", "标题", "时长(秒)"],
        "Part": [
            "book_id", "test_no", "part", "题型", "标签", "题号范围",
            "音频文件", "时长(秒)",
        ],
        "题目": [
            "book_id", "test_no", "part", "题号", "题干", "答案",
            "选项A", "选项B", "选项C", "配图", "起始时间t0",
        ],
        "原文": ["book_id", "test_no", "part", "序号", "t0", "t1", "文本"],
    },
    "speaking": {
        "场景包": ["pack_id", "part", "名称", "中文", "学习目标", "level", "顺序"],
        "跟读句": [
            "句子ID(可空)", "pack_id", "英文", "中文", "提示",
            "难度", "重读词", "来源", "启用",
        ],
        "造句题": ["题ID(可空)", "pack_id", "中文提示", "参考答案", "句型"],
        "场景": [
            "场景ID", "pack_id", "part", "标题", "中文", "level",
            "开场白", "跟读句IDs(可空)", "造句题IDs(可空)",
        ],
        "句型库(可选)": ["part", "组ID", "组名", "组中文", "英文", "中文"],
        "Part1题库(可选)": ["序号", "问题", "中文", "参考答案"],
        "范文(可选)": ["编号", "问题", "参考答案"],
    },
}

# 枚举列（生成器加下拉，校验器校验）：模块 → 工作表 → 列 → 可选值
ENUMS: dict[str, dict[str, dict[str, list[str]]]] = {
    "reading": {"句子": {"题型": ["meaning", "blank", "grammar"]}},
    "listening": {"Part": {"题型": ["picture", "choice", "fill"]}},
    "speaking": {"跟读句": {"启用": ["是", "否"]}},
}

# 预填书目的工作表
BOOK_SHEETS = {"reading": "书目", "listening": "书目"}

# 说明页规则（模块级；通用规则由 common_notes 追加）
MODULE_NOTES: dict[str, list[str]] = {
    "words": [
        "必默 / 高频 / 固搭：英文、中文必填；同义：原短语、同义短语必填，中文可空。",
        "同一张表内按英文（去首尾空格、连续空白归一、转小写）去重，重复行会报错。",
        "跨库重复只提示、不自动删除；分组留空归入「未分组」。",
        "音频可写文件名（放在 audio/words/ 下）或相对 frontend/public 的完整路径。",
    ],
    "reading": [
        "题型填 meaning / blank / grammar，多个用逗号分隔；PET 现有句子全部三型。",
        "每个句子至少 1 道语法题、至少 3 块句子成分；语法题的答案填 1–4。",
        "考点填 grammar.xlsx「语法体系」里的编号；考点标签是页面上展示的一句话。",
        "关键信息若填写，必须是英文原句里的片段。",
        "语法点编号必须能在 grammar.xlsx 的「语法体系」里找到。",
        "句子ID 全级别唯一，建议 <book_id>-t<test_no>-p<part>-s<n>。",
    ],
    "grammar": [
        "语法体系：天、考点编号在级别内唯一；考点编号建议连续。",
        "例句的句子ID 不能与 reading.xlsx 的句子ID 重复；每个例句至少 1 道语法题。",
        "语法题答案填 1–4；可以引用 reading.xlsx 或 grammar.xlsx 里的句子ID。",
        "每个考点建议至少 1 道题，缺题会提示。",
    ],
    "listening": [
        "题型填 picture / choice / fill。",
        "picture / choice 答案填 1–3；choice 填 3 个选项，picture 填配图（选项可空），fill 填答案文本。",
        "音频建议命名 <book_id>-t<test_no>-p<part>.mp3，放在 audio/listen/ 下。",
        "配图建议 img/listen/<book_id>-t<test_no>-q<题号>.png。",
        "原文 t0/t1 按 part 内升序；缺时间轴时播放器不能逐句高亮。",
    ],
    "speaking": [
        "part 填 1–4；pack_id 在级别内唯一，顺序用于计划切分。",
        "跟读句 / 造句题的 pack_id 必须存在；句子ID / 题ID 可空，构建时按 <pack_id>-<序号> 生成。",
        "跟读句难度 1–5；重读词用逗号分隔，建议都出现在英文里。",
        "口语计划不用单独填，页面会按 packs / scenes 和用户选择的天数自动切分。",
        "句型库 / Part1题库 / 范文 为可选项，没有就留空。",
    ],
}

COMMON_NOTES = [
    "级别由文件所在目录决定（ket / pet / fce），表格里不用填级别。",
    "「说明」是当前页；其后每页第 1 行是表头，不要合并单元格、不要加标题行。",
    "空单元格按空值处理；英文、中文等必填项留空会报错。",
    "答案在 Excel 里用 1 基（1–4 或 1–3），生成 JSON 时再转 0 基。",
    "保存后运行：backend/.venv/Scripts/python.exe tools/check_content.py --exam <级别> --module <模块>",
]

# 说明页示例（每个模块一段）
EXAMPLES: dict[str, dict[str, list[str]]] = {
    "words": {
        "必默": ["1. 家居与穿着", "accommodation", "住宿", "/əˌkɒməˈdeɪʃn/", "n.", "We need to book our accommodation.", "我们需要预订住宿。", "", "bimo-01.mp3"],
        "同义": ["阅读 Part 1", "a DVD you can keep", "你可以拥有的 DVD", "make something to take home", "制作可带回家的物品", ""],
    },
    "reading": {
        "句子": ["t1", "1", "1", "t1-t1-p1-s01", "The race now starts at 4 pm, not 3 pm.", "比赛现在改到下午 4 点开始。", "not 3 pm", "meaning,blank,grammar", "29", "一般现在时表既定安排 · not 对比否定", "the race 特指那场比赛", "一般现在时"],
        "语法题": ["t1-t1-p1-s01", "The race starts at 4 pm, ______ 3 pm.", "not", "no", "don't", "doesn't", "1", "对比否定时间状语用 not。", "29"],
    },
    "grammar": {
        "语法体系": ["1", "名词", "1", "可数名词和不可数名词"],
        "语法题": ["g-ex-01", "There are two ______ on the desk.", "books", "book", "a book", "bookes", "1", "two 后接可数名词复数。", "1"],
    },
    "listening": {
        "Part": ["k-t1", "1", "1", "picture", "短对话选图", "Questions 1–7", "k-t1-t1-p1.mp3", "558"],
        "题目": ["k-t1", "1", "1", "1", "What is the girl going to bring?", "1", "", "", "", "img/listen/k-t1-t1-q1.png", "18.25"],
    },
    "speaking": {
        "场景包": ["k-s01", "1", "Greetings and introductions", "问候与介绍", "完整句问候 + 自我介绍", "A2", "1"],
        "跟读句": ["", "k-s01", "Good morning. It is nice to meet you.", "早上好，很高兴见到你。", "先微笑，重读 nice。", "2", "morning,nice", "自编", "是"],
        "造句题": ["", "k-s01", "告诉考官你的名字和年龄。", "My name is Wenwen and I am twelve years old.", "greeting"],
    },
}

_CJK = re.compile(r"[㐀-䶿一-鿿]")


def norm_term(value: Any) -> str:
    """英文去重键：去首尾空格、连续空白归一、转小写。"""
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def cell(row: tuple[Any, ...], index: int) -> str:
    """按列下标取单元格文本；越界返回空串。"""
    if index < 0 or index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else str(value).strip()


def is_blank_row(row: tuple[Any, ...]) -> bool:
    return all(v is None or str(v).strip() == "" for v in row)


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text or ""))


def module_path(root: Any, exam: str, module: str) -> Any:
    """data-src/english/<exam>/<module>.xlsx"""
    return root / "data-src" / "english" / exam / f"{module}.xlsx"
