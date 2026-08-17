import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_skill_list_has_two_skills(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    assert {item["name"] for item in response.json()["skills"]} == {"accident-handling", "long-rental-planning", "pretrip-support"}


@pytest.mark.parametrize("message, expected", [
    ("车辆发生事故了", "accident-handling"),
    ("车辆故障无法使用", "accident-handling"),
    ("车身有损坏", "accident-handling"),
    ("发生了碰撞", "accident-handling"),
    ("乘客受伤需要处理", "accident-handling"),
    ("我要办理长租", "long-rental-planning"),
    ("请规划月租方案", "long-rental-planning"),
    ("租期怎么续租", "long-rental-planning"),
    ("咨询长期租赁", "long-rental-planning"),
    ("帮我做租车计划", "long-rental-planning"),
])
def test_skill_routing_cases(client, message, expected):
    response = client.post("/api/skills/route", json={"message": message})
    assert response.status_code == 200
    assert response.json()["skill"]["name"] == expected
    assert response.json()["loaded"] is False


def test_unknown_message_is_not_forced_to_a_skill(client):
    response = client.post("/api/skills/route", json={"message": "你好"})
    assert response.status_code == 200
    assert response.json()["skill"] is None


def test_route_rejects_empty_message(client):
    assert client.post("/api/skills/route", json={"message": ""}).status_code == 422


def test_route_rejects_unknown_fields(client):
    assert client.post("/api/skills/route", json={"message": "事故", "extra": 1}).status_code == 422


def test_skill_detail_progressively_loads_full_content(client):
    response = client.get("/api/skills/accident-handling")
    assert response.status_code == 200
    body = response.json()
    assert "approval_policy" in body["content"]
    assert body["references"] == ["policy.md"]


def test_unknown_skill_returns_404(client):
    assert client.get("/api/skills/missing").status_code == 404


def test_demo_data_is_synthetic_and_structured(client):
    response = client.get("/api/demo-data")
    assert response.status_code == 200
    assert response.json()["orders"][0]["order_id"] == "ord_demo_001"


def test_registry_lists_metadata_without_full_content(client):
    for skill in client.get("/api/skills").json()["skills"]:
        assert set(skill) == {"name", "description"}
