import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "1_2_0_2build_kg__neo4j.ipynb"
nb = json.loads(NB.read_text(encoding="utf-8"))
src = "".join(nb["cells"][13]["source"])
needle = "verify_subgraph_assignment(neo4j_driver, entity_labels_for_sg)"
if "_assert_labeled_nodes_exist(sg_stats)" not in src:
    src = src.replace(
        needle,
        needle + "\n            _assert_labeled_nodes_exist(sg_stats)",
        1,
    )
    nb["cells"][13]["source"] = [src]
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print("patched step 6.5")
else:
    print("already ok")
