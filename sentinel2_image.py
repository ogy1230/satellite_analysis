import os
import requests
from datetime import datetime, timedelta
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt
import numpy as np
from rasterio.merge import merge
from rasterio.plot import reshape_as_image

def download_sentinel2_image(lat, lon, date, output_dir='sentinel2_images'):
    # SentinelHub APIの認証情報を環境変数から取得
    user = os.getenv('DHUS_USER')
    password = os.getenv('DHUS_PASSWORD')
    
    if not user or not password:
        print("DHUS_USERまたはDHUS_PASSWORDが設定されていません。環境変数を設定してください。")
        return None
        
    try:
        api = SentinelAPI(
            user, 
            password, 
            'https://scihub.copernicus.eu/dhus',
            timeout=30  # 30秒のタイムアウト設定
        )
        
        # APIの認証テスト
        try:
            api.query(platformname='Sentinel-2', date=(date, date))
        except Exception as e:
            print(f"API認証エラー: {str(e)}")
            return None
    except Exception as e:
        print(f"API接続エラー: {str(e)}")
        return None
    
    # 緯度経度からBBOXを生成
    bbox = (lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01)
    
    # データの存在確認
    try:
        print("データの存在を確認中...")
        products = api.query(
            area=geojson_to_wkt({
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]]
                ]]
            }),
            date=(date, date),
            platformname='Sentinel-2',
            cloudcoverpercentage=(0, 100)  # クラウドカバーの制限を緩和
        )
        
        if not products:
            print("データが見つかりませんでした。過去1ヶ月のデータを検索します...")
            one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            products = api.query(
                area=geojson_to_wkt({
                    "type": "Polygon",
                    "coordinates": [[
                        [bbox[0], bbox[1]],
                        [bbox[2], bbox[1]],
                        [bbox[2], bbox[3]],
                        [bbox[0], bbox[3]],
                        [bbox[0], bbox[1]]
                    ]]
                }),
                date=(one_month_ago, date),
                platformname='Sentinel-2',
                cloudcoverpercentage=(0, 100),
                order_by='cloudcoverpercentage'
            )
            
            if not products:
                print("過去1ヶ月のデータも見つかりませんでした。")
                return None
    except Exception as e:
        print(f"データ検索エラー: {str(e)}")
        return None
    
    # データが見つかった場合にダウンロード
    try:
        product_id = list(products.keys())[0]
        print(f"ダウンロードを開始します: {product_id}")
        api.download(product_id, directory_path=output_dir)
        
        # ダウンロードしたファイルのパスを取得
        zip_path = os.path.join(output_dir, f'{product_id}.zip')
        
        # ZIPファイルからB04(レッド)、B03(グリーン)、B02(ブルー)バンドを抽出
        with rasterio.open(f'zip://{zip_path}!*/T*/R*/B04.jp2') as red:
            with rasterio.open(f'zip://{zip_path}!*/T*/R*/B03.jp2') as green:
                with rasterio.open(f'zip://{zip_path}!*/T*/R*/B02.jp2') as blue:
                    # 画像を読み込み
                    red_data = red.read(1)
                    green_data = green.read(1)
                    blue_data = blue.read(1)
                    
                    # データを正規化
                    red_data = (red_data.astype(float) - red_data.min()) / (red_data.max() - red_data.min())
                    green_data = (green_data.astype(float) - green_data.min()) / (green_data.max() - green_data.min())
                    blue_data = (blue_data.astype(float) - blue_data.min()) / (blue_data.max() - blue_data.min())
                    
                    # RGB画像を作成
                    rgb = np.stack([red_data, green_data, blue_data], axis=-1)
                    
                    # 画像を保存
                    output_path = os.path.join(output_dir, f'sentinel2_{lat}_{lon}_{date}.png')
                    plt.imsave(output_path, rgb)
                    
                    return output_path
    except Exception as e:
        print(f"データダウンロードエラー: {str(e)}")
        return None
        
        if not products:
            print("データが見つかりませんでした。過去1ヶ月のデータを検索します...")
            one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            products = api.query(
                area=geojson_to_wkt({
                    "type": "Polygon",
                    "coordinates": [[
                        [bbox[0], bbox[1]],
                        [bbox[2], bbox[1]],
                        [bbox[2], bbox[3]],
                        [bbox[0], bbox[3]],
                        [bbox[0], bbox[1]]
                    ]]
                }),
                date=(one_month_ago, date),
                platformname='Sentinel-2',
                cloudcoverpercentage=(0, 100),
                order_by='cloudcoverpercentage'
            )
            
            if not products:
                print("過去1ヶ月のデータも見つかりませんでした。")
                return None
    except Exception as e:
        print(f"データ検索エラー: {str(e)}")
        return None
    
    # データが見つかった場合にダウンロード
    try:
        product_id = list(products.keys())[0]
        print(f"ダウンロードを開始します: {product_id}")
        api.download(product_id, directory_path=output_dir)
        
        # ダウンロードしたファイルのパスを取得
        zip_path = os.path.join(output_dir, f'{product_id}.zip')
        
        # ZIPファイルからB04(レッド)、B03(グリーン)、B02(ブルー)バンドを抽出
        with rasterio.open(f'zip://{zip_path}!*/T*/R*/B04.jp2') as red:
            with rasterio.open(f'zip://{zip_path}!*/T*/R*/B03.jp2') as green:
                with rasterio.open(f'zip://{zip_path}!*/T*/R*/B02.jp2') as blue:
                    # 画像を読み込み
                    red_data = red.read(1)
                    green_data = green.read(1)
                    blue_data = blue.read(1)
                    
                    # データを正規化
                    red_data = (red_data.astype(float) - red_data.min()) / (red_data.max() - red_data.min())
                    green_data = (green_data.astype(float) - green_data.min()) / (green_data.max() - green_data.min())
                    blue_data = (blue_data.astype(float) - blue_data.min()) / (blue_data.max() - blue_data.min())
                    
                    # RGB画像を作成
                    rgb = np.stack([red_data, green_data, blue_data], axis=-1)
                    
                    # 画像を保存
                    output_path = os.path.join(output_dir, f'sentinel2_{lat}_{lon}_{date}.png')
                    plt.imsave(output_path, rgb)
                    
                    return output_path
    except Exception as e:
        print(f"データダウンロードエラー: {str(e)}")
        return None
    
    # Sentinel-2のデータを検索
    products = api.query(
        area=geojson_to_wkt({
            "type": "Polygon",
            "coordinates": [[
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]]
            ]]
        })
    )
    if products:
        product_id = list(products.keys())[0]
        try:
            api.download(product_id, directory_path=output_dir)
        except Exception as e:
            print(f"データダウンロードエラー: {str(e)}")
            return None
        
        # ダウンロードしたファイルのパスを取得
        zip_path = os.path.join(output_dir, f'{product_id}.zip')
        
        # ZIPファイルからB04(レッド)、B03(グリーン)、B02(ブルー)バンドを抽出
        with rasterio.open(f'zip://{zip_path}!*/T*/R*/B04.jp2') as red:
            with rasterio.open(f'zip://{zip_path}!*/T*/R*/B03.jp2') as green:
                with rasterio.open(f'zip://{zip_path}!*/T*/R*/B02.jp2') as blue:
                    # 画像を読み込み
                    red_data = red.read(1)
                    green_data = green.read(1)
                    blue_data = blue.read(1)
                    
                    # データを正規化
                    red_data = (red_data.astype(float) - red_data.min()) / (red_data.max() - red_data.min())
                    green_data = (green_data.astype(float) - green_data.min()) / (green_data.max() - green_data.min())
                    blue_data = (blue_data.astype(float) - blue_data.min()) / (blue_data.max() - blue_data.min())
                    
                    # RGB画像を作成
                    rgb = np.stack([red_data, green_data, blue_data], axis=-1)
                    
                    # 画像を保存
                    output_path = os.path.join(output_dir, f'sentinel2_{lat}_{lon}_{date}.png')
                    plt.imsave(output_path, rgb)
                    
                    return output_path
    else:
        print("該当するデータが見つかりませんでした")
        return None

if __name__ == "__main__":
    # 使用例
    # 緯度経度を指定（例：東京駅）
    latitude = 35.6812
    longitude = 139.7671
    # 日付を指定（YYYY-MM-DD形式）
    # 現在までの最新のデータを取得
    today = datetime.now()
    date = today.strftime("%Y%m%d")
    
    # 画像をダウンロード
    output_path = download_sentinel2_image(latitude, longitude, date)
    if output_path:
        print(f"画像が保存されました: {output_path}")
