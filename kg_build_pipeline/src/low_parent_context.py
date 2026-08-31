"""Build parent-scoped text contexts for Low Pass1 / Pass2 extraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChunkSnapshot:
    chunk_id: Optional[str] = None
    index: Optional[int] = None
    filename: Optional[str] = None
    text: str = ""
    role: str = "current"  # previous | current | next | original


@dataclass
class ParentContext:
    """Role-separated text window for one mid parent."""

    parent_element_id: str
    parent_name: Optional[str] = None
    parent_labels: List[str] = field(default_factory=list)
    parent_original_text: str = ""
    filename: str = ""
    home_chunks: List[ChunkSnapshot] = field(default_factory=list)
    previous_chunks: List[ChunkSnapshot] = field(default_factory=list)
    next_chunks: List[ChunkSnapshot] = field(default_factory=list)
    pass_kind: str = "pass1"  # pass1 | pass2

    def evidence_corpus(self) -> str:
        """Parent original ∪ home chunk text (H09-A support zone)."""
        parts: List[str] = []
        if self.parent_original_text.strip():
            parts.append(self.parent_original_text.strip())
        for c in self.home_chunks:
            t = (c.text or "").strip()
            if t and t not in parts:
                parts.append(t)
        return "\n\n".join(parts)

    def pass1_prompt_text(self) -> str:
        """Pass1: original_text + home chunk only (no neighbors)."""
        blocks: List[str] = []
        if self.parent_original_text.strip():
            blocks.append(
                f"[PARENT_ORIGINAL_TEXT]\n{self.parent_original_text.strip()}"
            )
        for i, c in enumerate(self.home_chunks):
            t = (c.text or "").strip()
            if t:
                blocks.append(f"[HOME_CHUNK index={c.index} id={c.chunk_id}]\n{t}")
        return "\n\n".join(blocks)

    def pass2_prompt_text(self) -> str:
        """Pass2: role-separated previous / original / current / next."""
        blocks: List[str] = []
        for c in self.previous_chunks:
            t = (c.text or "").strip()
            if t:
                blocks.append(f"[PREVIOUS_CHUNK index={c.index}]\n{t}")
        if self.parent_original_text.strip():
            blocks.append(
                f"[PARENT_ORIGINAL_TEXT]\n{self.parent_original_text.strip()}"
            )
        for c in self.home_chunks:
            t = (c.text or "").strip()
            if t:
                blocks.append(f"[CURRENT_CHUNK index={c.index}]\n{t}")
        for c in self.next_chunks:
            t = (c.text or "").strip()
            if t:
                blocks.append(f"[NEXT_CHUNK index={c.index}]\n{t}")
        return "\n\n".join(blocks)

    def extraction_text(self) -> str:
        if self.pass_kind == "pass2":
            return self.pass2_prompt_text()
        return self.pass1_prompt_text()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_element_id": self.parent_element_id,
            "parent_name": self.parent_name,
            "parent_labels": list(self.parent_labels),
            "filename": self.filename,
            "pass_kind": self.pass_kind,
            "parent_original_len": len(self.parent_original_text or ""),
            "home_chunk_count": len(self.home_chunks),
            "previous_chunk_count": len(self.previous_chunks),
            "next_chunk_count": len(self.next_chunks),
        }


class ContextTextNode:
    """Minimal text node compatible with extract_document_schemas."""

    def __init__(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._text = text or ""
        self.metadata = metadata or {}

    def get_text(self) -> str:
        return self._text

    def get_content(self) -> str:
        return self._text


def context_to_text_nodes(ctx: ParentContext) -> List[ContextTextNode]:
    """One synthetic node carrying the full role-structured window."""
    text = ctx.extraction_text()
    home = ctx.home_chunks[0] if ctx.home_chunks else None
    md: Dict[str, Any] = {
        "section_role": "All",
        "filename": ctx.filename,
        "parent_element_id": ctx.parent_element_id,
        "pass_kind": ctx.pass_kind,
    }
    if home:
        md["chunk_id"] = home.chunk_id
        md["chunk_index"] = home.index
    return [ContextTextNode(text, md)]


def build_pass1_context(
    *,
    parent_element_id: str,
    parent_name: Optional[str],
    parent_labels: List[str],
    parent_original_text: str,
    filename: str,
    home_chunks: List[Dict[str, Any]],
    use_parent_original_text: bool = True,
    use_current_chunk: bool = True,
) -> ParentContext:
    homes: List[ChunkSnapshot] = []
    if use_current_chunk:
        for c in home_chunks:
            homes.append(
                ChunkSnapshot(
                    chunk_id=c.get("id") or c.get("chunk_id"),
                    index=c.get("index"),
                    filename=c.get("filename") or filename,
                    text=str(c.get("text") or ""),
                    role="current",
                )
            )
    return ParentContext(
        parent_element_id=parent_element_id,
        parent_name=parent_name,
        parent_labels=list(parent_labels or []),
        parent_original_text=(parent_original_text or "") if use_parent_original_text else "",
        filename=filename,
        home_chunks=homes,
        pass_kind="pass1",
    )


def build_pass2_context(
    pass1: ParentContext,
    *,
    previous_chunks: List[Dict[str, Any]],
    next_chunks: List[Dict[str, Any]],
) -> ParentContext:
    prev = [
        ChunkSnapshot(
            chunk_id=c.get("id") or c.get("chunk_id"),
            index=c.get("index"),
            filename=c.get("filename") or pass1.filename,
            text=str(c.get("text") or ""),
            role="previous",
        )
        for c in previous_chunks
    ]
    nxt = [
        ChunkSnapshot(
            chunk_id=c.get("id") or c.get("chunk_id"),
            index=c.get("index"),
            filename=c.get("filename") or pass1.filename,
            text=str(c.get("text") or ""),
            role="next",
        )
        for c in next_chunks
    ]
    return ParentContext(
        parent_element_id=pass1.parent_element_id,
        parent_name=pass1.parent_name,
        parent_labels=list(pass1.parent_labels),
        parent_original_text=pass1.parent_original_text,
        filename=pass1.filename,
        home_chunks=list(pass1.home_chunks),
        previous_chunks=prev,
        next_chunks=nxt,
        pass_kind="pass2",
    )


def text_supported_by_corpus(child_text: str, corpus: str) -> bool:
    """True if child original_text is supported by parent∪home corpus (substring)."""
    child = (child_text or "").strip().lower()
    if not child:
        return False
    base = (corpus or "").lower()
    if child in base:
        return True
    # Tolerate short paraphrases: require substantial overlap via containment of head
    head = child[:80]
    return bool(head) and head in base
