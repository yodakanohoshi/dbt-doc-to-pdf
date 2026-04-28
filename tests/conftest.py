from pathlib import Path

import pytest

from dbt_doc_to_pdf.extractor import extract_models
from dbt_doc_to_pdf.loader import load_catalog, load_manifest

SAMPLE_TARGET = Path(__file__).parent.parent / "sample_project" / "target"


@pytest.fixture(scope="session")
def manifest() -> dict:
    return load_manifest(SAMPLE_TARGET)


@pytest.fixture(scope="session")
def catalog() -> dict:
    return load_catalog(SAMPLE_TARGET)


@pytest.fixture(scope="session")
def models(manifest, catalog):
    return extract_models(manifest, catalog)


@pytest.fixture(scope="session")
def html_path(tmp_path_factory, models):
    from dbt_doc_to_pdf.html_gen import generate_html

    out = tmp_path_factory.mktemp("html") / "catalog.html"
    generate_html(models, out, project_name="sample_project")
    return out


@pytest.fixture(scope="session")
def html_text(html_path) -> str:
    return html_path.read_text(encoding="utf-8")
