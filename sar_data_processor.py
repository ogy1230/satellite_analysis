import os
import json
from datetime import datetime
import numpy as np
import rasterio
from sentinelhub import (
    SentinelHubDownloadClient,
    SentinelHubSession,
    SHConfig,
    BBox,
    CRS,
    DataCollection,
    DownloadRequest,
    MimeType,
    bbox_to_dimensions
)
from pathlib import Path

class SARDataProcessor:
    def __init__(self, config_path='config.ini'):
        self.config = SHConfig()
        self.load_config(config_path)
        self.session = SentinelHubSession(config=self.config)
        self.output_dir = Path("sar_data")
        self.output_dir.mkdir(exist_ok=True)

    def load_config(self, config_path):
        """設定ファイルから認証情報を読み込む"""
        import configparser
        config = configparser.ConfigParser(interpolation=None)
        config.read(config_path)
        
        if config.has_section('sentinelhub'):
            # API認証情報の設定
            self.config.sh_client_id = config.get('sentinelhub', 'client_id')
            self.config.sh_client_secret = config.get('sentinelhub', 'client_secret')
            
            # デフォルトの設定
            self.config.sh_base_url = 'https://services.sentinel-hub.com'
            self.config.sh_auth_base_url = 'https://services.sentinel-hub.com/oauth/token'
            
            # セッションの有効期限を設定
            self.config.sh_session_validity = 3600  # 1時間
            
        else:
            raise ValueError("設定ファイルにsentinelhubセクションが見つかりません")

    def get_sar_data(self, bbox, time_interval, resolution=10):
        """
        SARデータを取得する
        
        Args:
            bbox: (min_x, min_y, max_x, max_y)の形式のBBox
            time_interval: (start_date, end_date)の形式のタプル
            resolution: 出力解像度（メートル）
        
        Returns:
            SARデータのパス
        """
        start_date, end_date = time_interval
        bbox = BBox(bbox=bbox, crs=CRS.WGS84)
        
        width, height = bbox_to_dimensions(bbox, resolution=resolution)
        
        request = DownloadRequest(
            data_folder=str(self.output_dir),
            request_type='POST',
            url='https://services.sentinel-hub.com/api/v1/process',
            headers={'Content-Type': 'application/json'},
            post_values={
                "input": {
                    "bounds": {
                        "bbox": bbox.lower_left + bbox.upper_right,
                        "properties": {
                            "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                        }
                    },
                    "data": [
                        {
                            "type": "sentinel-1-grd",
                            "dataFilter": {
                                "timeRange": {
                                    "from": start_date,
                                    "to": end_date
                                }
                            },
                            "processing": {
                                "backCoeff": "GAMMA0_TERRAIN"
                            }
                        }
                    ]
                },
                "output": {
                    "responses": [
                        {
                            "identifier": "default",
                            "format": {
                                "type": "image/tiff"
                            }
                        }
                    ]
                }
            },
            save_response=True
        )
        
        client = SentinelHubDownloadClient(config=self.config, session=self.session)
        response = client.download(request)
        
        # 出力ファイルのパスを返す
        return os.path.join(self.output_dir, response['default']['url'].split('/')[-1])

    def calculate_difference(self, file1, file2, output_path):
        """
        2つのSARデータの差分を計算する
        
        Args:
            file1: ファイル1のパス
            file2: ファイル2のパス
            output_path: 差分データの出力パス
        """
        with rasterio.open(file1) as src1:
            data1 = src1.read(1)
            profile = src1.profile

        with rasterio.open(file2) as src2:
            data2 = src2.read(1)

        # 差分を計算
        diff = data2 - data1
        
        # メタデータを更新
        profile.update(dtype=diff.dtype)
        
        # 差分データを保存
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(diff, 1)

    def plot_difference(self, diff_file, output_path):
        """
        差分データを可視化して保存する
        
        Args:
            diff_file: 差分データのファイルパス
            output_path: 出力画像のパス
        """
        import matplotlib.pyplot as plt
        
        with rasterio.open(diff_file) as src:
            diff = src.read(1)
            
        plt.figure(figsize=(10, 10))
        plt.imshow(diff, cmap='seismic', vmin=-100, vmax=100)
        plt.colorbar(label='差分値')
        plt.title('SARデータの差分')
        plt.savefig(output_path)
        plt.close()

def main():
    # 使用例
    processor = SARDataProcessor()
    
    # 取得範囲の定義（例：東京付近）
    bbox = (139.0, 35.5, 139.5, 36.0)
    
    # 2つの期間を定義
    period1 = ('2023-01-01', '2023-01-15')
    period2 = ('2023-06-01', '2023-06-15')
    
    # SARデータを取得
    sar1_path = processor.get_sar_data(bbox, period1)
    sar2_path = processor.get_sar_data(bbox, period2)
    
    # 差分を計算
    diff_path = processor.output_dir / 'difference.tif'
    processor.calculate_difference(sar1_path, sar2_path, diff_path)
    
    # 差分を可視化
    plot_path = processor.output_dir / 'difference_plot.png'
    processor.plot_difference(diff_path, plot_path)
    
    print(f"差分データが保存されました: {diff_path}")
    print(f"差分画像が保存されました: {plot_path}")

if __name__ == "__main__":
    main()
