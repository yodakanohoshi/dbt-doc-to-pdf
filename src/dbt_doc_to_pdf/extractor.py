from typing import Any

from .models import ColumnInfo, ModelInfo


def extract_models(manifest: dict[str, Any], catalog: dict[str, Any]) -> list[ModelInfo]:
    catalog_nodes = catalog.get("nodes", {})
    col_tests: dict[str, dict[str, list[str]]] = {}

    # Build column -> tests mapping from test nodes
    for node in manifest["nodes"].values():
        if node["resource_type"] != "test":
            continue
        attached = node.get("attached_node", "")
        col = node.get("column_name", "")
        test_name = node.get("test_metadata", {}).get("name", "")
        if attached and col and test_name:
            col_tests.setdefault(attached, {}).setdefault(col, []).append(test_name)

    models: list[ModelInfo] = []
    for uid, node in manifest["nodes"].items():
        if node["resource_type"] != "model":
            continue

        catalog_cols = catalog_nodes.get(uid, {}).get("columns", {})

        columns: list[ColumnInfo] = []
        for col_name, col_data in node.get("columns", {}).items():
            data_type = catalog_cols.get(col_name.lower(), {}).get("type", "")
            tests = col_tests.get(uid, {}).get(col_name, [])
            columns.append(ColumnInfo(
                name=col_name,
                description=col_data.get("description", ""),
                data_type=data_type,
                tests=tests,
            ))

        path = node.get("path", "")
        layer = path.split("/")[0] if "/" in path else "other"

        depends_on = [
            dep.split(".")[-1]
            for dep in node.get("depends_on", {}).get("nodes", [])
            if dep.startswith("model.")
        ]

        models.append(ModelInfo(
            unique_id=uid,
            name=node["name"],
            schema=node.get("schema", ""),
            database=node.get("database", ""),
            description=node.get("description", ""),
            materialized=node.get("config", {}).get("materialized", ""),
            columns=columns,
            depends_on=depends_on,
            layer=layer,
            path=path,
        ))

    return sorted(models, key=lambda m: (m.layer, m.name))
