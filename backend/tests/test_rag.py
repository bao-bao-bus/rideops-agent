from rideops.rag.chunker import split_markdown
from rideops.rag.bm25 import BM25Index
from rideops.rag.embeddings import MockEmbedding, OpenAICompatibleEmbeddingProvider, cosine_similarity
from rideops.rag.parser import parse_markdown
from rideops.rag.vector_store import SQLiteVectorStore


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


def test_bm25_uses_chinese_token_coverage_and_keeps_business_terms():
    index = BM25Index()
    index.add("accident", "事故发生后应先确认人员安全并记录订单号")
    index.add("rental", "长租方案需要确认租期、城市、车型和预算")
    assert index.search("订单号事故怎么处理", top_k=1)[0][0] == "accident"
    assert index.search("完全不相关的股票走势", top_k=5) == []


def test_sqlite_vector_index_survives_reopen(tmp_path):
    from rideops.rag.chunker import DocumentChunk

    chunk = DocumentChunk("demo", "Demo", "Safety", "事故后确认人员安全", "demo.md")
    provider = MockEmbedding()
    first = SQLiteVectorStore(tmp_path / "vectors.db")
    first.sync([chunk], provider)
    second = SQLiteVectorStore(tmp_path / "vectors.db")
    assert second.all()[0].chunk.content == chunk.content
    assert second.search(provider.embed_query("事故安全"), top_k=1)[0][0] == first.all()[0].chunk_id


def test_real_embedding_adapter_requires_explicit_credentials():
    try:
        OpenAICompatibleEmbeddingProvider("", "", "model")
    except ValueError as error:
        assert "EMBEDDING_BASE_URL" in str(error)
    else:
        raise AssertionError("real adapter must not start without credentials")
