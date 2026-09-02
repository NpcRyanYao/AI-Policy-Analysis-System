"""预置政策分类、条款类型、数据源注册表。"""

from typing import Any

POLICY_LEVELS = [
    {"value": "national", "label": "国家"},
    {"value": "provincial", "label": "省"},
    {"value": "municipal", "label": "市"},
]

CLAUSE_TYPES = [
    {"value": "mandatory", "label": "强制性条款", "keywords": ["应当", "必须", "严禁", "不得", "禁止"]},
    {"value": "prohibited", "label": "禁止性条款", "keywords": ["不得", "禁止", "严禁"]},
    {"value": "recommended", "label": "推荐性条款", "keywords": ["鼓励", "支持", "倡导", "可以", "建议"]},
]

CATEGORY_TREE: list[dict[str, Any]] = [
    {
        "value": "generative_ai",
        "label": "生成式 AI 管理",
        "children": [
            {"value": "service_access", "label": "服务准入"},
            {"value": "content_safety", "label": "内容安全"},
            {"value": "training_data", "label": "训练数据"},
            {"value": "content_labeling", "label": "标识义务"},
        ],
    },
    {
        "value": "algorithm_filing",
        "label": "算法备案",
        "children": [
            {"value": "recommend_algo", "label": "推荐算法"},
            {"value": "deep_synthesis", "label": "深度合成"},
            {"value": "filing_process", "label": "备案流程"},
        ],
    },
    {
        "value": "data_security",
        "label": "数据安全",
        "children": [
            {"value": "classification", "label": "数据分类分级"},
            {"value": "cross_border", "label": "跨境传输"},
            {"value": "important_data", "label": "重要数据"},
        ],
    },
    {
        "value": "personal_info",
        "label": "个人信息保护",
        "children": [
            {"value": "consent", "label": "知情同意"},
            {"value": "sensitive_pi", "label": "敏感个人信息"},
            {"value": "auto_decision", "label": "自动化决策"},
        ],
    },
    {
        "value": "ai_ethics",
        "label": "AI 伦理",
        "children": [
            {"value": "ethics_review", "label": "科技伦理审查"},
            {"value": "fairness", "label": "公平性"},
            {"value": "human_oversight", "label": "人类监督"},
        ],
    },
    {
        "value": "industry_supervision",
        "label": "行业监管",
        "children": [
            {"value": "internet_info", "label": "互联网信息服务"},
            {"value": "industry_data", "label": "工业和信息化"},
            {"value": "local_industry", "label": "地方产业政策"},
        ],
    },
]


SOURCE_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "cac",
        "name": "国家互联网信息办公室",
        "level": "national",
        "region": "national",
        "home_url": "https://www.cac.gov.cn/",
        "list_urls": ["https://www.cac.gov.cn/xxgk/index.htm"],
        "priority": 1,
    },
    {
        "id": "miit",
        "name": "工业和信息化部",
        "level": "national",
        "region": "national",
        "home_url": "https://www.miit.gov.cn/",
        "list_urls": ["https://www.miit.gov.cn/zwgk/zcwj/index.html"],
        "priority": 2,
    },
    {
        "id": "samr",
        "name": "国家市场监督管理总局",
        "level": "national",
        "region": "national",
        "home_url": "https://www.samr.gov.cn/",
        "list_urls": ["https://www.samr.gov.cn/zw/zxxx/index.html"],
        "priority": 3,
    },
    {
        "id": "most",
        "name": "科学技术部",
        "level": "national",
        "region": "national",
        "home_url": "https://www.most.gov.cn/",
        "list_urls": ["https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/"],
        "priority": 4,
    },
    {
        "id": "gov_cn",
        "name": "中国政府网",
        "level": "national",
        "region": "national",
        "home_url": "https://www.gov.cn/",
        "list_urls": ["https://www.gov.cn/zhengce/"],
        "priority": 5,
    },
    {
        "id": "beijing_cac",
        "name": "北京市互联网信息办公室",
        "level": "municipal",
        "region": "beijing",
        "home_url": "https://www.beijing.gov.cn/",
        "list_urls": [],
        "priority": 10,
    },
    {
        "id": "shanghai_cac",
        "name": "上海市互联网信息办公室",
        "level": "municipal",
        "region": "shanghai",
        "home_url": "https://www.shanghai.gov.cn/",
        "list_urls": [],
        "priority": 11,
    },
    {
        "id": "guangdong_cac",
        "name": "广东省互联网信息办公室",
        "level": "provincial",
        "region": "guangdong",
        "home_url": "https://www.gd.gov.cn/",
        "list_urls": [],
        "priority": 12,
    },
    {
        "id": "zhejiang_cac",
        "name": "浙江省互联网信息办公室",
        "level": "provincial",
        "region": "zhejiang",
        "home_url": "https://www.zj.gov.cn/",
        "list_urls": [],
        "priority": 13,
    },
    {
        "id": "manual",
        "name": "人工补录",
        "level": "national",
        "region": "national",
        "home_url": "",
        "list_urls": [],
        "priority": 99,
    },
]


KEYWORD_CATEGORY_HINTS: dict[str, list[str]] = {
    "generative_ai": ["生成式人工智能", "生成式 AI", "大模型", "基础模型", "AIGC"],
    "content_labeling": ["标识", "深度合成标识", "显著标识", "隐性标识"],
    "algorithm_filing": ["算法备案", "算法推荐", "推荐算法"],
    "deep_synthesis": ["深度合成", "深度伪造", "换脸"],
    "data_security": ["数据安全", "重要数据", "核心数据", "数据分类分级"],
    "cross_border": ["出境", "跨境", "数据出境"],
    "personal_info": ["个人信息", "隐私", "敏感个人信息"],
    "auto_decision": ["自动化决策", "个性化推荐"],
    "ai_ethics": ["科技伦理", "伦理规范", "人类监督", "公平"],
    "industry_supervision": ["工业和信息化", "互联网信息服务"],
    "service_access": ["安全评估", "上线", "备案", "许可"],
    "training_data": ["训练数据", "语料", "知识产权"],
}


def flatten_categories() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for parent in CATEGORY_TREE:
        rows.append({"value": parent["value"], "label": parent["label"], "parent": ""})
        for child in parent.get("children", []):
            rows.append(
                {
                    "value": child["value"],
                    "label": child["label"],
                    "parent": parent["value"],
                }
            )
    return rows


def category_label(value: str) -> str:
    for item in flatten_categories():
        if item["value"] == value:
            return item["label"]
    return value


def source_by_id(source_id: str) -> dict[str, Any] | None:
    for item in SOURCE_REGISTRY:
        if item["id"] == source_id:
            return item
    return None
