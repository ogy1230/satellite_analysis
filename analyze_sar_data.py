import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
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

def visualize_soil_moisture(data, metadata, output_path):
    """
    地表水分量データを可視化し、PNGファイルとして保存します。
    後方散乱(dB)が高いほど、地表の水分量が多いと仮定します。
    """
    plt.figure(figsize=(10, 10))
    # cmapを'viridis_r'にすることで、値が高いほど色が濃くなります（湿潤を表現）。
    im = plt.imshow(data, cmap='viridis_r') 
    plt.title(f"Surface Moisture Analysis (VV Backscatter - dB)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # カラーバーを追加
    cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    cbar.set_label('Backscatter (dB) - Higher is wetter')

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
        vv_db, meta = process_sar_tiff(tiff_path)
        if not dem_loaded:
            dem = load_and_resample_dem(str(dem_path), meta)
            dem_loaded = True
        # ここでvv_dbとdemを使った地形補正や解析が可能
        # 例: 標高情報を可視化とともに保存
        dem_output = output_dir / (Path(tiff_path).stem + '_dem.png')
        plt.figure(figsize=(10, 10))
        plt.imshow(dem, cmap='terrain')
        plt.title('DEM (標高)')
        plt.colorbar(label='標高 (m)')
        plt.savefig(dem_output, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"DEM可視化を保存しました: {dem_output}")
        # 通常のSAR可視化も従来通り実行

    for tiff_file in tiff_files:
        print(str(tiff_file).split('/')[1])
        print(f"{tiff_file.name} を処理中...")
        try:
            db_data, metadata = process_sar_tiff(tiff_file)

            # 出力ファイル名を作成
            output_filename = output_dir / f"{str(tiff_file).split('/')[1]}_analysis.png"

            visualize_soil_moisture(db_data, metadata, output_filename)
        except Exception as e:
            print(f"{tiff_file.name} の処理に失敗しました。エラー: {e}")

if __name__ == '__main__':
    main()
