# GNSS Database Module

このドキュメントは、GNSS観測データ、衛星位置、単独測位結果をSQLiteデータベースに保存・読み込みするためのデータベースモジュールについて説明します。

## 概要

`app.gnss.database` モジュールは、以下のデータを効率的にSQLiteデータベースに保存する機能を提供します：

1. **観測値 (EpochObservations)**: 各エポックのGNSS生観測データ
2. **衛星位置 (SatellitePosition)**: 計算された衛星のECEF座標
3. **単独測位結果 (SPP Solutions)**: Single Point Positioningの計算結果

## データベース構造

データベースは正規化されたスキーマを使用し、冗長性を最小限に抑えながら効率的なクエリパフォーマンスを維持します。

### テーブル構成

#### 1. `epochs` テーブル
観測エポック（タイムスタンプ）を格納します。

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 主キー（自動増分） |
| datetime | DATETIME | 観測時刻（UTC）、ユニーク |

#### 2. `satellites` テーブル
特定のエポックにおける各衛星の観測データを格納します。

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 主キー（自動増分） |
| epoch_id | INTEGER | エポックへの外部キー |
| satellite_id | STRING | 衛星ID（例: "G01", "E05"） |
| prn | INTEGER | PRN番号 |
| system | STRING | 衛星システム（"GPS", "QZSS", "Galileo", "GLONASS"） |

#### 3. `signals` テーブル
各衛星・周波数帯の信号観測値を格納します。

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 主キー（自動増分） |
| satellite_id | INTEGER | 衛星への外部キー |
| band | STRING | 周波数帯（例: "L1", "L2", "E1"） |
| pseudorange | FLOAT | 擬似距離（メートル） |
| carrier_phase | FLOAT | 搬送波位相（サイクル） |
| doppler | FLOAT | ドップラー（Hz） |
| snr | FLOAT | 信号対雑音比（dB-Hz） |

#### 4. `ambiguities` テーブル
二周波の組み合わせによるアンビギュイティ観測値を格納します。

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 主キー（自動増分） |
| satellite_id | INTEGER | 衛星への外部キー |
| combination | STRING | 周波数の組み合わせ（例: "L1_L2"） |
| widelane | FLOAT | ワイドレーンアンビギュイティ（サイクル） |
| ionofree | FLOAT | 電離層フリーアンビギュイティ（サイクル） |
| geofree | FLOAT | ジオメトリフリーアンビギュイティ（サイクル） |
| multipath | FLOAT | マルチパス（メートル） |

#### 5. `satellite_positions` テーブル
計算された衛星位置（ECEF座標）を格納します。

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 主キー（自動増分） |
| satellite_id | INTEGER | 衛星への外部キー |
| x | FLOAT | ECEF X座標（メートル） |
| y | FLOAT | ECEF Y座標（メートル） |
| z | FLOAT | ECEF Z座標（メートル） |
| clock_bias | FLOAT | 衛星時計バイアス（秒） |

#### 6. `spp_solutions` テーブル
単独測位の計算結果を格納します。

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 主キー（自動増分） |
| epoch_id | INTEGER | エポックへの外部キー |
| x, y, z | FLOAT | ECEF座標（メートル） |
| latitude | FLOAT | 緯度（度） |
| longitude | FLOAT | 経度（度） |
| height | FLOAT | 楕円体高（メートル） |
| clock_bias_m | FLOAT | 受信機時計バイアス（メートル） |
| num_satellites | INTEGER | 使用衛星数 |
| residuals | TEXT | 残差のJSON配列 |

## 使用方法

### 基本的な使い方

```python
from pathlib import Path
from app.gnss.database import GnssDatabase
from app.gnss.satellite_signals import parse_rinex_observation_file

# データベースの初期化
db = GnssDatabase("gnss_data.db")

# RINEXファイルの解析
signal_code_map = {...}  # 信号コードマップを読み込む
epochs = parse_rinex_observation_file("observation.rnx", signal_code_map)

# データベースに保存
db.save_epoch_observations(epochs)

# データベースから読み込み
loaded_epochs = db.load_epoch_observations()

# 統計情報の取得
stats = db.get_statistics()
print(f"エポック数: {stats['num_epochs']}")
print(f"衛星数: {stats['num_satellites']}")
```

### 時刻フィルタを使った読み込み

```python
from datetime import datetime, timezone

# 開始時刻と終了時刻を指定
start_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
end_dt = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

# 指定期間のデータを読み込み
epochs = db.load_epoch_observations(
    start_datetime=start_dt,
    end_datetime=end_dt
)
```

### 衛星位置の保存

```python
from datetime import datetime, timezone

epoch_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

positions = {
    "G01": {
        "x": 12345678.90,
        "y": 23456789.01,
        "z": 34567890.12,
        "clock_bias": 0.000123
    },
    "E05": {
        "x": 98765432.10,
        "y": 87654321.09,
        "z": 76543210.98,
        "clock_bias": -0.000456
    }
}

db.save_satellite_positions(positions, epoch_dt)
```

### SPP解の保存

