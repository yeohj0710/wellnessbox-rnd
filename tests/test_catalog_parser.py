from wellnessbox_rnd.domain.catalog import canonicalize_catalog_term


def test_canonicalize_catalog_term_matches_long_current_supplement_title() -> None:
    assert (
        canonicalize_catalog_term("Nordic Naturals Ultimate Omega Lemon Flavor Soft Gels")
        == "omega3"
    )


def test_canonicalize_catalog_term_matches_long_avoid_title() -> None:
    assert (
        canonicalize_catalog_term(
            "Renew Life Extra Care Ultimate Flora Probiotic 50 Billion CFU Capsules"
        )
        == "probiotics"
    )


def test_canonicalize_catalog_term_keeps_ambiguous_generic_title_unmatched() -> None:
    assert canonicalize_catalog_term("Daily Wellness Capsules") is None


def test_canonicalize_catalog_term_prefers_b_complex_over_vitamin_c_false_positive() -> None:
    assert (
        canonicalize_catalog_term("Garden of Life Vitamin Code Raw B-Complex")
        == "vitamin_b_complex"
    )
