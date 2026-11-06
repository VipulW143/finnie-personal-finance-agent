"""Source-boundary preservation, configuration precedence, and SDK boundaries."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from finnie.chunking import split_text, chunk_document
from finnie.config import get_settings, get_alpaca_credentials
from finnie.embeddings import embed_texts
from finnie.llm import ask_model
from finnie.retrieval import index_chunks, search_chunks
from finnie.similarity import cosine_similarity


META = dict(title="Example Source", url="https://example.org", publisher="Test publisher", topic="Saving")


class FoundationTests(unittest.TestCase):
    def test_chunking_preserves_words_bounds_lists_and_source_metadata(self):
        paragraphs = "# Title\r\n\r\n- one\r\n- two\r\n\r\n" + " ".join("word" + str(i) for i in range(40))
        chunks = split_text(paragraphs, 45)
        self.assertTrue(all(0 < len(c) <= 45 for c in chunks))
        self.assertEqual(" ".join(chunks).split(), paragraphs.split())
        self.assertIn("- one\n- two", chunks[0])
        records = chunk_document(paragraphs, META, 45)
        self.assertEqual([r["text"] for r in records], chunks)
        self.assertEqual(len({r["chunk_id"] for r in records}), len(records))
        self.assertTrue(all(r["url"] == META["url"] and r["topic"] == "Saving" for r in records))
        self.assertEqual(records[0]["chunk_id"], "example-source-001")
        # One overlong token must survive intact when pieces are rejoined.
        self.assertEqual("".join(split_text("x"*121, 20)), "x"*121)
        self.assertEqual(split_text(" \r\n "), [])
        with self.assertRaises(ValueError):
            split_text("text", 0)
        with self.assertRaisesRegex(ValueError, "publisher"):
            chunk_document("text", dict(META, publisher=""))

    def test_configuration_loads_local_env_but_process_values_win(self):
        with TemporaryDirectory() as directory, patch("finnie.config.PROJECT_ROOT", Path(directory)), patch.dict(os.environ, {"FINNIE_ENV": "process"}, clear=True):
            (Path(directory)/".env").write_text("FINNIE_ENV=file\nFINNIE_PROVIDER=demo\nAPCA_API_KEY_ID=test-id\nAPCA_API_SECRET_KEY=test-secret\n")
            settings = get_settings()
            self.assertEqual(settings["environment"], "process")
            self.assertEqual(settings["provider"], "demo")
            self.assertNotIn("test-secret", str(settings))
            self.assertEqual(get_alpaca_credentials(), ("test-id", "test-secret"))
        with TemporaryDirectory() as directory, patch("finnie.config.PROJECT_ROOT", Path(directory)), patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
            self.assertEqual(settings["provider"], "openai")
            self.assertEqual(settings["embedding_model"], "text-embedding-3-small")
            self.assertIsNone(get_alpaca_credentials())

    def test_embeddings_restore_api_order_and_reject_blanks_without_calling(self):
        with patch("finnie.embeddings.OpenAI") as client, patch("finnie.embeddings.get_settings", return_value={"embedding_model": "test-model"}):
            client.return_value.embeddings.create.return_value = SimpleNamespace(data=[
                SimpleNamespace(index=1, embedding=[0., 1.]), SimpleNamespace(index=0, embedding=[1., 0.])])
            self.assertEqual(embed_texts([" first ", "second"]), [[1., 0.], [0., 1.]])
            self.assertEqual(client.return_value.embeddings.create.call_args.kwargs["input"], ["first", "second"])
            client.reset_mock()
            self.assertEqual(embed_texts([]), [])
            with self.assertRaises(ValueError):
                embed_texts([" "])
            client.assert_not_called()

    def test_language_model_uses_configured_model_and_actual_prompt(self):
        with patch("finnie.llm.OpenAI") as client, patch("finnie.llm.get_settings", return_value={"model": "test-model"}):
            client.return_value.responses.create.return_value = SimpleNamespace(output_text="answer")
            self.assertEqual(ask_model("Explain a budget"), "answer")
            client.return_value.responses.create.assert_called_once_with(model="test-model", input="Explain a budget")

    def test_index_and_search_keep_embeddings_and_citations_aligned(self):
        chunks = [dict(META, text="budget", chunk_id="one"), dict(META, text="bond", chunk_id="two")]
        with patch("finnie.retrieval.embed_texts", return_value=[[1., 0.], [0., 1.]]):
            store = index_chunks(chunks)
        with patch("finnie.retrieval.embed_texts", return_value=[[0., 1.]]):
            matches = search_chunks("bond", store, 1)
        self.assertEqual(matches[0]["chunk_id"], "two")
        self.assertEqual(matches[0]["url"], META["url"])
        self.assertNotIn("embedding", chunks[0])
        with patch("finnie.retrieval.embed_texts", return_value=[]), self.assertRaises(ValueError):
            index_chunks(chunks)
        self.assertEqual(len(index_chunks([])), 0)
        self.assertEqual(search_chunks("q", []), [])
        for query, data, k in (("q", [], 0), (" ", [], 1), ("q", chunks, 1)):
            with self.assertRaises(ValueError):
                search_chunks(query, data, k)

    def test_cosine_reference_and_invalid_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0)
        self.assertAlmostEqual(cosine_similarity([1, 1], [1, 1]), 1)
        for a, b in (([], []), ([1], [1, 2]), ([0], [1])):
            with self.assertRaises(ValueError):
                cosine_similarity(a, b)


if __name__ == "__main__":
    unittest.main()
