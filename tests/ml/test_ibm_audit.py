from ml.eda.ibm_audit import audit, load_raw, verify_against_documented_facts


def test_ibm_audit_matches_documented_facts():
    df = load_raw()
    report = audit(df)
    mismatches = verify_against_documented_facts(report)
    assert mismatches == []


def test_ibm_raw_shape():
    df = load_raw()
    assert df.shape == (7043, 33)


def test_ibm_no_duplicate_customer_ids():
    df = load_raw()
    assert df["CustomerID"].duplicated().sum() == 0
