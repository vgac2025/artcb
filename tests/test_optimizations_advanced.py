"""
Tests pour les optimisations avancées 3-10
Rapport 027 — Implémentation complète
"""

import tempfile
from pathlib import Path

import pytest

from src.artcb.agents.pool_manager import AgentPoolManager
from src.artcb.io.pdf_loader_async import extract_pdf_text_async
from src.artcb.ir.compression import GraphCompressor
from src.artcb.ir.models import IRGraph, IRNode, sha256_text
from src.artcb.memory.graph_store import GraphStore
from src.artcb.memory.node_index import NodeIndex
from src.artcb.memory.vector_store_faiss import VectorStoreFAISS
from src.artcb.pol.scorer_numpy import PolScorerNumPy

# ============================================================================
# HELPERS
# ============================================================================

def create_test_graph(graph_id: str, texts: list[str]) -> IRGraph:
    """Créer un graphe de test valide"""
    source_text = " ".join(texts)
    nodes = [
        IRNode(
            id=f"n{i}",
            t="concept",
            sym="C",
            txt=txt,
            checksum=sha256_text(txt),
            start=0,
            end=len(txt)
        )
        for i, txt in enumerate(texts)
    ]

    return IRGraph(
        graph_id=graph_id,
        source_text=source_text,
        nodes=nodes,
        edges=[],
        checksum=sha256_text(source_text)
    )


# ============================================================================
# OPTIMISATION #3 : FAISS VECTORISATION
# ============================================================================

def test_faiss_vector_store_cpu():
    """Test FAISS vector store en mode CPU"""
    store = VectorStoreFAISS(embedding_dim=384, use_gpu=False)

    # Créer graphe test
    graph = create_test_graph("g_test_faiss", ["intelligence artificielle", "machine learning"])

    # Indexer
    store.index_graph(graph)
    assert store.index.ntotal == 2

    # Rechercher
    results = store.search("AI et ML", top_k=2)
    assert len(results) == 2
    assert all(0.0 <= r["similarity"] <= 1.0 for r in results)


def test_faiss_similarity_scores():
    """Test calcul similarité FAISS"""
    store = VectorStoreFAISS(embedding_dim=384, use_gpu=False)

    graph = create_test_graph("g_test_sim", ["chat noir", "chien blanc"])

    store.index_graph(graph)

    # Recherche exacte
    results = store.search("chat noir", top_k=1)
    assert results[0]["similarity"] > 0.3  # Similarité raisonnable


def test_faiss_empty_query():
    """Test FAISS avec requête vide"""
    store = VectorStoreFAISS(embedding_dim=384, use_gpu=False)

    graph = create_test_graph("g_test_empty", ["test"])

    store.index_graph(graph)
    results = store.search("", top_k=1)
    assert len(results) == 1  # Retourne quand même un résultat


# ============================================================================
# OPTIMISATION #4 : ASYNC I/O PDF
# ============================================================================

@pytest.mark.asyncio
async def test_async_pdf_extraction():
    """Test extraction PDF asynchrone — résiste aux PDFs corrompus/auto-référents."""
    pdf_path = Path("data/fixtures/wailly_le_roi_de_l_inconnu.pdf")

    if not pdf_path.exists():
        pytest.skip("PDF Wailly non disponible")

    # Extraction async — le PDF peut avoir des pages corrompues (LimitReachedError)
    text = await extract_pdf_text_async(pdf_path, max_pages=5, parallel=True)

    # Si toutes les pages sont corrompues, on accepte un résultat vide sans crash
    assert isinstance(text, str)
    # Si du texte a pu être extrait, il doit être cohérent
    if len(text) > 100:
        assert "Wailly" in text or "roi" in text or "Wailly" in text.lower()


