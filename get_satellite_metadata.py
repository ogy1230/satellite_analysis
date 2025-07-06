import os
from datetime import datetime, timedelta
import json
from sentinelhub import (
    SHConfig,
    SentinelHubCatalog,
    DataCollection,
    BBox,
    CRS,
    SentinelHubRequest,
    MimeType,
    bbox_to_dimensions
)
from PIL import Image
import numpy as np
import os
from datetime import datetime, timedelta
import json
from pathlib import Path
import configparser
from sentinelhub import SentinelHubSession
import time
from pathlib import Path
import configparser
import io

def get_satellite_image(sh_config, bbox, metadata, output_dir):
    """
    Sentinel-2の衛星画像を取得して保存
    """
    # プラットフォームに応じた評価スクリプトの定義
    platform = metadata['platform'].lower()
    
    if platform == 'sentinel-2b':
        # Sentinel-2B用の評価スクリプト
        evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "UINT8"
                }
            };
        }

        function evaluatePixel(sample) {
            // データの範囲を確認
            const B02 = sample.B02;
            const B03 = sample.B03;
            const B04 = sample.B04;
            
            // データの正規化
            const maxVal = 10000; // Sentinel-2のDN値の最大値
            
            // データの範囲を0-255に正規化
            const B02_norm = Math.min(255, Math.max(0, Math.round(B02 / maxVal * 255)));
            const B03_norm = Math.min(255, Math.max(0, Math.round(B03 / maxVal * 255)));
            const B04_norm = Math.min(255, Math.max(0, Math.round(B04 / maxVal * 255)));
            
            // データの範囲を拡張（コントラスト調整）
            const stretch = (value) => {
                // 0-255の範囲を0-1に正規化
                const norm = value / 255;
                // より強いコントラスト調整
                return Math.round(255 * Math.pow(norm, 1/2.5));
            };
            
            // 明るさ調整
            const B02_final = Math.min(255, Math.max(0, stretch(B02_norm) * 1.2));
            const B03_final = Math.min(255, Math.max(0, stretch(B03_norm) * 1.2));
            const B04_final = Math.min(255, Math.max(0, stretch(B04_norm) * 1.2));
            
            return [B04_final, B03_final, B02_final];
        }
        """
    else:
        # Sentinel-2A/C用の評価スクリプト
        evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "UINT8"
                }
            };
        }

        function evaluatePixel(sample) {
            // データの範囲を確認
            const B02 = sample.B02;
            const B03 = sample.B03;
            const B04 = sample.B04;
            
            // データの正規化
            const maxVal = 10000; // Sentinel-2のDN値の最大値
            
            // データの範囲を0-255に正規化
            const B02_norm = Math.min(255, Math.max(0, Math.round(B02 / maxVal * 255)));
            const B03_norm = Math.min(255, Math.max(0, Math.round(B03 / maxVal * 255)));
            const B04_norm = Math.min(255, Math.max(0, Math.round(B04 / maxVal * 255)));
            
            // データの範囲を拡張（コントラスト調整）
            const stretch = (value) => {
                // 0-255の範囲を0-1に正規化
                const norm = value / 255;
                // より穏やかなコントラスト調整
                return Math.round(255 * Math.pow(norm, 1/2.0));
            };
            
            // 明るさ調整
            const B02_final = Math.min(255, Math.max(0, stretch(B02_norm) * 1.1));
            const B03_final = Math.min(255, Math.max(0, stretch(B03_norm) * 1.1));
            const B04_final = Math.min(255, Math.max(0, stretch(B04_norm) * 1.1));
            
            return [B04_final, B03_final, B02_final];
        }
        """

    # 画像の保存ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    # メタデータから時間範囲を取得
    date_str = metadata['datetime'][:10]  # YYYY-MM-DD形式
    
    # 画像のファイル名を生成
    img_filename = f"satellite_{date_str}.png"
    img_path = os.path.join(output_dir, img_filename)
    
    # 画像データの取得
    print(f"\n{date_str}の画像を取得中...")
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(metadata['datetime'], metadata['datetime']),
                mosaicking_order='leastCC'
            )
        ],
        responses=[
            SentinelHubRequest.output_response('default', MimeType.TIFF)
        ],
        bbox=bbox,
        size=bbox_to_dimensions(bbox, resolution=10),
        config=sh_config
    )
    
    # 画像データの取得
    data = request.get_data()
    
    if not data:
        print(f"{metadata['datetime']}の画像を取得できませんでした")
        return

    # 画像を保存
    date = metadata['datetime'][:10]
    img_path = os.path.join(output_dir, f'satellite_{date}.png')
    
    # 画像の明るさチェック
    img_array = np.array(data[0])
    
    # 各ピクセルの明るさを計算
    brightness = np.mean(img_array, axis=2)
    dark_ratio = np.sum(brightness < 50) / brightness.size  # 暗いピクセルの割合
    white_ratio = np.sum(brightness >= 250) / brightness.size  # 白いピクセルの割合
    
    if dark_ratio < 0.9 and white_ratio < 0.9:  # 90%以上が暗いまたはほぼ白い場合は保存しない
        Image.fromarray(img_array).save(img_path)
        print(f"{date}の画像を取得しました")
    else:
        if dark_ratio >= 0.9:
            print(f"{date}の画像は90%以上が暗いため、保存をスキップしました")
        else:
            print(f"{date}の画像は90%以上が白いため、保存をスキップしました")

    return img_path if os.path.exists(img_path) else None

