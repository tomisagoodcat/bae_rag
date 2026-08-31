# BAE Ontology V6 (OOPS!-revised)

Generated from `../BAE_v3_clean.ttl` by scripts in `schema/oops_revise/`.

| File | Description |
|------|-------------|
| `BAE.ttl` | Revised ontology (IRI `https://bdi.whu.edu.cn/BAE`, version `6.0-oops`) |
| `BAE.rdf` | RDF/XML submitted to OOPS! |
| `BAE_oops_request.xml` | OOPSRequest wrapper |
| `BAE_oops_report.xml` | Authoritative OOPS! XML response |
| `BAE_oops_report.md` | Human-readable OOPS! report |
| `CHANGELOG_OOPS.md` | What was changed vs v3_clean |

Regenerate:

```bash
python schema/oops_revise/apply_oops_fixes.py
python schema/oops_revise/run_oops_eval.py --ttl schema/ttl/V6/BAE.ttl --out-dir schema/ttl/V6
```
