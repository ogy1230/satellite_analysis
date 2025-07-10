import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from rasterio.warp import reproject, Resampling

def process_sar_tiff(tiff_path):
    """
    GeoTIFFファイルを読み込み、線形の後方散乱係数をdBに変換してデータ配列を返します。
    """
    with rasterio.open(tiff_path) as src:
        # 最初のバンドを読み込む
        vv_linear = src.read(1).astype(float)

        # Sentinel-1データには対数変換に無効なゼロ値が含まれている可能性があるため、
        # 変換前にゼロや負の値をNaNに置き換えます。
        vv_linear[vv_linear <= 0] = np.nan

        # dBに変換
        vv_db = 10 * np.log10(vv_linear)

        return vv_db, src.meta

def load_and_resample_dem(dem_path, ref_meta):
    """
    DEMを読み込み、SAR画像（ref_meta）に合わせてリサンプリング
    """
    with rasterio.open(dem_path) as dem_src:
        dem = dem_src.read(1).astype(float)
        dem_resampled = np.empty((ref_meta['height'], ref_meta['width']), dtype=float)
        reproject(
            source=dem,
            destination=dem_resampled,
            src_transform=dem_src.transform,
            src_crs=dem_src.crs,
            dst_transform=ref_meta['transform'],
            dst_crs=ref_meta['crs'],
            resampling=Resampling.bilinear
        )
    return dem_resampled

def apply_terrain_correction(vv_db, dem, metadata):
    """
    SARデータに標高に基づいた地形補正を適用
    """
    # データの統計値を計算
    valid_data = vv_db[~np.isnan(vv_db)]
    if len(valid_data) > 0:
        data_min = np.min(valid_data)
        data_max = np.max(valid_data)
        data_mean = np.mean(valid_data)
        
        print(f"データ統計: min={data_min:.2f}dB, max={data_max:.2f}dB, mean={data_mean:.2f}dB")
    
    # 標高帯ごとの補正値を定義（より細かい調整）
    elevation_correction = {
        '0-200m': 0,      # 低地帯: 0dB補正
        '200-400m': 1,    # 軽い丘陵: +1dB補正
        '400-600m': 2,    # 中程度の丘陵: +2dB補正
        '600-800m': 3,    # 山麓: +3dB補正
        '800-1000m': 4,   # 山地: +4dB補正
        '1000-1500m': 5,  # 高地: +5dB補正
        '1500-2000m': 6   # 高山: +6dB補正
    }
    
    # 標高帯を定義
    elevation_bins = [0, 200, 400, 600, 800, 1000, 1500, 2000]
    
    # 補正マップを作成
    correction_map = np.zeros_like(dem)
    
    # 標高帯ごとに補正値を適用
    for i in range(len(elevation_bins)-1):
        low = elevation_bins[i]
        high = elevation_bins[i+1]
        elev_range = f"{low}-{high}m"
        
        # 標高帯のマスク
        mask = np.logical_and(dem >= low, dem < high)
        
        # 補正値を適用
        correction_map[mask] = elevation_correction[elev_range]
        
        # 補正値の適用範囲を確認
        if np.any(mask):
            print(f"標高帯 {elev_range}: {np.sum(mask)} ピクセル")
    
    # 補正を適用
    corrected_vv = vv_db + correction_map
    
    # NaN値の処理
    corrected_vv = np.where(np.isnan(corrected_vv), vv_db, corrected_vv)
    
    # データの範囲を調整
    corrected_vv = np.clip(corrected_vv, -20, 0)
    
    # 補正後のデータの統計を表示
    valid_corrected = corrected_vv[~np.isnan(corrected_vv)]
    if len(valid_corrected) > 0:
        corrected_min = np.min(valid_corrected)
        corrected_max = np.max(valid_corrected)
        corrected_mean = np.mean(valid_corrected)
        print(f"補正後統計: min={corrected_min:.2f}dB, max={corrected_max:.2f}dB, mean={corrected_mean:.2f}dB")
    
    return corrected_vv
    
    # 標高帯ごとに補正値を適用
    for i in range(len(elevation_bins)-1):
        low = elevation_bins[i]
        high = elevation_bins[i+1]
        elev_range = f"{low}-{high}m"
        
        # 標高帯のマスク
        mask = np.logical_and(dem >= low, dem < high)
        
        # 補正値を適用
        correction_map[mask] = elevation_correction[elev_range]
    
    # 補正を適用
    corrected_vv = vv_db + correction_map
    
    # NaN値の処理
    corrected_vv = np.where(np.isnan(corrected_vv), vv_db, corrected_vv)
    
    # データの範囲を調整
    corrected_vv = np.clip(corrected_vv, -20, 0)
    
    return corrected_vv

