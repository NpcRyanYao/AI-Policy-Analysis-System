from app.llm.client import normalize_compare_payload


def test_normalize_nested_and_alias_keys():
    raw = {
        "ok": True,
        "data": {
            "共同要求": ["都应做算法备案"],
            "差异": [{"content": "标识义务不同", "policy": "标识办法"}],
        },
    }
    out = normalize_compare_payload(raw)
    assert out is not None
    assert out["common_requirements"][0]["text"] == "都应做算法备案"
    assert out["differences"][0]["text"] == "标识义务不同"
    assert out["differences"][0]["policy_title"] == "标识办法"


def test_normalize_ok_shell_is_empty():
    assert normalize_compare_payload({"ok": True, "status": 200}) is None
    assert normalize_compare_payload({}) is None
