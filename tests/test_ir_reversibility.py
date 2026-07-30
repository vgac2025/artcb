"""Tests de réversibilité IR Engine — critère F-02 (≥ 99 %, cible 100 %)."""

from __future__ import annotations

import json

import pytest

from artcb.ir.decoder import IRDecoder
from artcb.ir.encoder import IREncoder

SAMPLE_TEXTS = [
    "Nous avons décidé d'utiliser FastAPI. Le problème est la perte de contexte.",
    "Observer le monde pour apprendre.",
    "Regarder le problème, créer une solution et l'apprendre.",
    "Si l'hypothèse est correcte, donc nous validons la solution.",
    "L'objectif est de mémoriser chaque raisonnement sans perte.",
    "Hier, nous avons discuté de l'architecture. Aujourd'hui, nous implémentons l'IR Engine.",
    "La preuve est dans le checksum sha256.",
    "Contexte: session de développement ARTCB.",
    "A\n\nB\n\nC",
    (
        "Nous avons décidé d'utiliser FastAPI pour le backend. "
        "Le problème principal est la perte de contexte entre sessions. "
        "La solution ARTCB encode chaque raisonnement en graphe signé. "
        "Prochaine étape : implémenter l'IR Engine."
    ),
]


@pytest.fixture
def encoder() -> IREncoder:
    return IREncoder()


@pytest.fixture
def decoder() -> IRDecoder:
    return IRDecoder()


@pytest.mark.parametrize("text", SAMPLE_TEXTS)
def test_reversibility_exact(text: str, encoder: IREncoder, decoder: IRDecoder) -> None:
    graph = encoder.encode(text)
    result = decoder.decode_with_metrics(graph)
    assert result["reversible"] is True
    assert result["similarity"] >= 0.99
    assert result["text"] == text


def test_graph_integrity(encoder: IREncoder) -> None:
    graph = encoder.encode("Test d'intégrité.")
    assert graph.verify_integrity() is True
    assert graph.checksum.startswith("sha256:")


def test_json_roundtrip(encoder: IREncoder, decoder: IRDecoder) -> None:
    original = SAMPLE_TEXTS[-1]
    graph = encoder.encode(original)
    raw = graph.to_json()
    parsed = json.loads(raw)
    restored = decoder.decode_with_metrics(type(graph).from_dict(parsed))
    assert restored["text"] == original


def test_temporal_edges_chain(encoder: IREncoder) -> None:
    text = "Première phrase. Deuxième phrase. Troisième phrase."
    graph = encoder.encode(text)
    temporal = [e for e in graph.edges if e.rel == "→t"]
    assert len(temporal) == 2


def test_node_classification(encoder: IREncoder) -> None:
    graph = encoder.encode("Nous avons décidé d'utiliser FastAPI.")
    assert graph.nodes[0].t == "D"


def test_compression_ratio_positive(encoder: IREncoder) -> None:
    long_text = SAMPLE_TEXTS[-1] * 3
    graph = encoder.encode(long_text)
    ratio = encoder.compression_ratio(graph)
    assert isinstance(ratio, float)


def test_macro_detection_on_repeated_pattern(encoder: IREncoder) -> None:
    repeated = "Observer le problème. " * 3
    graph = encoder.encode(repeated)
    assert len(graph.nodes) >= 3


def test_empty_text_raises(encoder: IREncoder) -> None:
    with pytest.raises(ValueError):
        encoder.encode("   ")


def test_decode_invalid_graph_raises(decoder: IRDecoder, encoder: IREncoder) -> None:
    graph = encoder.encode("Test.")
    graph.checksum = "sha256:invalid"
    with pytest.raises(ValueError):
        decoder.decode(graph)
