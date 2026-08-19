from ml.data_generation.validate import validate


def test_all_generator_validation_checks_pass():
    report = validate()
    assert report["all_checks_passed"] is True, report["checks"]


def test_sanity_check_auc_not_trivial_or_random():
    report = validate()
    auc = report["sanity_check_logistic_regression"]["auc"]
    assert 0.5 < auc < 1.0


def test_no_single_feature_near_perfectly_separates_churn():
    report = validate()
    for feature, auc in report["single_feature_auc"].items():
        assert auc is not None
        assert auc < 0.95, f"{feature} AUC too close to 1.0: {auc}"
