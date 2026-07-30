from __future__ import annotations

import unittest

from studyflow.domain.models import SlidePage, SourceChunk


class DomainModelTests(unittest.TestCase):
    def test_slide_index_is_one_based(self) -> None:
        with self.assertRaises(ValueError):
            SlidePage(index=0, text="Invalid")

    def test_source_chunk_requires_slide_citation(self) -> None:
        with self.assertRaises(ValueError):
            SourceChunk(id="chunk-1", document_id="doc-1", text="Evidence", slide_indexes=())


if __name__ == "__main__":
    unittest.main()
