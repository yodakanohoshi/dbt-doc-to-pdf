"""Integration tests: verify HTML content matches dbt metadata."""


class TestTableInfo:
    def test_all_model_names_in_html(self, html_text, models):
        for model in models:
            assert model.name in html_text, f"モデル名 '{model.name}' が HTML に見つかりません"

    def test_model_descriptions_in_html(self, html_text, models):
        for model in models:
            if model.description:
                assert model.description in html_text, (
                    f"モデル '{model.name}' の説明が HTML に見つかりません: {model.description!r}"
                )

    def test_layer_labels_in_html(self, html_text):
        assert "staging" in html_text, "staging レイヤーが HTML にありません"
        assert "ecommerce" in html_text, "ecommerce レイヤーが HTML にありません"

    def test_materialization_in_html(self, html_text, models):
        for model in models:
            assert model.materialized in html_text, (
                f"マテリアライズ '{model.materialized}' が HTML にありません"
            )

    def test_schema_in_html(self, html_text, models):
        for schema in {m.schema for m in models}:
            assert schema in html_text, f"スキーマ '{schema}' が HTML にありません"


class TestColumnInfo:
    def test_all_column_names_in_html(self, html_text, models):
        for model in models:
            for col in model.columns:
                assert col.name in html_text, (
                    f"{model.name}.{col.name} が HTML に見つかりません"
                )

    def test_column_descriptions_in_html(self, html_text, models):
        for model in models:
            for col in model.columns:
                if col.description:
                    assert col.description in html_text, (
                        f"{model.name}.{col.name} の説明が HTML にありません: {col.description!r}"
                    )

    def test_data_types_in_html(self, html_text):
        expected_types = {"INTEGER", "VARCHAR", "DATE", "BIGINT"}
        for dtype in expected_types:
            assert dtype in html_text, f"データ型 '{dtype}' が HTML にありません"

    def test_test_names_in_html(self, html_text, models):
        has_tests = any(col.tests for m in models for col in m.columns)
        assert has_tests, "テスト情報が抽出されていません"

        for test_name in {t for m in models for col in m.columns for t in col.tests}:
            assert test_name in html_text, f"テスト名 '{test_name}' が HTML にありません"



class TestMetadataConsistency:
    def test_column_count_consistency(self, models):
        by_name = {m.name: m for m in models}
        assert len(by_name["customers"].columns) == 9
        assert len(by_name["orders"].columns) == 7

    def test_project_name_in_html(self, html_text):
        assert "sample_project" in html_text, "プロジェクト名が HTML にありません"

    def test_html_is_valid_structure(self, html_text):
        assert html_text.startswith("<!DOCTYPE html>")
        assert "</html>" in html_text
        assert '<meta charset="utf-8">' in html_text
