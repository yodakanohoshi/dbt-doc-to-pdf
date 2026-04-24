# dbt-doc-to-pdf 設計仕様書

dbt の `dbt docs generate` で生成されるメタデータ (`manifest.json` / `catalog.json`) を読み込み、PDF 形式のテーブルカタログを生成する CLI ツール。

---

## 目次

1. [ゴールと制約](#1-ゴールと制約)
2. [入力データ仕様](#2-入力データ仕様)
3. [アーキテクチャ概要](#3-アーキテクチャ概要)
4. [モジュール設計](#4-モジュール設計)
5. [データモデル](#5-データモデル)
6. [PDF 出力仕様](#6-pdf-出力仕様)
7. [ER 図レイアウトアルゴリズム](#7-er-図レイアウトアルゴリズム)
8. [テスト設計](#8-テスト設計)
9. [既知の制約と設計判断の記録](#9-既知の制約と設計判断の記録)

---

## 1. ゴールと制約

### ゴール

- `dbt docs generate` が出力する JSON メタデータから、読みやすい PDF データカタログを生成する
- テーブル情報・カラム情報・データ型・テスト定義・依存関係（データリネージ）を 1 つの PDF にまとめる

### 制約

- `pandas` は使用しない
- `pip install` で導入可能なライブラリのみ使用する
- 日本語テキストを PDF に出力できること

---

## 2. 入力データ仕様

`dbt docs generate` を実行すると `target/` ディレクトリに以下が生成される。

### manifest.json

dbt プロジェクトの全リソース定義を含む。本ツールが使うフィールドは以下。

| パス | 型 | 内容 |
|------|----|------|
| `nodes.<uid>.resource_type` | string | `"model"` または `"test"` でフィルタ |
| `nodes.<uid>.name` | string | モデル名 |
| `nodes.<uid>.path` | string | `staging/foo.sql` — 先頭ディレクトリをレイヤーとして使用 |
| `nodes.<uid>.description` | string | モデルの説明文 (schema.yml 由来) |
| `nodes.<uid>.columns.<col>.description` | string | カラムの説明文 |
| `nodes.<uid>.config.materialized` | string | `table` / `view` |
| `nodes.<uid>.depends_on.nodes` | string[] | 依存ノードの unique_id 一覧 |
| `nodes.<uid>.schema` | string | DB スキーマ名 |
| `nodes.<uid>.database` | string | DB 名 |
| `nodes.<uid>.attached_node` | string | テストノード: 対象モデルの unique_id |
| `nodes.<uid>.column_name` | string | テストノード: 対象カラム名 |
| `nodes.<uid>.test_metadata.name` | string | テストノード: テスト種別 (`unique` / `not_null` 等) |

### catalog.json

実際に DB を参照して得たスキーマ情報を含む。

| パス | 型 | 内容 |
|------|----|------|
| `nodes.<uid>.columns.<col>.type` | string | カラムの実際のデータ型 (`INTEGER` / `VARCHAR` 等) |

> **注意**: catalog は `dbt docs generate` 実行時に DB にアクセスして取得される。DB が存在しない場合は `nodes` が空になる。

---

## 3. アーキテクチャ概要

```
manifest.json ─┐
               ├─► loader.py ─► extractor.py ─► [ModelInfo]
catalog.json  ─┘                                     │
                                                      ▼
                                              pdf_gen.py
                                             ┌──────────────────┐
                                             │ 表紙             │
                                             │ 目次             │
                                             │ モデル詳細 × N   │
                                             │ ER 図           │──► catalog.pdf
                                             └────────┬─────────┘
                                                      │ build_er_diagram()
                                               er_diagram.py
```

処理フローは **ロード → 変換 → 生成** の一方向パイプラインで、副作用は最後の PDF 書き出しのみ。

---

## 4. モジュール設計

### `loader.py`

```
load_manifest(target_dir: Path) -> dict
load_catalog(target_dir: Path)  -> dict
```

JSON ファイルを読んで Python dict として返すだけ。パースエラーは呼び出し元に委ねる。

---

### `extractor.py`

```
extract_models(manifest: dict, catalog: dict) -> list[ModelInfo]
```

manifest と catalog を受け取り、アプリ内部で使う `ModelInfo` リストに変換する。

**処理順序:**

1. manifest の全ノードから `resource_type == "test"` のノードを走査し、`col_tests[model_uid][col_name] = [test_name, ...]` という辞書を構築する。
2. `resource_type == "model"` のノードを走査し、各カラムについて:
   - 説明文は manifest の `columns.<col>.description`
   - データ型は catalog の `columns.<col>.type` (キーは小文字で照合)
   - テスト一覧は手順 1 で構築した `col_tests` から取得
3. `path` の先頭ディレクトリ (`staging/foo.sql` → `"staging"`) をレイヤーとする
4. `depends_on.nodes` から `model.` プレフィックスのものだけ抽出し、`split(".")[-1]` でモデル名のみを取り出す
5. `(layer, name)` の昇順でソートして返す

---

### `models.py`

変換後の内部表現。2 つのデータクラスのみ。詳細は [§5 データモデル](#5-データモデル) を参照。

---

### `pdf_gen.py`

```
generate_pdf(models: list[ModelInfo], output_path: Path, project_name: str) -> None
```

reportlab の **Platypus** (`SimpleDocTemplate` + Flowable) を使って PDF を構築する。

**主要な内部関数:**

| 関数 | 役割 |
|------|------|
| `_register_fonts()` | `HeiseiKakuGo-W5` CID フォントを pdfmetrics に登録 |
| `_styles()` | 各箇所で使う `ParagraphStyle` をまとめて生成して dict で返す |
| `_cover_page()` | タイトル・プロジェクト名・生成日の表紙ページ Flowable を返す |
| `_toc_page()` | レイヤー別モデル一覧の目次ページ Flowable を返す |
| `_model_section()` | 1 モデル分のヘッダー・メタ情報・カラムテーブルを Flowable のリストで返す |
| `generate_pdf()` | 上記を組み合わせて story を構築し `doc.build()` で PDF を出力する |

**カラムテーブルの列幅 (A4 - 余白 30mm = 165mm を分配):**

| 列 | 幅 |
|----|----|
| # | 8 mm |
| カラム名 | 38 mm |
| データ型 | 38 mm |
| 説明 | 72 mm |
| テスト | 29 mm |

セル内テキストは `Paragraph` でラップしているため長いテキストは自動折り返しになる。

---

### `er_diagram.py`

```
build_er_diagram(models: list[ModelInfo], page_width: float) -> Drawing
```

reportlab の **Graphics** (`Drawing` + `shapes`) で ER 図を描画し、Platypus の Flowable として返す。内部座標系は y 軸が上向き。詳細は [§7 ER 図レイアウトアルゴリズム](#7-er-図レイアウトアルゴリズム) を参照。

---

### `__main__.py`

CLI エントリーポイント。argparse で以下のオプションを受け付ける。

| オプション | デフォルト | 説明 |
|-----------|----------|------|
| `--target-dir` | `./target` | manifest.json / catalog.json のあるディレクトリ |
| `--output` | `./catalog.pdf` | 出力 PDF パス |
| `--project` | `sample_project` | 表紙に表示するプロジェクト名 |

---

## 5. データモデル

```python
@dataclass
class ColumnInfo:
    name: str           # カラム名 (manifest 由来、大文字小文字を保持)
    description: str    # カラムの説明文 (schema.yml 由来)
    data_type: str      # DB の実データ型 (catalog 由来、未存在時は "")
    tests: list[str]    # 適用テスト名一覧 (["unique", "not_null"] 等)

@dataclass
class ModelInfo:
    unique_id: str      # "model.project.name" 形式の manifest UID
    name: str           # モデル名
    schema: str         # DB スキーマ名
    database: str       # DB 名
    description: str    # モデルの説明文 (schema.yml 由来)
    materialized: str   # "table" / "view"
    columns: list[ColumnInfo]
    depends_on: list[str]  # 依存先モデル名のリスト (unique_id でなくモデル名)
    layer: str          # パスの先頭ディレクトリ ("staging" / "ecommerce" 等)
```

---

## 6. PDF 出力仕様

### ページ構成

| ページ | 内容 |
|--------|------|
| 1 | 表紙: タイトル・プロジェクト名・生成日 |
| 2 | 目次: レイヤー別モデル一覧 |
| 3〜N | モデル詳細: レイヤーごとにまとめて掲載 |
| N+1 | ER 図 / データリネージ |

### モデル詳細ページの構成要素

```
┌───────────────────────────────────────┐
│  model_name  (レイヤー色の背景バー)     │
├──────────┬───────────┬────────────────┤
│ レイヤー │ Staging   │ マテリアライズ │ view │
│ スキーマ │ main      │ データベース   │ dev  │
└──────────┴───────────┴────────────────┘
  モデルの説明文
  依存モデル: xxx、yyy

┌─────┬──────────────┬────────────┬──────────┬──────────┐
│  #  │  カラム名    │  データ型  │   説明   │  テスト  │
├─────┼──────────────┼────────────┼──────────┼──────────┤
│  1  │ customer_id  │ INTEGER    │ 顧客ID   │ unique,  │
│     │              │            │          │ not_null │
└─────┴──────────────┴────────────┴──────────┴──────────┘
```

### フォント

| 用途 | フォント | サイズ |
|------|---------|--------|
| 表紙タイトル | HeiseiKakuGo-W5 | 28pt |
| セクション見出し | HeiseiKakuGo-W5 | 16pt |
| モデル名バー | HeiseiKakuGo-W5 | 13pt |
| 本文・表内 | HeiseiKakuGo-W5 | 8〜9pt |

`HeiseiKakuGo-W5` は reportlab に内蔵された Adobe CID フォントで、フォントファイルのインストールなしに日本語を出力できる。

### カラーパレット

| 用途 | カラーコード |
|------|------------|
| テキスト (濃紺) | `#2C3E50` |
| Staging レイヤー | `#2980B9` |
| Ecommerce レイヤー | `#27AE60` |
| その他レイヤー | `#7F8C8D` |
| 表ヘッダー背景 | `#F4F6F7` |
| 表罫線 | `#BDC3C7` |

---

## 7. ER 図レイアウトアルゴリズム

### 前提

- 左列: staging モデル
- 右列: staging 以外のモデル (ecommerce 等)
- 矢印方向: staging ボックスの右端 → ecommerce ボックスの左端 (データの流れ)

### ボックスの高さ計算

```
box_height = HEADER_H(22) + len(columns) × ROW_H(14) + PAD(8)
```

### staging 列の y 座標計算

staging モデルをソート順に積み上げ、各ボックスの `y_bottom` を記録する。

```
y = 0
for model in reversed(staging):
    staging_positions[model.name] = y
    y += box_height(model) + v_gap(16)
```

### ecommerce 列の y 座標計算

各 ecommerce モデルについて、依存先の staging ボックスの **中心 y 座標の平均** を求め、そこにボックスを中央揃えで配置する。

```
dep_centers = [staging_pos[dep] + box_height(dep) / 2  for dep in model.depends_on]
ecommerce_pos[model] = mean(dep_centers) - box_height(model) / 2
```

配置後、ボックス同士の重なりを下から上へのパスで解消する (前ボックスの上端 + v_gap を下限として押し上げ)。

### 矢印の描画

矢印はボックス描画より先に描くことでボックスの下に隠れる。矢先 (x2, y2) に向かう小さな正三角形 (size=6) を三角関数で計算して塗りつぶす。

---

## 8. テスト設計

### テストファイル構成

```
tests/
├── conftest.py          セッションスコープ fixtures
├── test_extractor.py    抽出ロジック単体テスト (11 件)
└── test_pdf_content.py  PDF 内容整合テスト (15 件)
```

### conftest.py fixtures

| fixture | scope | 内容 |
|---------|-------|------|
| `manifest` | session | `load_manifest()` の戻り値 |
| `catalog` | session | `load_catalog()` の戻り値 |
| `models` | session | `extract_models()` の戻り値 |
| `pdf_path` | session | テスト用一時ディレクトリに生成した PDF のパス |
| `pdf_text` | session | `pdfplumber.extract_text()` で全ページを結合したテキスト |
| `pdf_table_cells` | session | `pdfplumber.extract_tables()` で全テーブルセルを `" | "` で結合したテキスト |

`pdf_text` と `pdf_table_cells` を使い分ける理由: テーブルセル内で折り返しが起きると `extract_text()` が行をページ順で取得するため、セルの続きが他のセルと混在する。`extract_tables()` はセル単位で構造化して取得するため折り返しテキストも正確に得られる。説明文の検証には `pdf_table_cells` を使う。

### test_extractor.py の検証項目

| テスト | 検証内容 |
|--------|---------|
| `test_model_count` | 5 モデルが抽出される |
| `test_model_names` | 期待するモデル名 5 件が一致する |
| `test_layer_assignment` | 各モデルのレイヤーが正しい |
| `test_descriptions_populated` | 全モデルに説明文がある |
| `test_column_count` | 各モデルのカラム数が schema.yml と一致する |
| `test_column_descriptions` | 全カラムに説明文がある |
| `test_column_data_types_from_catalog` | catalog.json 由来のデータ型が設定されている |
| `test_tests_attached_to_columns` | `unique` / `not_null` テストが正しいカラムに付いている |
| `test_depends_on` | 依存モデル名が正しい |
| `test_materialization` | table / view が正しく設定されている |
| `test_schema_and_database` | schema / database が空でない |

### test_pdf_content.py の検証項目

| クラス | テスト | 検証内容 |
|--------|--------|---------|
| `TestTableInfo` | `test_all_model_names_in_pdf` | 全モデル名が PDF テキストに含まれる |
| | `test_model_descriptions_in_pdf` | 全モデル説明文が PDF テキストに含まれる |
| | `test_layer_labels_in_pdf` | "Staging" / "Ecommerce" の文字列が存在する |
| | `test_materialization_in_pdf` | "table" / "view" が存在する |
| | `test_schema_in_pdf` | スキーマ名が存在する |
| `TestColumnInfo` | `test_all_column_names_in_pdf` | 全カラム名が PDF テキストに含まれる |
| | `test_column_descriptions_in_pdf` | 全カラム説明文がテーブルセルに含まれる |
| | `test_data_types_in_pdf` | 主要なデータ型文字列が存在する |
| | `test_test_names_in_pdf` | テスト名が PDF テキストに含まれる |
| `TestLineage` | `test_er_section_title_in_pdf` | "ER" の文字列が存在する |
| | `test_dependency_models_present` | 依存モデルが PDF に掲載されている |
| `TestMetadataConsistency` | `test_column_count_consistency` | カラム数が期待値と一致 |
| | `test_no_empty_data_types_for_catalog_models` | catalog 存在モデルのカラムにデータ型がある |
| | `test_pdf_page_count` | 4 ページ以上存在する |
| | `test_cover_contains_project_name` | 表紙にプロジェクト名がある |

---

## 9. 既知の制約と設計判断の記録

### CID フォントの使用

日本語対応に `HeiseiKakuGo-W5` (reportlab 内蔵 Adobe CID フォント) を使用している。CID フォントはシステムにフォントファイルがなくても使えるが、PDF 内部でグリフ ID の順序が Unicode コードポイント順と異なる場合がある。このため `pdfplumber` でテキスト抽出すると複数セルにまたがる長いテキスト (例: `TIMESTAMP WITH TIME ZONE`) が前後のセルと混在して抽出されることがある。テストでは説明文の検証を `extract_tables()` ベースの `pdf_table_cells` fixture で行うことでこの問題を回避している。

### ER 図の対象レイヤー

現在の ER 図は staging → それ以外 の 2 カラム構成を前提にしている。3 レイヤー以上 (staging / intermediate / mart など) の場合は `er_diagram.py` のレイアウトロジックを拡張する必要がある。

### catalog.json が空の場合

`catalog.json` の `nodes` が空 (dbt が DB に接続できなかった等) の場合、全カラムの `data_type` が空文字列になる。PDF 生成自体は成功するが、カラムテーブルのデータ型列に `-` が表示される。

### depends_on のスコープ

`depends_on.nodes` には `source.` や `seed.` ノードが含まれることがある。本ツールは `model.` プレフィックスのもののみを依存関係として扱い、source/seed はリネージ図に表示しない。
