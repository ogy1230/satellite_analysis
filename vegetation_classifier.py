import requests
import datetime
import json
import xml.etree.ElementTree as ET
from typing import Tuple, Optional
import numpy as np
import rasterio
from rasterio.enums import Resampling
import os

class SatelliteDataFetcher:
    def __init__(self):
        self.copernicus_url = "https://scihub.copernicus.eu/dhus/search"
        self.earthdata_url = "https://search.earthdata.nasa.gov/search"

    def get_sentinel1_data(self, lat: float, lon: float, date: datetime.datetime) -> Optional[str]:
        """
        Sentinel-1データを取得
        """
        try:
            params = {
                'q': f'platformname:Sentinel-1 AND footprint:"Intersects(POINT({lon} {lat}))"',
                'start': 0,
                'rows': 1,
                'format': 'json',
                'date': f'[{date.strftime("%Y-%m-%d")}T00:00:00.000Z TO {date.strftime("%Y-%m-%d")}T23:59:59.999Z]'
            }
            
            response = requests.get(self.copernicus_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['feed']['opensearch:totalResults'] > 0:
                    return data['feed']['entry'][0]['link'][0]['href']
        except Exception as e:
            print(f"Error fetching Sentinel-1 data: {e}")
        return None

    def get_alos2_data(self, lat: float, lon: float, date: datetime.datetime) -> Optional[str]:
        """
        ALOS-2データを取得
        """
        try:
            params = {
                'q': f'platformname:ALOS-2 AND footprint:"Intersects(POINT({lon} {lat}))"',
                'start': 0,
                'rows': 1,
                'format': 'json',
                'date': f'[{date.strftime("%Y-%m-%d")}T00:00:00.000Z TO {date.strftime("%Y-%m-%d")}T23:59:59.999Z]'
            }
            
            response = requests.get(self.earthdata_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['feed']['opensearch:totalResults'] > 0:
                    return data['feed']['entry'][0]['link'][0]['href']
        except Exception as e:
            print(f"Error fetching ALOS-2 data: {e}")
        return None

class VegetationClassifier:
    def __init__(self):
        self.data_fetcher = SatelliteDataFetcher()

    def get_closest_date_data(self, lat: float, lon: float, target_date: datetime.datetime, days_range: int = 30) -> Tuple[Optional[str], Optional[str]]:
        """
        指定された日付の近傍のデータを取得
        """
        current_date = target_date
        for i in range(days_range):
            # 前後の日付をチェック
            for delta in [-1, 1]:
                check_date = current_date + datetime.timedelta(days=delta * i)
                
                sentinel1_url = self.data_fetcher.get_sentinel1_data(lat, lon, check_date)
                if sentinel1_url:
                    return sentinel1_url, None
                
                alos2_url = self.data_fetcher.get_alos2_data(lat, lon, check_date)
                if alos2_url:
                    return None, alos2_url
        
        return None, None

    def classify_vegetation(self, lat: float, lon: float, target_date: datetime.datetime) -> str:
        """
        植生を分類
        """
        sentinel1_url, alos2_url = self.get_closest_date_data(lat, lon, target_date)
        
        if sentinel1_url:
            # Sentinel-1データを使用
            with rasterio.open(sentinel1_url) as src:
                # データを読み込み
                data = src.read(1)
                # データの統計を計算
                mean = np.mean(data)
                std = np.std(data)
                
                # 植生の分類
                if mean > -10 and std > 5:
                    return "森林"
                elif mean > -15 and std < 5:
                    return "草地"
                else:
                    return "その他"
        
        elif alos2_url:
            # ALOS-2データを使用
            with rasterio.open(alos2_url) as src:
                # データを読み込み
                data = src.read(1)
                # データの統計を計算
                mean = np.mean(data)
                std = np.std(data)
                
                # 植生の分類
                if mean > -10 and std > 5:
                    return "森林"
                elif mean > -15 and std < 5:
                    return "草地"
                else:
                    return "その他"
        
        return "データ取得不可"

def main():
    # 使用例
    classifier = VegetationClassifier()
    
    # 緯度経度と日付を指定
    latitude = 35.6895  # 東京の緯度
    longitude = 139.6917  # 東京の経度
    target_date = datetime.datetime(2025, 6, 22)
    
    result = classifier.classify_vegetation(latitude, longitude, target_date)
    print(f"植生の分類結果: {result}")

if __name__ == "__main__":
    main()
