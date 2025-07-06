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



if __name__ == '__main__':
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
    latitude = 35.6812  # 緯度（例：東京駅）
    longitude = 139.7671  # 経度（例：東京駅）
    bbox = BBox(bbox=[longitude - 0.01, latitude - 0.01, longitude + 0.01, latitude + 0.01], crs=CRS.WGS84)
    
    # 時間範囲設定
    today = datetime.now()
    date = today.strftime("%Y%m%d")
    one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=365)).strftime("%Y%m%d")
    time_interval = (one_month_ago, date)

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
    target_dates = [
        '2024-07-05',
    ]
    for item in search_iterator:
        date = item['properties']['datetime'].split('T')[0]
        if date in target_dates:
            print(item)