```python
import numpy as np
from datetime import datetime, timezone

epoch_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

solution_data = {
    "position_ecef": np.array([-3962108.673, 3381309.574, 3668678.638]),
    "position_llh": np.array([35.7105, 139.8107, 45.3]),
    "clock_bias_m": 12345.678,
    "num_satellites": 8,
    "residuals": np.array([0.5, -0.3, 0.8, -0.2, 0.1, -0.6, 0.4, -0.1])
}

db.save_spp_solution(solution_data, epoch_dt)
```

### データベースのクリア

```python
# 全データを削除
db.clear_database()
```

## 実用例

### 例1: RINEXファイルからデータベースへの変換

```python
import json
from pathlib import Path
from app.gnss.database import GnssDatabase
from app.gnss.satellite_signals import parse_rinex_observation_file

# 信号コードマップの読み込み
with open("app/.signal_code_map.json", "r") as f:
    signal_code_map = json.load(f)

# RINEXファイルの解析
epochs = parse_rinex_observation_file("data/observation.rnx", signal_code_map)

# データベースに保存
db = GnssDatabase("output/gnss_data.db")
db.save_epoch_observations(epochs)

print(f"保存完了: {len(epochs)} エポック")
```

### 例2: データベースからの読み込みと処理

```python
from app.gnss.database import GnssDatabase

# データベースの読み込み
db = GnssDatabase("output/gnss_data.db")

# 全エポックを読み込み
epochs = db.load_epoch_observations()

# 各エポックの処理
for epoch in epochs:
    print(f"時刻: {epoch.datetime}")
    print(f"  GPS衛星数: {len(epoch.satellites_gps)}")
    print(f"  Galileo衛星数: {len(epoch.satellites_galileo)}")

    # 各衛星の処理
    for sat_id, sat_obs in epoch.iter_satellites():
        if "L1" in sat_obs.signals:
            signal = sat_obs.signals["L1"]
            print(f"    {sat_id}: PR={signal.pseudorange:.3f} m, SNR={signal.snr:.1f} dB-Hz")
```

### 例3: SPP計算結果の保存

```python
from app.gnss.database import GnssDatabase
from app.spp import parse_rinex_navigation_file, single_point_positioning

# データベースから観測値を読み込み
db = GnssDatabase("gnss_data.db")
epochs = db.load_epoch_observations()

# 航法メッセージの読み込み
nav_data = parse_rinex_navigation_file("navigation.rnx")

# SPP計算
solutions = single_point_positioning(epochs, nav_data)

# 結果をデータベースに保存
for sol in solutions:
    solution_data = {
        "position_ecef": sol.position_ecef,
        "position_llh": sol.position_llh,
        "clock_bias_m": sol.clock_bias_m,
        "num_satellites": sol.num_sats,
        "residuals": sol.residuals
    }
    db.save_spp_solution(solution_data, sol.datetime)
```

## 利点

### 1. パフォーマンス
- 正規化されたスキーマにより、データの冗長性を削減
- インデックスにより高速なクエリが可能
- 大量のエポックデータを効率的に管理

### 2. データ整合性
- 外部キー制約により、データの整合性を保証
- カスケード削除により、関連データの自動削除
- ユニーク制約により、重複データを防止

### 3. 柔軟性
- 時刻範囲でのフィルタリング機能
- 複数のGNSSシステム（GPS、Galileo、GLONASS、QZSS）に対応
- 観測値、衛星位置、測位解を個別に管理可能

### 4. 拡張性
- SQLAlchemy ORMを使用し、将来の拡張が容易
- PostgreSQL等の他のデータベースエンジンへの移行が可能

## テストの実行

```bash
# データベースモジュールのテストを実行
pytest tests/gnss/test_database.py -v

# カバレッジ付きで実行
pytest tests/gnss/test_database.py --cov=app.gnss.database
```

## 依存関係

- Python 3.10以上
- SQLAlchemy 2.0以上
- NumPy（SPP解の保存時に使用）

## 注意事項

1. **時刻の扱い**: すべての時刻は`datetime`オブジェクトとして扱われ、データベースに保存されます。タイムゾーン情報を含めることを推奨します。

2. **同一エポックの上書き**: 同じ時刻のエポックを再度保存すると、既存のデータは削除され、新しいデータで置き換えられます。

3. **トランザクション**: 各保存操作はトランザクション内で実行され、エラーが発生した場合はロールバックされます。

4. **大規模データ**: 大量のエポックを一度に保存する場合は、メモリ使用量に注意してください。必要に応じてバッチ処理を検討してください。

## トラブルシューティング

### データベースファイルが破損した場合

```python
# データベースファイルを削除して再作成
import os
os.remove("gnss_data.db")
db = GnssDatabase("gnss_data.db")
```

### パフォーマンスの最適化

大量のデータを扱う場合は、セッションを明示的に管理することでパフォーマンスを向上できます：

```python
session = db.Session()
try:
    for epoch in large_epoch_list:
        db._save_single_epoch(session, epoch)
    session.commit()
finally:
    session.close()
```

## 参考資料

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [RINEX Format Specification](https://files.igs.org/pub/data/format/rinex304.pdf)
