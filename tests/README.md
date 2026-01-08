# Test Guide

## テストの実行

### セットアップ

テストに必要な依存関係をインストール:

```bash
# uvを使用している場合
uv sync --dev

# または pip を使用
pip install -e ".[dev]"
```

### 全テストの実行

```bash
pytest
```

### 詳細な出力で実行

```bash
pytest -v
```

### 特定のテストファイルを実行

```bash
pytest tests/test_satellite_pairs.py
```

### 特定のテストクラスを実行

```bash
pytest tests/test_satellite_pairs.py::TestGetSatellitesSortedBySignalStrength
```

### 特定のテストメソッドを実行

```bash
pytest tests/test_satellite_pairs.py::TestGetSatellitesSortedBySignalStrength::test_basic_functionality
```

### カバレッジレポートと共に実行

```bash
pytest --cov=app --cov-report=html
```

カバレッジレポートは `htmlcov/index.html` で確認できます。

### テストの説明

#### `test_satellite_pairs.py`

衛星ペア選択機能のテスト:

- `TestGetSatellitesSortedBySignalStrength`: 信号強度順ソート機能のテスト
  - 基本動作確認
  - ソート順の検証
  - コンステレーションフィルター
  - 無効な入力のエラーハンドリング
  - NaN値の除外

- `TestGetSatellitePairsBySignalStrength`: 衛星ペア生成機能のテスト
  - 基本動作確認
  - 基準衛星の選択
  - top_nパラメータの動作
  - 重複ペアの検証

- `TestIntegration`: 統合テスト
  - エンドツーエンドのワークフロー
  - 複数信号タイプのサポート
  - 出力フォーマットの一貫性

## テストデータ

テストは `sample_data/static_baseline/3075358x.25o` のサンプルRINEXファイルを使用します。
このファイルが存在しない場合、テストはスキップされます。

## トラブルシューティング

### サンプルファイルが見つからない

```
SKIPPED [1] tests/test_satellite_pairs.py: Sample RINEX file not found
```

→ `sample_data/static_baseline/3075358x.25o` が存在することを確認してください。

### Import エラー

```
ModuleNotFoundError: No module named 'app'
```

→ プロジェクトルートから pytest を実行していることを確認してください。
