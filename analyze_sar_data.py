import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

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
    print(input_dir)
    output_dir = Path('analysis_results')
    output_dir.mkdir(exist_ok=True)

    if not input_dir.exists():
        print(f"エラー: 入力ディレクトリ '{input_dir}' が見つかりません。")
        print("'get_sentinel_1_sardata.py' を先に実行してデータをダウンロードしてください。")
        return

    tiff_files = list(input_dir.rglob('*.tiff'))
    print(list(input_dir.rglob('*')))
    if not tiff_files:
        print(f"'{input_dir}' にTIFFファイルが見つかりません。")
        return

    for tiff_file in tiff_files:
        print(f"{tiff_file.name} を処理中...")
        try:
            db_data, metadata = process_sar_tiff(tiff_file)

            # 出力ファイル名を作成
            output_filename = output_dir / f"{tiff_file.stem}_analysis.png"

            visualize_soil_moisture(db_data, metadata, output_filename)
        except Exception as e:
            print(f"{tiff_file.name} の処理に失敗しました。エラー: {e}")

if __name__ == '__main__':
    main()
