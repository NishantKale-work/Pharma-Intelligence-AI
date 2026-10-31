from app.core.data_quality import validate_project_data


def test_all_source_datasets_validate():
    results = validate_project_data()

    assert set(results) == {
        "company_data",
        "therapeutic_group_data",
        "value_unit_data",
        "market_therapeutic_group_data",
    }

    for name, result in results.items():
        assert result["status"] == "success", (
            f"{name} failed: {result}"
        )