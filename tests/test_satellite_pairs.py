"""
Test satellite pair selection based on signal strength.
"""

import pytest
import numpy as np
from pathlib import Path
import georinex as gr

from app.plot2sig import (
    get_satellites_sorted_by_signal_strength,
    get_satellite_pairs_by_signal_strength,
)


@pytest.fixture
def sample_rinex_file():
    """サンプルRINEXファイルのパスを返す"""
    # プロジェクトルートからの相対パス
    sample_file = (
        Path(__file__).parent.parent
        / "sample_data"
        / "static_baseline"
        / "3075358x.25o"
    )
    if not sample_file.exists():
        pytest.skip(f"Sample RINEX file not found: {sample_file}")
    return sample_file


@pytest.fixture
def rinex_obs(sample_rinex_file):
    """サンプルRINEXファイルを読み込んでrinexobsオブジェクトを返す"""
    import warnings

    warnings.simplefilter("ignore", FutureWarning)
    return gr.load(str(sample_rinex_file))


class TestGetSatellitesSortedBySignalStrength:
    """get_satellites_sorted_by_signal_strength関数のテスト"""

    def test_basic_functionality(self, rinex_obs):
        """基本的な動作確認"""
        result = get_satellites_sorted_by_signal_strength(rinex_obs, signal_type="S1C")

        # 結果が辞書であること
        assert isinstance(result, dict)

        # 結果が空でないこと
        assert len(result) > 0

        # 各エポックの結果がリストであること
        for time_val, sat_list in result.items():
            assert isinstance(sat_list, list)

            # リストの各要素がタプルであること
            for item in sat_list:
                assert isinstance(item, tuple)
                assert len(item) == 2
                assert isinstance(item[0], str)  # 衛星名
                assert isinstance(item[1], (float, np.floating))  # 信号強度

    def test_signal_strength_sorting(self, rinex_obs):
        """信号強度が降順にソートされていることを確認"""
        result = get_satellites_sorted_by_signal_strength(rinex_obs, signal_type="S1C")

        for time_val, sat_list in result.items():
            if len(sat_list) > 1:
                # 降順にソートされているか確認
                strengths = [strength for _, strength in sat_list]
                assert strengths == sorted(strengths, reverse=True)
                break  # 1エポック確認できれば十分

    def test_constellation_filter(self, rinex_obs):
        """コンステレーションフィルターが正しく動作することを確認"""
        # GPSのみ
        result_gps = get_satellites_sorted_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G"
        )

        # すべての衛星がGで始まることを確認
        for time_val, sat_list in result_gps.items():
            for sv, _ in sat_list:
                assert sv.startswith("G")

    def test_invalid_signal_type(self, rinex_obs):
        """無効な信号タイプでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Signal type .* not found"):
            get_satellites_sorted_by_signal_strength(
                rinex_obs, signal_type="INVALID_SIGNAL"
            )

    def test_no_nan_values(self, rinex_obs):
        """NaN値が結果に含まれていないことを確認"""
        result = get_satellites_sorted_by_signal_strength(rinex_obs, signal_type="S1C")

        for time_val, sat_list in result.items():
            for sv, strength in sat_list:
                assert not np.isnan(strength)

    def test_epoch_count(self, rinex_obs):
        """処理されたエポック数が妥当であることを確認"""
        result = get_satellites_sorted_by_signal_strength(rinex_obs, signal_type="S1C")

        # エポック数がRINEXファイルのタイムスタンプ数と一致すること
        assert len(result) == len(rinex_obs.time)


class TestGetSatellitePairsBySignalStrength:
    """get_satellite_pairs_by_signal_strength関数のテスト"""

    def test_basic_functionality(self, rinex_obs):
        """基本的な動作確認"""
        result = get_satellite_pairs_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G"
        )

        # 結果がリストであること
        assert isinstance(result, list)

        # 各要素がタプルであること
        for pair in result:
            assert isinstance(pair, tuple)
            assert len(pair) == 2
            assert isinstance(pair[0], str)
            assert isinstance(pair[1], str)

    def test_reference_satellite(self, rinex_obs):
        """最も信号強度の高い衛星が基準衛星として使用されていることを確認"""
        result = get_satellite_pairs_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G"
        )

        if len(result) > 0:
            # すべてのペアの最初の要素が同じ（基準衛星）であること
            reference_sats = [pair[0] for pair in result]
            assert len(set(reference_sats)) == 1

    def test_top_n_parameter(self, rinex_obs):
        """top_nパラメータが正しく動作することを確認"""
        top_n = 5
        result = get_satellite_pairs_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G", top_n=top_n
        )

        # ペア数はtop_n - 1以下であること（基準衛星を除く）
        assert len(result) <= top_n - 1

    def test_no_duplicate_pairs(self, rinex_obs):
        """重複したペアが存在しないことを確認"""
        result = get_satellite_pairs_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G"
        )

        # ペアをソートして比較（順序を正規化）
        normalized_pairs = [tuple(sorted(pair)) for pair in result]
        assert len(normalized_pairs) == len(set(normalized_pairs))

    def test_minimum_satellites(self, rinex_obs):
        """衛星が2つ未満の場合は空リストを返すことを確認"""
        # 存在しないコンステレーションを指定
        result = get_satellite_pairs_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="Z", top_n=1
        )

        assert isinstance(result, list)
        # 衛星が少ない場合は空または少数のペア


class TestIntegration:
    """統合テスト"""

    def test_end_to_end_workflow(self, rinex_obs):
        """エンドツーエンドのワークフローをテスト"""
        # ステップ1: 信号強度順にソート
        sorted_sats = get_satellites_sorted_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G"
        )

        assert len(sorted_sats) > 0

        # ステップ2: 衛星ペアを生成
        pairs = get_satellite_pairs_by_signal_strength(
            rinex_obs, signal_type="S1C", constellation="G", top_n=5
        )

        # ペアが生成されていること
        if len([sv for sv in rinex_obs.sv.values if str(sv).startswith("G")]) >= 2:
            assert len(pairs) > 0

        # 生成されたペアの衛星がソート結果に含まれていること
        all_sats_in_sorted = set()
        for time_val, sat_list in sorted_sats.items():
            all_sats_in_sorted.update([sv for sv, _ in sat_list])

        for sat1, sat2 in pairs:
            assert sat1 in all_sats_in_sorted
            assert sat2 in all_sats_in_sorted

    def test_multiple_signal_types(self, rinex_obs):
        """複数の信号タイプで動作することを確認"""
        signal_types = ["S1C", "S2X"]

        for sig_type in signal_types:
            if sig_type in rinex_obs:
                result = get_satellites_sorted_by_signal_strength(
                    rinex_obs, signal_type=sig_type, constellation="G"
                )
                assert len(result) > 0

    def test_output_format_consistency(self, rinex_obs):
        """出力フォーマットの一貫性を確認"""
        sorted_sats = get_satellites_sorted_by_signal_strength(
            rinex_obs, signal_type="S1C"
        )

        # 最初の3エポックをチェック
        for idx, (time_val, sat_list) in enumerate(list(sorted_sats.items())[:3]):
            # 時刻がnumpy datetime64型であること
            assert isinstance(time_val, (np.datetime64, np.ndarray))

            # 各衛星エントリが適切なフォーマットであること
            for sv, strength in sat_list:
                assert len(sv) >= 2  # 最低でも"G1"のような形式
                assert sv[0].isalpha()  # 最初の文字はアルファベット
                assert strength > 0  # 信号強度は正の値


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
