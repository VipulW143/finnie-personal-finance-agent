"""FAISS ranking, metadata alignment, persistence, and migration regressions."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from finnie.rag import (
    INDEX_CACHE_VERSION, _read_cached_index, _write_cached_index,
    answer_with_sources,
)
from finnie.retrieval import index_chunks, search_chunks
from finnie.similarity import cosine_similarity
from finnie.vector_store import VectorStore


def chunk(name, vector, topic="Investing"):
    return {
        "chunk_id": name, "text": name, "title": name,
        "url": "https://example.org/" + name, "publisher": "SEC",
        "topic": topic, "embedding": vector,
    }


class FaissTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            chunk("first", [1.0, 0.0]),
            chunk("second", [0.8, 0.6]),
            chunk("third", [0.0, 1.0], "Saving"),
        ]

    def test_scores_match_cosine_and_metadata_stays_aligned(self):
        query = [0.9, 0.1]
        with patch("finnie.retrieval.embed_texts", return_value=[query]):
            results = search_chunks("question", VectorStore(self.chunks), top_k=9)
        expected = sorted(self.chunks, key=lambda c: cosine_similarity(query, c["embedding"]), reverse=True)
        self.assertEqual([r["chunk_id"] for r in results], [c["chunk_id"] for c in expected])
        for result, source in zip(results, expected):
            self.assertAlmostEqual(result["score"], cosine_similarity(query, source["embedding"]), places=6)
            self.assertEqual(result["url"], source["url"])
            self.assertNotIn("embedding", result)

    def test_round_trip_and_legacy_migration_without_embedding_calls(self):
        with TemporaryDirectory() as directory, patch(
            "finnie.rag.INDEX_CACHE_PATH", Path(directory) / "index.json"
        ) as path, patch("finnie.retrieval.embed_texts") as embed:
            store = VectorStore(self.chunks)
            _write_cached_index("fingerprint", store)
            restored, migrated = _read_cached_index("fingerprint")
            self.assertFalse(migrated)
            self.assertEqual(restored.search([1, 0], 3), store.search([1, 0], 3))
            self.assertIsNone(_read_cached_index("changed-fingerprint"))
            path.write_text(json.dumps({"version": 1, "fingerprint": "fingerprint", "chunks": self.chunks}))
            restored, migrated = _read_cached_index("fingerprint")
            self.assertTrue(migrated)
            _write_cached_index("fingerprint", restored)
            self.assertEqual(json.loads(path.read_text())["version"], INDEX_CACHE_VERSION)
            self.assertFalse(list(Path(directory).glob("*.tmp")))
            embed.assert_not_called()

    def test_corrupt_native_index_rebuilds_from_valid_cached_vectors(self):
        with TemporaryDirectory() as directory, patch(
            "finnie.rag.INDEX_CACHE_PATH", Path(directory) / "index.json"
        ) as path:
            _write_cached_index("fingerprint", VectorStore(self.chunks))
            data = json.loads(path.read_text())
            data["faiss_index"] = "invalid base64"
            path.write_text(json.dumps(data))
            store, needs_save = _read_cached_index("fingerprint")
            self.assertTrue(needs_save)
            self.assertEqual(store.search([1, 0], 1)[0]["chunk_id"], "first")

    def test_filter_excludes_better_scoring_other_category(self):
        with patch("finnie.retrieval.embed_texts", return_value=[[1.0, 0.0]]), patch(
            "finnie.rag.ask_model", return_value="A savings explanation [1]."
        ):
            result = answer_with_sources("Saving?", VectorStore(self.chunks), category="Saving")
        self.assertIn("https://example.org/third", result)
        self.assertNotIn("https://example.org/first", result)

    def test_bad_vectors_and_count_are_rejected(self):
        for vectors in ([[0, 0]], [[float("nan"), 1]], [[1, 2], [1]]):
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                VectorStore([chunk(str(i), v) for i, v in enumerate(vectors)])
        with self.assertRaises(ValueError):
            VectorStore(self.chunks).search([1, 0, 0], 1)
        with patch("finnie.retrieval.embed_texts", return_value=[]), self.assertRaises(ValueError):
            index_chunks([{"text": "one"}])
        self.assertEqual(VectorStore([]).search([1, 0], 3), [])


if __name__ == "__main__":
    unittest.main()