def estimate_moisture_by_elevation(vv_db, dem, metadata):
    """
    標高帯ごとに水分量を推定
    """
    # 標高帯を定義
    elevation_bins = [0, 500, 1000, 1500, 2000]
    
    # 水分量推定用の閾値（標高帯ごとに異なる）
    moisture_thresholds = {
        '0-500m': (-15, -5),    # 低地帯
        '500-1000m': (-20, -10),  # 山麓
        '1000-1500m': (-25, -15), # 山地
        '1500-2000m': (-30, -20)  # 高地
    }
    
    # 結果を格納するマップ
    moisture_map = np.zeros_like(vv_db)
    moisture_levels = np.zeros_like(vv_db)
    
    for i in range(len(elevation_bins)-1):
        low = elevation_bins[i]
        high = elevation_bins[i+1]
        elev_range = f"{low}-{high}m"
        
        # 標高帯のマスク
        mask = np.logical_and(dem >= low, dem < high)
        
        # 水分量推定
        moisture_map[mask] = np.where(
            vv_db[mask] < moisture_thresholds[elev_range][0],
            1,  # 高水分
            np.where(
                vv_db[mask] < moisture_thresholds[elev_range][1],
                0.5,  # 中水分
                0    # 低水分
            )
        )
        
        # 水分レベルの追加情報を保存
        moisture_levels[mask] = vv_db[mask]
    
    return moisture_map, moisture_levels

def sado_island_clip(data, metadata):
    """
    佐渡島の範囲（bbox）でデータをクリッピング
    """
    # 佐渡島の範囲（bbox）
    sado_bbox = {
        'min_lon': 138.17,  # 経度最小
        'min_lat': 37.81,   # 緯度最小
        'max_lon': 138.61,  # 経度最大
        'max_lat': 38.34    # 緯度最大
    }
    
    # メタデータから変換行列を取得
    transform = metadata['transform']
    
    # 経度緯度をピクセル座標に変換
    def lonlat_to_pixel(lon, lat):
        # rasterioのwindow_from_coordinatesを使用
        window = rasterio.windows.from_bounds(
            left=lon,
            bottom=lat,
            right=lon,
            top=lat,
            transform=transform
        )
        return int(window.col_off), int(window.row_off)
    
    # ピクセル座標を計算
    left, top = lonlat_to_pixel(sado_bbox['min_lon'], sado_bbox['max_lat'])
    right, bottom = lonlat_to_pixel(sado_bbox['max_lon'], sado_bbox['min_lat'])
    
    # クリッピング範囲を計算
    width = right - left
    height = bottom - top
    
    # データをクリッピング
    clipped_data = data[top:bottom, left:right]
    
    # クリップ後のメタデータを更新
    clipped_meta = metadata.copy()
    clipped_meta.update({
        'width': width,
        'height': height,
        'transform': rasterio.Affine(
            transform[0], transform[1], 
            left * transform[0] + transform[2],
            transform[3], transform[4], 
            top * transform[4] + transform[5]
        )
    })
    
    return clipped_data, clipped_meta

def visualize_moisture_with_elevation(vv_db, dem, metadata, output_path):
    """
    地形補正後の水分量を標高データとともに可視化
    """
    plt.figure(figsize=(18, 6))
    
    # 佐渡島範囲でのクリッピング
    vv_db, metadata = sado_island_clip(vv_db, metadata)
    dem, _ = sado_island_clip(dem, metadata)
    
    # 地形補正を適用
    corrected_vv = apply_terrain_correction(vv_db, dem, metadata)
    
    # 水分量推定
    moisture_map, moisture_levels = estimate_moisture_by_elevation(corrected_vv, dem, metadata)
    
    # サブプロット1: 地形補正後のSARデータ
    plt.subplot(1, 4, 1)
    plt.imshow(corrected_vv, cmap='viridis_r', vmin=-30, vmax=0)
    plt.title('Terrain-Corrected SAR (dB)')
    plt.colorbar(label='Backscatter (dB)')
    
    # サブプロット2: 水分量マップ
    plt.subplot(1, 4, 2)
    plt.imshow(moisture_map, cmap='Blues', vmin=0, vmax=1)
    plt.title('Estimated Moisture Content')
    cbar = plt.colorbar(label='Moisture Level')
    cbar.set_ticks([0, 0.5, 1])
    cbar.set_ticklabels(['Low', 'Medium', 'High'])
    
    # サブプロット3: 水分レベルの分布
    plt.subplot(1, 4, 3)
    plt.imshow(moisture_levels, cmap='viridis_r', vmin=-30, vmax=0)
    plt.title('Moisture Levels (dB)')
    plt.colorbar(label='Backscatter (dB)')
    
    # サブプロット4: DEMデータ
    plt.subplot(1, 4, 4)
    plt.imshow(dem, cmap='terrain', vmin=0, vmax=2000)
    plt.title('Elevation (m)')
    plt.colorbar(label='Elevation (m)')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def analyze_sar_by_elevation(vv_db, dem, output_path):
    """
    標高帯ごとにSAR値の統計を計算
    """
    # 標高帯を定義（例：0-500m, 500-1000m, 1000-1500m, 1500-2000m）
    elevation_bins = [0, 500, 1000, 1500, 2000]
    
    # 統計値を格納するリスト
    stats = []
    for i in range(len(elevation_bins)-1):
        low = elevation_bins[i]
        high = elevation_bins[i+1]
        mask = np.logical_and(dem >= low, dem < high)
        valid_pixels = vv_db[mask]
        
        if len(valid_pixels) > 0:
            stats.append({
                'elevation_range': f"{low}-{high}m",
                'mean': np.nanmean(valid_pixels),
                'std': np.nanstd(valid_pixels),
                'count': len(valid_pixels)
            })
    
    # 統計結果をCSVに保存
    df = pd.DataFrame(stats)
    df.to_csv(output_path, index=False)
    return df

