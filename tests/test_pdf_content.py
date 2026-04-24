"""Integration tests: verify PDF content matches dbt metadata."""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_text(pdf_text: str) -> str:
    return pdf_text


# ---------------------------------------------------------------------------
# Table-level tests
# ---------------------------------------------------------------------------

class TestTableInfo:
    def test_all_model_names_in_pdf(self, pdf_text, models):
        for model in models:
            assert model.name in pdf_text, f"モデル名 '{model.name}' が PDF に見つかりません"

    def test_model_descriptions_in_pdf(self, pdf_text, models):
        for model in models:
            if model.description:
                assert model.description in pdf_text, (
                    f"モデル '{model.name}' の説明が PDF に見つかりません: {model.description!r}"
                )

    def test_layer_labels_in_pdf(self, pdf_text):
        assert "Staging" in pdf_text, "Staging レイヤーラベルが PDF にありません"
        assert "Ecommerce" in pdf_text, "Ecommerce レイヤーラベルが PDF にありません"

    def test_materialization_in_pdf(self, pdf_text, models):
        for model in models:
            assert model.materialized in pdf_text, (
                f"マテリアライズ '{model.materialized}' が PDF にありません"
            )

    def test_schema_in_pdf(self, pdf_text, models):
        schemas = {m.schema for m in models}
        for schema in schemas:
            assert schema in pdf_text, f"スキーマ '{schema}' が PDF にありません"


# ---------------------------------------------------------------------------
# Column-level tests
# ---------------------------------------------------------------------------

class TestColumnInfo:
    def test_all_column_names_in_pdf(self, pdf_text, models):
        for model in models:
            for col in model.columns:
                assert col.name in pdf_text, (
                    f"{model.name}.{col.name} が PDF に見つかりません"
                )

    def test_column_descriptions_in_pdf(self, pdf_table_cells, models):
        """テーブルセルから説明文を検証 (セル内折り返しに対応)。"""
        for model in models:
            for col in model.columns:
                if col.description:
                    assert col.description in pdf_table_cells, (
                        f"{model.name}.{col.name} の説明 {col.description!r} が PDF にありません"
                    )

    def test_data_types_in_pdf(self, pdf_text, models):
        expected_types = {"INTEGER", "VARCHAR", "DATE", "BIGINT"}
        for dtype in expected_types:
            assert dtype in pdf_text, f"データ型 '{dtype}' が PDF にありません"

    def test_test_names_in_pdf(self, pdf_text, models):
        has_tests = any(col.tests for m in models for col in m.columns)
        assert has_tests, "テスト情報が抽出されていません"

        test_names = {t for m in models for col in m.columns for t in col.tests}
        for test_name in test_names:
            assert test_name in pdf_text, f"テスト名 '{test_name}' が PDF にありません"


# ---------------------------------------------------------------------------
# Lineage / ER section tests
# ---------------------------------------------------------------------------

class TestLineage:
    def test_er_section_title_in_pdf(self, pdf_text):
        assert "ER" in pdf_text, "ER 図セクションが PDF にありません"

    def test_dependency_models_present(self, pdf_text, models):
        # upstream モデルも PDF に掲載されていること
        all_deps = {dep for m in models for dep in m.depends_on}
        all_names = {m.name for m in models}
        for dep in all_deps:
            assert dep in all_names, f"依存モデル '{dep}' が models リストに存在しません"
            assert dep in pdf_text, f"依存モデル '{dep}' が PDF に見つかりません"


# ---------------------------------------------------------------------------
# Metadata consistency tests
# ---------------------------------------------------------------------------

class TestMetadataConsistency:
    def test_column_count_consistency(self, models):
        """manifest と catalog でカラム数が一致すること。"""
        by_name = {m.name: m for m in models}
        # catalog から直接件数確認は extractor 経由で行う
        # customers は 9 columns (schema.yml 定義と一致)
        assert len(by_name["customers"].columns) == 9
        assert len(by_name["orders"].columns) == 7

    def test_no_empty_data_types_for_catalog_models(self, models):
        """catalog.json に存在するモデルのカラムはデータ型を持つ。"""
        catalog_models = {"customers", "orders", "stg_customers"}
        by_name = {m.name: m for m in models}
        for model_name in catalog_models:
            for col in by_name[model_name].columns:
                assert col.data_type, (
                    f"{model_name}.{col.name} のデータ型が空です (catalog に存在するはず)"
                )

    def test_pdf_page_count(self, pdf_path):
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            # 表紙 + 目次 + コンテンツ複数ページ + ER図 >= 4 ページ
            assert len(pdf.pages) >= 4, f"ページ数が少なすぎます: {len(pdf.pages)}"

    def test_cover_contains_project_name(self, pdf_text):
        assert "sample_project" in pdf_text, "表紙にプロジェクト名がありません"