def download_satellite_images(sh_config, metadata_list, bbox, output_dir):
    """
    メタデータリストから衛星画像を一括でダウンロード
    """
    print("\n衛星画像のダウンロードを開始します...")
    total = len(metadata_list)
    
    for i, metadata in enumerate(metadata_list, 1):
        print(f"\n[{i}/{total}] {metadata['datetime']} の画像を処理中...")
        get_satellite_image(sh_config, bbox, metadata, output_dir)
        time.sleep(1)  # APIの負荷を考慮して1秒待機

    print("\n画像のダウンロードが完了しました")


def get_satellite_metadata(sh_config, bbox, time_interval):
    """
    Sentinel-2の衛星データのメタデータを取得する
    """
    catalog = SentinelHubCatalog(config=sh_config)
    
    search_iterator = catalog.search(
        DataCollection.SENTINEL2_L2A,
        bbox=bbox,
        time=time_interval,
        fields={
            'include': ['properties.datetime', 'properties.platform', 'properties.eo:cloud_cover']
        }
    )
    
    metadata_list = []
    for item in search_iterator:
        cloud_cover = item['properties'].get('eo:cloud_cover', None)
        if cloud_cover is not None:
            cloud_cover = float(cloud_cover)
        
        metadata = {
            'datetime': item['properties']['datetime'],
            'cloud_cover': cloud_cover,
            'tile_id': item['id'],  # idフィールドからタイルIDを取得
            'platform': item['properties']['platform'],
            'bbox': item['bbox'],  # APIレスポンスから直接座標を取得
            'resolution': 10  # デフォルトの解像度
        }
        metadata_list.append(metadata)
    
    return metadata_list

def save_metadata(metadata_list, output_dir):
    """
    メタデータをJSONファイルとして保存
    """
    os.makedirs(output_dir, exist_ok=True)
    metadata_file = os.path.join(output_dir, 'satellite_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata_list, f, indent=2)
    print(f"メタデータを {metadata_file} に保存しました")

def main():
    # 設定ファイルの読み込み
    config_path = Path(__file__).parent / 'config.ini'
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path)
    
    # Sentinel Hubの設定
    sh_config = SHConfig()
    sh_config.sh_base_url = 'https://services.sentinel-hub.com'
    sh_config.sh_client_id = config.get('sentinelhub', 'client_id')
    sh_config.sh_client_secret = config.get('sentinelhub', 'client_secret')
    
    # パラメータ設定
    resolution = 10  # 10mの解像度
    latitude = 38.0410  # 緯度（例：東京駅）
    longitude = 138.4147  # 経度（例：東京駅）
    bbox = BBox(bbox=[longitude - 0.01, latitude - 0.01, longitude + 0.01, latitude + 0.01], crs=CRS.WGS84)
    
    # 時間範囲設定
    today = datetime.now()
    date = today.strftime("%Y%m%d")
    one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=365)).strftime("%Y%m%d")
    time_interval = (one_month_ago, date)
    
    # メタデータ取得
    metadata_list = get_satellite_metadata(sh_config, bbox, time_interval)
    
    # メタデータの保存
    save_metadata(metadata_list, '.')
    
    # メタデータの表示
    print("\n取得したメタデータの概要:")
    for i, meta in enumerate(metadata_list, 1):
        cloud_cover = meta['cloud_cover']
        cloud_cover_str = f"{cloud_cover:.1f}%" if cloud_cover is not None else "情報なし"
        
        print(f"\n画像 {i}:")
        print(f"日時: {meta['datetime']}")
        print(f"雲量: {cloud_cover_str}")
        print(f"タイルID: {meta['tile_id']}")
        print(f"プラットフォーム: {meta['platform']}")
        
        # 雲量が高すぎる画像を表示
        if cloud_cover is not None and cloud_cover > 80:
            print("警告: 雲量が非常に高い可能性があります")

    # 画像データのダウンロード
    images_dir = 'satellite_images'
    download_satellite_images(sh_config, metadata_list, bbox, images_dir)

if __name__ == '__main__':
    main()
