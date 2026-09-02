from app.services.search_index import tokenize_for_fts
from app.services.utils import parse_date


def test_parse_date_variants():
    assert str(parse_date("2023年8月15日")) == "2023-08-15"
    assert str(parse_date("2023-08-15")) == "2023-08-15"


def test_tokenize_chinese():
    tokens = tokenize_for_fts("生成式人工智能服务管理暂行办法")
    assert "生成式" in tokens or "人工智能" in tokens
