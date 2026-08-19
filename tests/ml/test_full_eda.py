from ml.eda.full_eda import (
    FIGURES_DIR,
    cross_source_comparison,
    leakage_review,
    load_combined,
    run_full_eda,
    structural_audit,
    target_analysis,
)


def test_structural_audit_finds_no_leakage_or_geo_columns():
    df = load_combined()
    report = structural_audit(df)
    assert report["shape"]["rows"] == 21043
    assert report["leakage_columns_present"] == []
    assert report["zero_variance_geo_columns_present"] == []
    assert report["duplicate_rows"] == 0
    assert report["duplicate_customer_ids"] == 0


def test_target_analysis_churn_rate_matches_known_band():
    df = load_combined()
    result = target_analysis(df)
    # IBM alone is 26.54%; blending in the higher-churn synthetic sources
    # (Pakistan ~31%, India ~33%) should land the combined rate a bit above
    # IBM's but still in the realistic band documented in validate.py.
    assert 0.20 <= result["overall_churn_rate"] <= 0.40
    assert set(result["churn_rate_by_source"].keys()) == {"IBM", "Pakistan-Synthetic", "India-Synthetic"}


def test_leakage_review_confirms_exclusions_and_reviews_cltv():
    df = load_combined()
    result = leakage_review(df)
    assert result["churn_score_excluded"] is True
    assert result["churn_reason_excluded"] is True
    assert result["cltv_decision"] in {"include_as_candidate_feature", "exclude_as_leakage_like"}
    assert isinstance(result["cltv_correlation_with_target"], float)


def test_cross_source_comparison_covers_all_three_sources():
    df = load_combined()
    result = cross_source_comparison(df)
    assert set(result.keys()) == {"IBM", "Pakistan-Synthetic", "India-Synthetic"}
    assert result["IBM"]["row_count"] == 7043
    assert result["Pakistan-Synthetic"]["row_count"] == 7000
    assert result["India-Synthetic"]["row_count"] == 7000


def test_run_full_eda_all_checks_pass_and_figures_exist():
    report = run_full_eda()
    assert report["all_checks_passed"] is True
    assert report["checks"]["leakage_columns_absent"] is True
    assert report["checks"]["figures_generated"] > 0

    for relative_path in report["distribution_figures"]:
        assert (FIGURES_DIR.parent.parent.parent / relative_path).exists()
    for relative_path in report["relationship_analysis"]["figures"]:
        assert (FIGURES_DIR.parent.parent.parent / relative_path).exists()
