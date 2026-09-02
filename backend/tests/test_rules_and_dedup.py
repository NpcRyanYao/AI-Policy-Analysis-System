from app.services.ingest_service import upsert_policy_record
from app.services.rule_engine import analyze_policy_rules, parse_policy_rules


def test_parse_generative_ai_policy():
    title = "生成式人工智能服务管理暂行办法"
    content = (
        "第一条 为了促进生成式人工智能健康发展和规范应用，制定本办法。\n"
        "第二条 提供生成式人工智能服务，应当遵守法律法规。\n"
        "第四条 提供生成式人工智能服务，应当依法开展安全评估，并履行算法备案手续。\n"
        "不得利用生成式人工智能服务生成虚假信息。\n"
        "鼓励生成式人工智能创新应用。\n"
        "对违法者依法给予警告、罚款直至追究刑事责任。\n"
        "本办法自2023年8月15日起施行。"
    )
    parsed = parse_policy_rules(title, content, "国家互联网信息办公室")
    cats = {c["category"] for c in parsed["categories"]}
    assert "generative_ai" in cats
    types = {c["clause_type"] for c in parsed["clauses"]}
    assert "mandatory" in types
    assert "prohibited" in types
    assert parsed["effective_time"] == "2023-08-15"


def test_analysis_has_fact_inference_advice():
    parsed = parse_policy_rules(
        "测试办法",
        "第二条 本办法适用于在中华人民共和国境内利用生成式人工智能技术向公众提供服务的组织。\n"
        "提供者应当进行安全评估。\n不得侵害他人权益。\n依法给予行政处罚。",
        "网信办",
    )
    analysis = analyze_policy_rules("测试办法", "提供者应当进行安全评估。依法给予行政处罚。", parsed)
    assert analysis["core_requirements"]
    assert analysis["action_suggestions"]
    assert all(x.get("kind") == "advice" for x in analysis["action_suggestions"])
    assert "disclaimer" in analysis["provenance"]


def test_dedup_title_org_date():
    from app.db.session import SessionLocal

    payload = {
        "title": "重复政策标题-单元测试",
        "issuing_org": "测试机构",
        "publish_time": "2024-01-01",
        "content": "正文A",
        "original_url": "https://example.com/a",
        "policy_level": "national",
        "source_id": "manual",
    }
    with SessionLocal() as session:
        _p1, new1 = upsert_policy_record(session, payload, ingest_method="manual", snapshot_id=None)
        session.flush()
        _p2, new2 = upsert_policy_record(session, payload, ingest_method="manual", snapshot_id=None)
        assert new1 is True
        assert new2 is False
        session.rollback()