def visualize_raw_sar(db_data, metadata, output_path):
    """
    SARデータの原始データを可視化
    """
    plt.figure(figsize=(12, 8))
    
    # カラーマップの設定
    cmap = plt.cm.terrain  # 地形を表現するためのカラーマップに変更
    cmap.set_bad(color='white')  # NaN値を白で表示
    
    # データの表示範囲を設定
    # データの実際の範囲に基づいて自動的に調整
    vmin = np.nanpercentile(db_data, 1)  # 1パーセンタイル
    vmax = np.nanpercentile(db_data, 99)  # 99パーセンタイル
    
    # データを表示
    im = plt.imshow(db_data, cmap=cmap, vmin=vmin, vmax=vmax)
    
    # タイトルと軸ラベルの設定
    plt.title('Raw SAR Data')
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # カラーバーを追加
    cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    cbar.set_label('Backscatter (dB)')

    # グリッドを表示
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"原始SARデータを保存しました: {output_path}")

def visualize_soil_moisture(db_data, metadata, output_path):
    """
    土壌水分量を可視化
    """
    plt.figure(figsize=(12, 8))
    
    # カラーマップの設定
    cmap = plt.cm.viridis_r
    cmap.set_bad(color='white')  # NaN値を白で表示
    
    # データの表示範囲をクリッピング後のデータに基づいて設定
    # データの実際の範囲を確認
    valid_data = db_data[~np.isnan(db_data)]
    if len(valid_data) > 0:
        data_min = np.min(valid_data)
        data_max = np.max(valid_data)
        
        # データの範囲を適切に設定
        vmin = max(data_min, -20)  # 最小値は-20dBを下限とする
        vmax = min(data_max, 0)     # 最大値は0dBを上限とする
    else:
        # データが存在しない場合のデフォルト値
        vmin = -20
        vmax = 0
    
    # データを表示
    im = plt.imshow(db_data, cmap=cmap, vmin=vmin, vmax=vmax)
    
    # タイトルと軸ラベルの設定
    plt.title('Soil Moisture from SAR')
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # カラーバーを追加
    cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    cbar.set_label('Backscatter (dB)')

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"可視化結果を保存しました: {output_path}")

def main():
    """
    sar_dataディレクトリ内のすべてのTIFFファイルを処理するメイン関数。
    """
    input_dir = Path('sar_data')
    output_dir = Path('analysis_results')
    output_dir.mkdir(exist_ok=True)

    dem_path = Path('dem/dem.tif')
    dem_loaded = False
    dem = None

    if not input_dir.exists():
        print(f"エラー: 入力ディレクトリ '{input_dir}' が見つかりません。")
        print("'get_sentinel_1_sardata.py' を先に実行してデータをダウンロードしてください。")
        return

    tiff_files = list(input_dir.rglob('*.tiff'))
    if not tiff_files:
        print(f"'{input_dir}' にTIFFファイルが見つかりません。")
        return

    if not dem_path.exists():
        print(f"エラー: DEMファイル '{dem_path}' が見つかりません。dem_download.py を使ってダウンロードしてください。")
        return

    for tiff_path in tiff_files:
        tag = str(tiff_path).split('/')[1]
        vv_db, meta = process_sar_tiff(tiff_path)
        if not dem_loaded:
            dem = load_and_resample_dem(str(dem_path), meta)
            dem_loaded = True
        
        # 水分量と標高の重ね合わせ可視化
        moisture_output = output_dir / (tag + '_moisture.png')
        visualize_moisture_with_elevation(vv_db, dem, meta, moisture_output)
        print(f"水分量と標高の重ね合わせ可視化を保存しました: {moisture_output}")
        
        # 通常のSAR可視化も従来通り実行

    for tiff_file in tiff_files:
        print(str(tiff_file).split('/')[1])
        print(f"{tiff_file.name} を処理中...")
        try:
            db_data, metadata = process_sar_tiff(tiff_file)
            db_data, metadata = sado_island_clip(db_data, metadata)

            # 原始SARデータの保存
            raw_output = output_dir / f"{str(tiff_file).split('/')[1]}_raw.png"
            visualize_raw_sar(db_data, metadata, raw_output)

            # 出力ファイル名を作成
            output_filename = output_dir / f"{str(tiff_file).split('/')[1]}_analysis.png"

            visualize_soil_moisture(db_data, metadata, output_filename)
        except Exception as e:
            print(f"{tiff_file.name} の処理に失敗しました。エラー: {e}")

if __name__ == '__main__':
    main()
