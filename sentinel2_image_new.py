import os
from datetime import datetime, timedelta
import numpy as np
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    SentinelHubDownloadClient,
    MimeType,
    CRS,
    BBox,
    DataCollection,
    bbox_to_dimensions
)
from PIL import Image
import matplotlib.pyplot as plt
import configparser
from pathlib import Path
import requests
import base64
import json


def save_image(data, output_path):
    print(f"データの最小値: {np.min(data)}")
    print(f"データの最大値: {np.max(data)}")
    # データを0-255の範囲に正規化
    normalized = np.clip(data[0], 0, 1)  # 0-1の範囲にクリッピング
    normalized = normalized * 255  # 0-255にスケーリング
    normalized = normalized.astype(np.uint8)  # uint8に変換
    
    # 明るさ調整
    adjusted = np.clip(normalized * 1.5, 0, 255).astype(np.uint8)
    
    # 画像を保存
    image = Image.fromarray(adjusted)
    image.save(output_path)


def download_sentinel2_image(lat, lon, date, output_dir='sentinel2_images'):
    # 設定ファイルの読み込み
    config_path = Path(__file__).parent / 'config.ini'
    config = configparser.ConfigParser(interpolation=None)
    
    try:
        config.read(config_path)
        
        # 認証情報の取得
        try:
            username = config.get('sentinelhub', 'username')
            password = config.get('sentinelhub', 'password')
            client_id = config.get('sentinelhub', 'client_id')
            client_secret = config.get('sentinelhub', 'client_secret')
            
            if not username or not password or not client_id or not client_secret:
                print("必要な設定が不足しています。config.iniファイルを確認してください。")
                return None
            
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {str(e)}")
            return None
            
        # Keycloak認証の設定
        try:
            # 認証トークンの取得
            auth_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
            auth_data = {
                "client_id": "cdse-public",
                "username": username,
                "password": password,
                "grant_type": "password",
                "scope": "openid profile email offline_access"
            }
            
            auth_headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            auth_response = requests.post(auth_url, headers=auth_headers, data=auth_data)
            auth_response.raise_for_status()
            auth_token = auth_response.json()["access_token"]
            print("Keycloak認証が成功しました")
            
            # SentinelHubの設定
            sh_config = SHConfig()
            sh_config.sh_base_url = 'https://services.sentinel-hub.com'
            sh_config.sh_client_id = client_id
            sh_config.sh_client_secret = client_secret
            sh_config.sh_oauth_token = auth_token
            
            # 設定の有効性を確認
            try:
                from sentinelhub import SentinelHubSession
                session = SentinelHubSession(sh_config)
                print("API認証が成功しました")
                
                # セッションの有効期限を確認
                #print(f"セッションの有効期限: {session.get_remaining_time()}")
                
                # その他の処理を継続
                # ...
                
            except Exception as e:
                print(f"API認証エラー: {str(e)}")
                return None
                
        except Exception as e:
            print(f"認証エラー: {str(e)}")
            return None
            
    except Exception as e:
        print(f"処理エラー: {str(e)}")
        return None
            
        print(f"設定ファイルの読み込みエラー: {str(e)}")
        return None
    
    # Bounding Boxの作成
    resolution = 10  # 10mの解像度
    bbox = BBox(bbox=[lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01], crs=CRS.WGS84)
    
    # リクエストの設定
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
    const B02_norm = Math.round(B02 / maxVal * 255);
    const B03_norm = Math.round(B03 / maxVal * 255);
    const B04_norm = Math.round(B04 / maxVal * 255);
    
    // 明るさ調整
    const factor = 1.5;
    const B02_final = Math.min(255, Math.max(0, B02_norm * factor));
    const B03_final = Math.min(255, Math.max(0, B03_norm * factor));
    const B04_final = Math.min(255, Math.max(0, B04_norm * factor));
    
    return [B04_final, B03_final, B02_final];
}
    """
    one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(one_month_ago, date),
                maxcc=0.1
            )
        ],
        responses=[
            SentinelHubRequest.output_response('default', MimeType.PNG)
        ],
        bbox=bbox,
        size=bbox_to_dimensions(bbox, resolution=resolution),
        config=sh_config
    )
    
    # ダウンロードの実行
    try:
        print("データのダウンロードを開始します...")
        data = request.get_data()
        
        if not data:
            print("データが見つかりませんでした。過去1ヶ月のデータを検索します...")
            one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            request = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
                        time_interval=(one_month_ago, date),
                        maxcc=0.1
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response('default', MimeType.PNG)
                ],
                bbox=bbox,
                size=bbox_to_dimensions(bbox, resolution=resolution),
                config=config
            )
            data = request.get_data()
            
            if not data:
                print("過去1ヶ月のデータも見つかりませんでした。")
                return None
        
        # 緯度-経度フォルダを作成
        coord_dir = os.path.join(output_dir, f"{lat}_{lon}")
        os.makedirs(coord_dir, exist_ok=True)
        
        # 画像を保存
        output_path = os.path.join(coord_dir, f'{date}.png')
        
        # データをPNGとして保存
        save_image(data, output_path)
        print(f"画像が保存されました: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None

def download_sentinel2_images_for_month(lat, lon, start_date, output_dir='sentinel2_images'):
    """
    指定座標の指定日付から1か月の画像データを連続で取得する
    
    Args:
        lat (float): 緯度
        lon (float): 経度
        start_date (str): 開始日付 (YYYYMMDD形式)
        output_dir (str, optional): 出力ディレクトリ
    
    Returns:
        list: ダウンロードされた画像のパスのリスト
    """
    downloaded_images = []
    current_date = datetime.strptime(start_date, "%Y%m%d")
    end_date = current_date + timedelta(days=30)
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        print(f"\n{date_str}のデータを取得中...")
        
        # 単一の日付の画像を取得
        image_path = download_sentinel2_image(lat, lon, date_str, output_dir)
        
        if image_path:
            downloaded_images.append(image_path)
        
        # 次の日付に移動
        current_date += timedelta(days=1)
    
    return downloaded_images

if __name__ == "__main__":
    os.makedirs("sentinel2_images", exist_ok=True)
    # 使用例
    latitude = 35.6812  # 緯度（例：東京駅）
    longitude = 139.7671  # 経度（例：東京駅）
    
    # 1か月分の画像を取得
    start_date = "20250601"  # 2025年6月1日から
    images = download_sentinel2_images_for_month(latitude, longitude, start_date)
    print(f"\n合計{len(images)}枚の画像を取得しました")
    
    # 単一の日付の画像を取得
    #single_date = "20250623"
    #single_image = download_sentinel2_image(latitude, longitude, single_date)
    #if single_image:
    #    print(f"単一の画像を保存しました: {single_image}")
    
    # 不要なコードを削除
    #longitude = 138.4132
    #latitude = 38.0608
    #today = datetime.now()
    #date = today.strftime("%Y%m%d")
    
    # 画像をダウンロード
    #output_path = download_sentinel2_image(latitude, longitude, date)
    #if output_path:
    #    print(f"画像が保存されました: {output_path}")
