from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from docling_runpod_worker.staging import inject_page_markers, page_marker


PAGE_TOKEN = re.compile(r"<page_number>(\d+)</page_number>")


def page_tokens(text: str) -> list[str]:
    """Tokens that match the standalone whitespace-delimited page markers."""
    return [tok for tok in text.split() if PAGE_TOKEN.fullmatch(tok)]


class InjectPageMarkersTests(unittest.TestCase):
    def test_multi_page_markers(self) -> None:
        result = inject_page_markers(["alpha", "beta", "gamma"])
        tokens = page_tokens(result)
        self.assertEqual(tokens, [
            "<page_number>1</page_number>",
            "<page_number>2</page_number>",
            "<page_number>3</page_number>",
        ])
        self.assertIn("alpha", result)
        self.assertIn("beta", result)
        self.assertIn("gamma", result)
        # Marker is whitespace-delimited standalone word
        self.assertEqual(page_marker(1).strip(), "<page_number>1</page_number>")
        self.assertTrue(page_marker(1).startswith(" "))
        self.assertTrue(page_marker(1).endswith(" "))

    def test_empty_page_skip_without_number_shift(self) -> None:
        result = inject_page_markers(["page one", "", "page three", "   ", "page five"])
        tokens = page_tokens(result)
        self.assertEqual(tokens, [
            "<page_number>1</page_number>",
            "<page_number>3</page_number>",
            "<page_number>5</page_number>",
        ])
        self.assertNotIn("<page_number>2</page_number>", result)
        self.assertNotIn("<page_number>4</page_number>", result)

    def test_single_page_fallback(self) -> None:
        result = inject_page_markers(["only page"])
        tokens = page_tokens(result)
        self.assertEqual(tokens, ["<page_number>1</page_number>"])
        self.assertIn("only page", result)

    def test_no_markers_when_all_empty(self) -> None:
        self.assertEqual(inject_page_markers([]), "")
        self.assertEqual(inject_page_markers(["", "  ", None or ""]), "")
        self.assertEqual(page_tokens(inject_page_markers(["", ""])), [])

    def test_postprocess_preserves_markers(self) -> None:
        """Mirrors extractor.py comment strip + newline collapse."""
        raw = inject_page_markers([
            "Hello world\n\n\n",
            "<!-- comment -->\nSecond page",
        ])
        text = re.sub(r"(?m)^<!--.*?-->\s*$", "", raw)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        tokens = page_tokens(text)
        self.assertEqual(tokens, [
            "<page_number>1</page_number>",
            "<page_number>2</page_number>",
        ])
        self.assertIn("Hello world", text)
        self.assertIn("Second page", text)


if __name__ == "__main__":
    unittest.main()
