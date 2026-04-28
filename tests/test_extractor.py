"""Unit tests for metadata extraction logic."""
import pytest

from dbt_doc_to_pdf.models import ColumnInfo, ModelInfo


def test_model_count(models):
    assert len(models) == 5


def test_model_names(models):
    names = {m.name for m in models}
    assert names == {"customers", "orders", "stg_customers", "stg_orders", "stg_order_items"}


def test_layer_assignment(models):
    by_name = {m.name: m for m in models}
    assert by_name["customers"].layer == "ecommerce"
    assert by_name["orders"].layer == "ecommerce"
    assert by_name["stg_customers"].layer == "staging"
    assert by_name["stg_orders"].layer == "staging"
    assert by_name["stg_order_items"].layer == "staging"


def test_descriptions_populated(models):
    for model in models:
        assert model.description, f"{model.name} has no description"


def test_column_count(models):
    by_name = {m.name: m for m in models}
    assert len(by_name["customers"].columns) == 9
    assert len(by_name["orders"].columns) == 7
    assert len(by_name["stg_customers"].columns) == 5
    assert len(by_name["stg_orders"].columns) == 5
    assert len(by_name["stg_order_items"].columns) == 5


def test_column_descriptions(models):
    """Every column defined in schema.yml should have a description."""
    for model in models:
        for col in model.columns:
            assert col.description, f"{model.name}.{col.name} has no description"


def test_column_data_types_from_catalog(models):
    """Columns should have data types populated from catalog.json."""
    by_name = {m.name: m for m in models}
    customers_cols = {c.name: c for c in by_name["customers"].columns}
    assert customers_cols["customer_id"].data_type == "INTEGER"
    assert customers_cols["lifetime_value"].data_type == "HUGEINT"
    assert customers_cols["created_at"].data_type == "TIMESTAMP WITH TIME ZONE"


def test_tests_attached_to_columns(models):
    """Test names should be attached to the appropriate columns."""
    by_name = {m.name: m for m in models}

    customers_cols = {c.name: c for c in by_name["customers"].columns}
    assert "unique" in customers_cols["customer_id"].tests
    assert "not_null" in customers_cols["customer_id"].tests

    orders_cols = {c.name: c for c in by_name["orders"].columns}
    assert "unique" in orders_cols["order_id"].tests
    assert "not_null" in orders_cols["customer_id"].tests



def test_materialization(models):
    by_name = {m.name: m for m in models}
    assert by_name["customers"].materialized == "table"
    assert by_name["orders"].materialized == "table"
    assert by_name["stg_customers"].materialized == "view"


def test_schema_and_database(models):
    for model in models:
        assert model.schema, f"{model.name} missing schema"
        assert model.database, f"{model.name} missing database"
