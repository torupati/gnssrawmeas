# GNSS Database Module

This document describes the database module for storing and loading GNSS observation data, satellite positions, and single point positioning (SPP) solutions in an SQLite database.

## Overview

The `app.gnss.database` module provides functionality to efficiently store the following data in an SQLite database:

1. **Observations (EpochObservations)**: Raw GNSS observation data for each epoch
2. **Satellite Positions (SatellitePosition)**: Computed satellite ECEF coordinates
3. **SPP Solutions (SppSolution)**: Single Point Positioning results

## Database Schema

The database uses a normalized schema to minimize redundancy while maintaining efficient query performance.

### Table Structure

#### 1. `epochs` Table
Stores observation epochs (timestamps).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| datetime | DATETIME | Observation time (UTC), unique |

#### 2. `satellites` Table
Stores observation data for each satellite at a specific epoch.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| epoch_id | INTEGER | Foreign key to epochs |
| satellite_id | STRING | Satellite ID (e.g., "G01", "E05") |
| prn | INTEGER | PRN number |
| system | STRING | Satellite system ("GPS", "QZSS", "Galileo", "GLONASS") |

#### 3. `signals` Table
Stores signal observations for each satellite and frequency band.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| satellite_id | INTEGER | Foreign key to satellites |
| band | STRING | Frequency band (e.g., "L1", "L2", "E1") |
| pseudorange | FLOAT | Pseudorange (meters) |
| carrier_phase | FLOAT | Carrier phase (cycles) |
| doppler | FLOAT | Doppler (Hz) |
| snr | FLOAT | Signal-to-noise ratio (dB-Hz) |

#### 4. `ambiguities` Table
Stores ambiguity observations for dual-frequency combinations.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| satellite_id | INTEGER | Foreign key to satellites |
| combination | STRING | Frequency combination (e.g., "L1_L2") |
| widelane | FLOAT | Widelane ambiguity (cycles) |
| ionofree | FLOAT | Ionosphere-free ambiguity (cycles) |
| geofree | FLOAT | Geometry-free ambiguity (cycles) |
| multipath | FLOAT | Multipath ionosphere-free indicator (meters) |

#### 5. `satellite_positions` Table
Stores computed satellite positions in ECEF coordinates.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| satellite_id | INTEGER | Foreign key to satellites |
| datetime | DATETIME | Observation time (UTC) |
| nano_second | INTEGER | Sub-second value in nanoseconds |
| x | FLOAT | ECEF X coordinate (meters) |
| y | FLOAT | ECEF Y coordinate (meters) |
| z | FLOAT | ECEF Z coordinate (meters) |
| clock_bias | FLOAT | Satellite clock bias (seconds) |

#### 6. `spp_solutions` Table
Stores single point positioning results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| epoch_id | INTEGER | Foreign key to epochs |
| x, y, z | FLOAT | ECEF coordinates (meters) |
| latitude | FLOAT | Latitude (degrees) |
| longitude | FLOAT | Longitude (degrees) |
| height | FLOAT | Ellipsoidal height (meters) |
| clock_bias_m | FLOAT | Receiver clock bias (meters) |
| num_satellites | INTEGER | Number of satellites used |
| residuals | TEXT | JSON array of residuals |

## Usage

### Basic Usage

```python
from pathlib import Path
from app.gnss.database import GnssDatabase
from app.gnss.satellite_signals import parse_rinex_observation_file

# Initialize database
db = GnssDatabase("gnss_data.db")

# Parse RINEX file
signal_code_map = {...}  # Load signal code map
epochs = parse_rinex_observation_file("observation.rnx", signal_code_map)

# Save to database
db.save_epoch_observations(epochs)

# Load from database
loaded_epochs = db.load_epoch_observations()

# Get statistics
stats = db.get_statistics()
print(f"Number of epochs: {stats['num_epochs']}")
print(f"Number of satellites: {stats['num_satellites']}")
```

### Loading with Time Filter

```python
from datetime import datetime, timezone

# Specify start and end times
start_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
end_dt = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

# Load data for the specified period
epochs = db.load_epoch_observations(
    start_datetime=start_dt,
    end_datetime=end_dt
)
```

### Saving Satellite Positions

```python
from datetime import datetime, timezone

epoch_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

positions = {
    "G01": {
        "datetime": epoch_dt,
        "nano_second": 500000000,
        "x": 12345678.90,
        "y": 23456789.01,
        "z": 34567890.12,
        "clock_bias": 0.000123
    },
    "E05": {
        "datetime": epoch_dt,
        "nano_second": 500000000,
        "x": 98765432.10,
        "y": 87654321.09,
        "z": 76543210.98,
        "clock_bias": -0.000456
    }
}

db.save_satellite_positions(positions, epoch_dt)
```

### Saving SPP Solutions

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

### Clearing the Database

```python
# Delete all data
db.clear_database()
```

## Practical Examples

### Example 1: Converting a RINEX File to Database

```python
import json
from pathlib import Path
from app.gnss.database import GnssDatabase
from app.gnss.satellite_signals import parse_rinex_observation_file

# Load signal code map
with open("app/.signal_code_map.json", "r") as f:
    signal_code_map = json.load(f)

# Parse RINEX file
epochs = parse_rinex_observation_file("data/observation.rnx", signal_code_map)

# Save to database
db = GnssDatabase("output/gnss_data.db")
db.save_epoch_observations(epochs)

print(f"Saved {len(epochs)} epochs")
```

### Example 2: Loading and Processing Data from Database

```python
from app.gnss.database import GnssDatabase

# Open database
db = GnssDatabase("output/gnss_data.db")

# Load all epochs
epochs = db.load_epoch_observations()

# Process each epoch
for epoch in epochs:
    print(f"Time: {epoch.datetime}")
    print(f"  GPS satellites: {len(epoch.satellites_gps)}")
    print(f"  Galileo satellites: {len(epoch.satellites_galileo)}")

    # Process each satellite
    for sat_id, sat_obs in epoch.iter_satellites():
        if "L1" in sat_obs.signals:
            signal = sat_obs.signals["L1"]
            print(f"    {sat_id}: PR={signal.pseudorange:.3f} m, SNR={signal.snr:.1f} dB-Hz")
```

### Example 3: Saving SPP Computation Results

```python
from app.gnss.database import GnssDatabase
from app.spp import parse_rinex_navigation_file, single_point_positioning

# Load observations from database
db = GnssDatabase("gnss_data.db")
epochs = db.load_epoch_observations()

# Load navigation message
nav_data = parse_rinex_navigation_file("navigation.rnx")

# Compute SPP
solutions = single_point_positioning(epochs, nav_data)

# Save results to database
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
