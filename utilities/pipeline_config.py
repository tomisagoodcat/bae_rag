"""Pipeline experiment variant configuration (Scheme A: global PIPELINE_VARIANT)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, List, Optional

VALID_PIPELINE_VARIANTS = frozenset({"full", "no_hierarchy"})


@dataclass(frozen=True)
class PipelineConfig:
    """Controls multi-dimensional retrieval (r, l, κ + G_sub)."""

    variant: str = "full"
    # None = 全部 κ；非 None = 当前实验启用的 κ 子集（见 utilities.olap_modes）
    allowed_olap_modes: Optional[FrozenSet[str]] = None

    def __post_init__(self) -> None:
        if self.variant not in VALID_PIPELINE_VARIANTS:
            raise ValueError(
                f"无效 PIPELINE_VARIANT={self.variant!r}；"
                f"合法值: {sorted(VALID_PIPELINE_VARIANTS)}"
            )

    @property
    def multi_dim_enabled(self) -> bool:
        return self.variant == "full"

    @property
    def kappa_routing_enabled(self) -> bool:
        return self.variant == "full"

    @property
    def gsub_enabled(self) -> bool:
        return self.variant == "full"

    def feature_flags(self) -> Dict[str, bool]:
        flags: Dict[str, bool] = {
            "multi_dim_retrieval": self.multi_dim_enabled,
            "kappa_routing_drill_roll_sibling": self.kappa_routing_enabled,
            "gsub_rank_bias": self.gsub_enabled,
            "recall_module_flat": True,
            "path_level_mid_low_navigation": self.multi_dim_enabled,
        }
        if self.allowed_olap_modes is not None:
            flags["olap_modes_restricted"] = True
        return flags

    def apply_olap_route_override(
        self,
        routed_olap: Dict[str, Any],
        *,
        dialogue_turn: int,
        llm: Any,
        query: str,
    ) -> Dict[str, Any]:
        """校正 κ：no_hierarchy 强制 first_turn；allowed_olap_modes 做 clamp。"""
        from utilities.olap_modes import clamp_routed_olap

        out = dict(routed_olap)
        if self.variant != "full" and dialogue_turn > 0:
            from utilities.dialogue_routing import route_first_turn

            first = route_first_turn(llm, query)
            out = {"kappa": "first_turn", "path_level": first["path_level"]}
        if self.allowed_olap_modes:
            k, lv = clamp_routed_olap(
                str(out.get("kappa") or "first_turn"),
                str(out.get("path_level") or "mid"),
                self.allowed_olap_modes,
            )
            if k != out.get("kappa"):
                out = {**out, "kappa": k, "path_level": lv, "kappa_clamped": True}
            else:
                out["path_level"] = lv
        return out

    def apply_route_override(
        self,
        routed: Dict[str, Any],
        *,
        dialogue_turn: int,
        llm: Any,
        query: str,
        route_modules_first_turn: Callable[[Any, str], List[str]],
    ) -> Dict[str, Any]:
        """
        full: return routed unchanged.
        no_hierarchy: turn>=1 forces κ=first_turn; l 仍由 route_first_turn LLM 决定。
        """
        if self.variant == "full":
            return routed
        if dialogue_turn == 0:
            return routed
        from utilities.dialogue_routing import route_first_turn

        first = route_first_turn(llm, query)
        return {
            "kappa": "first_turn",
            "path_level": first["path_level"],
            "target_subgraphs": first["target_subgraphs"],
        }

    def expected_kappa_for_turn(self, turn_index: int, annotated_kappa: str | None) -> str | None:
        """Expected κ for evaluation: no_hierarchy turn>=2 always first_turn."""
        if self.variant == "full":
            return annotated_kappa
        if turn_index <= 1:
            return annotated_kappa or "first_turn"
        return "first_turn"

    def expected_l_for_turn(self, turn_index: int, annotated_l: str | None) -> str | None:
        if self.variant == "full":
            return annotated_l
        return annotated_l


_PIPELINE_CONFIG = PipelineConfig(variant="full")


def get_pipeline_config() -> PipelineConfig:
    return _PIPELINE_CONFIG


def set_pipeline_variant(variant: str) -> PipelineConfig:
    global _PIPELINE_CONFIG
    cur = _PIPELINE_CONFIG
    _PIPELINE_CONFIG = PipelineConfig(
        variant=variant, allowed_olap_modes=cur.allowed_olap_modes
    )
    return _PIPELINE_CONFIG


def set_olap_modes(allowed: Optional[FrozenSet[str]]) -> PipelineConfig:
    """``allowed=None`` 表示实验不限制 κ。"""
    global _PIPELINE_CONFIG
    cur = _PIPELINE_CONFIG
    _PIPELINE_CONFIG = PipelineConfig(
        variant=cur.variant, allowed_olap_modes=allowed
    )
    return _PIPELINE_CONFIG