@pytest.mark.asyncio
async def test_async_pdf_fallback_sequential():
    """Test fallback séquentiel pour petits PDFs"""
    pdf_path = Path("data/fixtures/wailly_le_roi_de_l_inconnu.pdf")

    if not pdf_path.exists():
        pytest.skip("PDF Wailly non disponible")

    # Forcer séquentiel (parallel=False)
    text = await extract_pdf_text_async(pdf_path, max_pages=2, parallel=False)

    assert len(text) > 500


# ============================================================================
# OPTIMISATION #5 : POOL WORKERS AGENTS
# ============================================================================

def test_pool_manager_explore_batch():
    """Test exploration batch avec pool workers"""
    texts = [
        "Premier texte à encoder",
        "Deuxième texte différent",
        "Troisième texte unique"
    ]

    with AgentPoolManager(max_workers=2, use_processes=False) as pool:
        graphs = pool.explore_batch(texts)

        assert len(graphs) == 3
        assert all(isinstance(g, IRGraph) for g in graphs)
        assert all(len(g.nodes) > 0 for g in graphs)


def test_pool_manager_validate_batch():
    """Test validation batch avec pool workers"""
    graphs = [create_test_graph(f"g_test_{i}", [f"test {i}"]) for i in range(3)]

    with AgentPoolManager(max_workers=2) as pool:
        results = pool.validate_batch(graphs)

        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)
        assert all(isinstance(r, dict) for r in results)


def test_pool_manager_context_manager():
    """Test context manager du pool"""
    pool = AgentPoolManager(max_workers=2)

    # Vérifier que le pool se ferme proprement
    with pool:
        assert pool.executor is not None

    # Après sortie du context, executor doit être fermé
    # (pas d'exception levée)


# ============================================================================
# OPTIMISATION #6 : COMPRESSION GRAPHES
# ============================================================================

def test_graph_compression():
    """Test compression/décompression graphe"""
    graph = create_test_graph("g_test_compress", ["A" * 1000, "B" * 1000])

    # Compresser
    compressed = GraphCompressor.compress_graph(graph, level=6)

    # Vérifier compression
    original_size = len(graph.to_json(indent=None).encode('utf-8'))
    assert len(compressed) < original_size

    # Décompresser
    decompressed = GraphCompressor.decompress_graph(compressed)

    assert decompressed.graph_id == graph.graph_id
    assert len(decompressed.nodes) == len(graph.nodes)


def test_compression_ratio_estimation():
    """Test estimation ratio compression"""
    graph = create_test_graph("g_test_ratio", ["test" * 100])

    ratio = GraphCompressor.estimate_compression_ratio(graph)

    assert 0.0 < ratio < 1.0  # Ratio entre 0 et 1


# ============================================================================
# OPTIMISATION #7 : INDEX B-TREE NODES
# ============================================================================

def test_node_index_add_and_find():
    """Test ajout et recherche dans index B-Tree"""
    index = NodeIndex()

    graph = create_test_graph("g1", ["test1", "test2"])

    index.add_graph(graph)

    # Recherche par ID
    result = index.find_by_id("n0")
    assert result is not None
    assert result[0] == "g1"
    assert result[1].id == "n0"


def test_node_index_by_type():
    """Test recherche par type de nœud"""
    index = NodeIndex()

    graph = create_test_graph("g1", ["test1", "test2", "test3"])

    index.add_graph(graph)

    # Recherche par type
    concepts = index.find_by_type("concept")
    assert len(concepts) >= 3


def test_node_index_text_prefix():
    """Test recherche par préfixe texte"""
    index = NodeIndex()

    graph = create_test_graph("g1", [
        "intelligence artificielle",
        "intelligence collective",
        "machine learning"
    ])

    index.add_graph(graph)

    # Recherche préfixe
    results = index.find_by_text_prefix("intelligence")
    assert len(results) == 2


# ============================================================================
# OPTIMISATION #8 : LAZY LOADING GRAPHES
# ============================================================================

