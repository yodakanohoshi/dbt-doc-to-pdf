import json
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
def pdf_path(tmp_path_factory, models):
    from dbt_doc_to_pdf.pdf_gen import generate_pdf

    out = tmp_path_factory.mktemp("pdf") / "catalog.pdf"
    generate_pdf(models, out, project_name="sample_project")
    return out


@pytest.fixture(scope="session")
def pdf_text(pdf_path) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n".join(pages)


@pytest.fixture(scope="session")
def pdf_table_cells(pdf_path) -> str:
    """All table cell text concatenated — reliable for multi-line cell checks."""
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    for cell in row:
                        if cell:
                            parts.append(cell.replace("\n", " "))
    return " | ".join(parts)
