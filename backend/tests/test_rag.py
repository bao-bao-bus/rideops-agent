from rideops.rag.chunker import split_markdown
from rideops.rag.embeddings import MockEmbedding, cosine_similarity
from rideops.rag.parser import parse_markdown


def test_policy_parser_preserves_title_and_source(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("# Demo policy\n\n## Safety\n\nStay safe.", encoding="utf-8")
    document = parse_markdown(path)
    assert document.title == "Demo policy"
    assert document.source == str(path)


def test_chunker_preserves_section_and_splits_long_content(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("# Demo\n\n## Safety\n\n" + ("碰撞后确认人员安全。" * 80), encoding="utf-8")
    chunks = split_markdown(parse_markdown(path), max_chars=80)
    assert len(chunks) > 1
    assert all(chunk.section == "Safety" for chunk in chunks)


def test_mock_embedding_is_deterministic_and_similar_text_scores_higher():
    model = MockEmbedding()
    first = model.embed("车辆发生故障")
    second = model.embed("车辆发生故障")
    unrelated = model.embed("月租方案")
    assert first == second
    assert cosine_similarity(first, second) > cosine_similarity(first, unrelated)


def test_rag_search_returns_citations(client):
    response = client.post("/api/rag/search", json={"query": "车辆发生碰撞后应该怎么处理"})
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is True
    assert body["evidence"]
    assert {"document_id", "title", "section", "content", "score", "source"} <= set(body["evidence"][0])


def test_rag_search_supports_long_rental_policy(client):
    response = client.post("/api/rag/search", json={"query": "长租需要收集哪些信息"})
    assert response.json()["evidence"][0]["document_id"] == "long-rental-planning"


def test_rag_refuses_when_no_evidence(client):
    response = client.post("/api/rag/search", json={"query": "火星天气和股票走势", "min_score": 0.5})
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is False
    assert body["evidence"] == []
    assert body["refusal_reason"]


def test_rag_query_validates_parameters(client):
    assert client.post("/api/rag/search", json={"query": "事故", "top_k": 0}).status_code == 422
    assert client.post("/api/rag/search", json={"query": "事故", "unexpected": True}).status_code == 422