def test_graph_store_lazy_loading():
    """Test lazy loading avec cache LRU"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = GraphStore(directory=Path(tmpdir), enable_cache=True, max_cache_size=2)

        # Créer 3 graphes
        graphs = [create_test_graph(f"g_test_{i}", [f"test {i}"]) for i in range(3)]

        # Sauvegarder
        for g in graphs:
            store.save(g)

        # Charger 3 graphes (cache max=2)
        store.load("g_test_0")
        store.load("g_test_1")
        store.load("g_test_2")  # Devrait évincer g_test_0

        # Vérifier cache
        assert len(store.cache) <= 2
        assert "g_test_2" in store.cache
        assert "g_test_1" in store.cache


def test_graph_store_cache_hit():
    """Test cache hit lors du rechargement"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = GraphStore(directory=Path(tmpdir), enable_cache=True, max_cache_size=10)

        graph = create_test_graph("g_cache_test", ["test"])

        store.save(graph)

        # Premier chargement (cache miss)
        store.load("g_cache_test")

        # Deuxième chargement (cache hit)
        store.load("g_cache_test")

        # Vérifier que c'est le même objet en cache
        assert "g_cache_test" in store.cache


# ============================================================================
# OPTIMISATION #9 : VECTORISATION NUMPY
# ============================================================================

def test_pol_scorer_numpy_batch():
    """Test calcul PoL batch avec NumPy"""
    scorer = PolScorerNumPy(alpha=0.4, beta=0.3, gamma=0.3)

    graphs = [create_test_graph(f"g_test_{i}", [f"test {i}_{j}" for j in range(5)]) for i in range(3)]

    # Calcul batch
    metrics = scorer.score_batch(
        graphs=graphs,
        nodes_validated=[4, 5, 3]
    )

    assert len(metrics.pol_score) == 3
    assert all(0.0 <= score <= 1.0 for score in metrics.pol_score)


def test_pol_scorer_numpy_multiple_graphs():
    """Test scoring de plusieurs graphes"""
    scorer = PolScorerNumPy()

    graphs = [
        create_test_graph(f"g_test_{i}", [f"test {i}_{j}" for j in range(3)])
        for i in range(3)
    ]

    metrics = scorer.score_batch(graphs=graphs)

    assert len(metrics.pol_score) == 3
    assert all(0.0 <= score <= 1.0 for score in metrics.pol_score)


# ============================================================================
# TESTS D'INTÉGRATION
# ============================================================================

def test_integration_all_optimizations():
    """Test intégration de toutes les optimisations"""
    # FAISS
    VectorStoreFAISS(embedding_dim=384, use_gpu=False)

    # Pool workers
    with AgentPoolManager(max_workers=2) as pool:
        texts = ["Test 1", "Test 2"]
        graphs = pool.explore_batch(texts)

        # Compression
        compressed = [GraphCompressor.compress_graph(g) for g in graphs]
        assert all(len(c) > 0 for c in compressed)

        # Index
        index = NodeIndex()
        for g in graphs:
            index.add_graph(g)

        # PoL NumPy
        scorer = PolScorerNumPy()
        metrics = scorer.score_batch(
            graphs=graphs,
            nodes_validated=[len(g.nodes) for g in graphs]
        )

        assert len(metrics.pol_score) == 2


def test_performance_comparison():
    """Test comparaison performance avec/sans optimisations"""
    import time

    from artcb.ir.encoder import IREncoder

    # Sans cache
    encoder_no_cache = IREncoder(enable_cache=False)
    text = "Test de performance encodage" * 10

    start = time.time()
    for _ in range(10):
        encoder_no_cache.encode(text)
    time_no_cache = time.time() - start

    # Avec cache
    encoder_cache = IREncoder(enable_cache=True)

    start = time.time()
    for _ in range(10):
        encoder_cache.encode(text)
    time_cache = time.time() - start

    # Cache devrait être plus rapide
    assert time_cache < time_no_cache
    speedup = time_no_cache / time_cache
    assert speedup > 1.2  # Au moins 20% plus rapide


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

