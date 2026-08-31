"""Patch notebook cell 13: deepseek-chat model + MAX_DOCS=all."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
nb_path = ROOT / "1_2_0_2build_kg__neo4j.ipynb"
nb = json.loads(nb_path.read_text(encoding="utf-8"))
src = "".join(nb["cells"][13]["source"])
src = src.replace('DEEPSEEK_MODEL    = "deepseek-v4-flash"', 'DEEPSEEK_MODEL    = "deepseek-chat"')
src = src.replace("MAX_DOCS = 1", 'MAX_DOCS = "all"')
nb["cells"][13]["source"] = [src]
nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Updated cell 13: deepseek-chat, MAX_DOCS=all")
