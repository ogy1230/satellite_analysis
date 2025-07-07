import os
from pathlib import Path
import rasterio
from elevation import clip, clean

# 必要なパッケージ: elevation, rasterio
# pip install elevation rasterio

def download_dem(bbox, out_path):
    """
    bbox: (min_lon, min_lat, max_lon, max_lat)
    out_path: 保存先GeoTIFFファイルパス
    """
    # 一時ディレクトリ
    temp_dir = Path('temp_dem')
    temp_dir.mkdir(exist_ok=True)
    tif_path = temp_dir / 'dem_tmp.tif'
    
    # bboxは (min_lon, min_lat, max_lon, max_lat)
    print(f"Downloading SRTM DEM for bbox: {bbox}")
    clip(bounds=bbox, output=str(tif_path))
    # 必要なら座標系や解像度の調整
    with rasterio.open(tif_path) as src:
        profile = src.profile
        data = src.read(1)
        # 必要ならここでリサンプリングやCRS変換も可能
    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(data, 1)
    clean()  # 一時ファイル削除
    print(f"DEM saved to {out_path}")

if __name__ == '__main__':
    # 例: bbox = (min_lon, min_lat, max_lon, max_lat)
    bbox = (139.6, 35.5, 139.9, 35.8)  # 東京周辺の例
    bbox = (138.17, 38.34, 138.61, 37.81)
    out_path = 'dem/dem.tif'
    Path('dem').mkdir(exist_ok=True)
    download_dem(bbox, out_path)
