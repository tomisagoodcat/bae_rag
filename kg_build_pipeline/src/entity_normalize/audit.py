"""In-memory audit records for entity_normalize (returned in stage stats)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class NormalizeAudit:
    hard_merge_groups: int = 0
    hard_merge_nodes_removed: int = 0
    external_links_created: int = 0
    external_links_llm: int = 0
    external_skipped_no_index: int = 0
    external_skipped_no_match: int = 0
    external_skipped_specimen_policy: int = 0
    external_skipped_excluded: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)

    def log(self, event_type: str, **payload: Any) -> None:
        self.events.append({"type": event_type, **payload})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hard_merge_groups": self.hard_merge_groups,
            "hard_merge_nodes_removed": self.hard_merge_nodes_removed,
            "external_links_created": self.external_links_created,
            "external_links_llm": self.external_links_llm,
            "external_skipped_no_index": self.external_skipped_no_index,
            "external_skipped_no_match": self.external_skipped_no_match,
            "external_skipped_specimen_policy": self.external_skipped_specimen_policy,
            "external_skipped_excluded": self.external_skipped_excluded,
            "event_count": len(self.events),
            "events": self.events[:500],
        }
