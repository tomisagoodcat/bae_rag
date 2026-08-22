"""One-off helper to copy extracted notebook cells into stage modules."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
STAGES = ROOT / "src" / "stages"


def main() -> None:
    # document_loader from cell 5
    src = (ROOT / "_extract_cell_5.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    if lines[0].startswith('"""'):
        i = 0
        while i < len(lines) and not (i > 0 and lines[i].strip().endswith('"""')):
            i += 1
        src = "\n".join(lines[i + 1 :])
    (STAGES / "document_loader.py").write_text(
        '"""Markdown load, structural split, semantic splitter (from 1_2_0_2 module1)."""\n'
        "from __future__ import annotations\n\n" + src.lstrip(),
        encoding="utf-8",
    )

    meta = (ROOT / "_extract_metadata.py").read_text(encoding="utf-8")
    body = meta.split("# ==================== 模块2", 1)[-1].lstrip()
    (STAGES / "metadata_enhance.py").write_text(
        '"""DC metadata and relation enhancement (from 1_2_0_2 module2)."""\n'
        "from __future__ import annotations\n\n" + body,
        encoding="utf-8",
    )

    chunk = (ROOT / "_extract_cell_18.py").read_text(encoding="utf-8")
    (STAGES / "chunk_merge.py").write_text(
        '"""Chunk dedup within same filename (from 1_2_0_2 module5)."""\n'
        "from __future__ import annotations\n\n" + chunk.split("# 模块5", 1)[-1].lstrip(),
        encoding="utf-8",
    )

    nb = json.loads((REPO / "1_2_1_2pagerankMetapath.ipynb").read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        s = "".join(cell.get("source", []))
        if "SUBGRAPH_CONFIGS" in s and "_compute_and_write" in s:
            start = s.index("SUBGRAPH_CONFIGS = {")
            end = s.index('url = "bolt://')
            (STAGES / "pagerank_config.py").write_text(
                '"""GDS subgraph projections for PageRank E segment (from 1_2_1_2)."""\n'
                "from __future__ import annotations\n\n" + s[start:end],
                encoding="utf-8",
            )
            break

    print("assembled stage modules")


if __name__ == "__main__":
    main()
