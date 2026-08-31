"""Smoke: low_expand dry-run imports + PASS-doc listing (mock Neo4j optional)."""
from __future__ import annotations

from unittest.mock import MagicMock

from kg_build_pipeline.src.low_extract_log import LowExtractLogger
from kg_build_pipeline.src.pipeline_event_format import format_pipeline_event
from kg_build_pipeline.src.stages.low_parents import list_pass_filenames
from kg_build_pipeline.src.stages.mid_quality_gate import persist_mid_gate_status


def test_event_format_low() -> None:
    line = format_pipeline_event(
        {"type": "low_pass1", "filename": "doc.md", "parent": "E1", "schema_rows": 3}
    )
    assert line and "[low] pass1" in line


def test_list_pass_filenames_mock() -> None:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    session.run.return_value.data.return_value = [{"filename": "doc_04.md"}]
    names = list_pass_filenames(driver, "neo4j")
    assert names == ["doc_04.md"]


def test_persist_mid_gate_status_mock() -> None:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    session.run.return_value.single.return_value = {"cnt": 4}
    n = persist_mid_gate_status(driver, "neo4j", "doc.md", status="PASS", score=0.82)
    assert n == 4
    session.run.assert_called()
    kwargs = session.run.call_args.kwargs
    assert kwargs.get("status") == "PASS"


def test_low_logger_roundtrip(tmp_path) -> None:
    # tmp_path may be pytest; allow pathlib Path
    from pathlib import Path

    log_dir = Path(tmp_path) if not isinstance(tmp_path, Path) else tmp_path
    logger = LowExtractLogger(log_dir=log_dir)
    path = logger.start_session(["doc_04.md"])
    logger.log_parent("doc_04.md", {"parent": "E1", "status": "ACCEPT"})
    logger.close()
    text = path.read_text(encoding="utf-8")
    assert "session_start" in text
    assert "ACCEPT" in text


def main() -> None:
    import tempfile
    from pathlib import Path

    test_event_format_low()
    test_list_pass_filenames_mock()
    test_persist_mid_gate_status_mock()
    with tempfile.TemporaryDirectory() as td:
        test_low_logger_roundtrip(Path(td))
    print("test_low_expand_smoke: OK")


if __name__ == "__main__":
    main()
