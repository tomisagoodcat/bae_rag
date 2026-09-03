"""Lexicon gates for mp_challenges (run: python -m kg_build_pipeline.scripts.test_argument_polarity)."""
from __future__ import annotations

from types import SimpleNamespace

from kg_build_pipeline.src.argument_cleanup import is_proper_substring, original_texts_equal
from kg_build_pipeline.src.argument_polarity import (
    filter_nodes_with_challenge_language,
    should_skip_challenges_extract,
    text_has_challenge_language,
)


def main() -> None:
    support = "These results support the conclusion that grain Cd was below the limit."
    assert not text_has_challenge_language(support)
    assert should_skip_challenges_extract("mp_challenges", support)
    assert not should_skip_challenges_extract("mp_supports", support)

    refute_en = "These measurements are inconsistent with the earlier claim of low Cd."
    assert text_has_challenge_language(refute_en)
    assert not should_skip_challenges_extract("mp_challenges", refute_en)

    refute_zh = "该结果未能证实前述关于大米重金属质量较好的判断。"
    assert text_has_challenge_language(refute_zh)

    bare = "Heavy-metal control remains a challenge for future work. 仍有挑战。"
    assert not text_has_challenge_language(bare)
    assert should_skip_challenges_extract("mp_challenges", bare)
    assert should_skip_challenges_extract("mp_challenges", "")
    assert should_skip_challenges_extract("mp_challenges", None)

    keep = SimpleNamespace(get_text=lambda: refute_en)
    drop = SimpleNamespace(get_text=lambda: support)
    filtered = filter_nodes_with_challenge_language([drop, keep, drop])
    assert filtered == [keep], filtered

    sg_ot = "344份样品全部合格，表明松江地区消费环节大米重金属质量较好。"
    cl_ot = "松江地区消费环节大米重金属质量较好"
    assert original_texts_equal(sg_ot, sg_ot)
    assert not original_texts_equal(sg_ot, cl_ot)
    assert is_proper_substring(cl_ot, sg_ot)
    assert not is_proper_substring(sg_ot, sg_ot)
    assert not is_proper_substring("镉超标", sg_ot)


if __name__ == "__main__":
    main()
    print("test_argument_polarity: ok")
