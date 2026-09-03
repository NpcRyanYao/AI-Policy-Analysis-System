def test_health_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["policy_count"] >= 1


def test_dashboard_and_list(client):
    dash = client.get("/api/v1/dashboard").json()
    assert dash["total"] >= 1
    listing = client.get("/api/v1/policies", params={"page_size": 5}).json()
    assert listing["total"] >= 1
    assert listing["items"]
    pid = listing["items"][0]["id"]
    detail = client.get(f"/api/v1/policies/{pid}").json()
    assert detail["original_url"].startswith("http")
    assert detail["content"]
    assert "provenance" in (detail.get("analysis") or {})


def test_search_keyword(client):
    resp = client.get("/api/v1/policies", params={"q": "生成式人工智能", "sort": "relevance"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    titles = " ".join(item["title"] for item in data["items"])
    assert "生成式" in titles or "人工智能" in titles


def test_compare_and_export(client):
    listing = client.get("/api/v1/policies", params={"page_size": 3}).json()["items"]
    ids = [x["id"] for x in listing[:2]]
    compared = client.post("/api/v1/policies/compare", json={"policy_ids": ids})
    assert compared.status_code == 200
    body = compared.json()
    assert "common_requirements" in body
    excel = client.get("/api/v1/export/excel", params={"ids": ",".join(ids)})
    assert excel.status_code == 200
    assert excel.content[:2] == b"PK"


def test_subscription_digest(client):
    created = client.post(
        "/api/v1/subscriptions",
        json={"name": "生成式AI", "keywords": ["生成式人工智能"], "categories": ["generative_ai"]},
    )
    assert created.status_code == 200
    digest = client.post("/api/v1/digests/generate")
    assert digest.status_code == 200
    assert digest.json()["policy_ids"]


def test_not_found(client):
    resp = client.get("/api/v1/policies/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_reanalyze_loaded_policy_twice(client):
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.policy import Policy
    from app.services.analysis_service import parse_and_analyze
    from app.services.policy_service import load_policy

    pid = client.get("/api/v1/policies", params={"page_size": 1}).json()["items"][0]["id"]
    with SessionLocal() as session:
        parse_and_analyze(session, load_policy(session, pid), force=True)
        session.commit()
        parse_and_analyze(session, load_policy(session, pid), force=True)
        session.commit()
        policy = session.execute(select(Policy).where(Policy.id == pid)).scalar_one()
        assert policy.status == "analyzed"
