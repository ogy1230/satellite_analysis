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
from sentinelhub import SentinelHubSession


def main():
    config_path = Path(__file__).parent / 'config.ini'
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path)
    client_id = config.get('sentinelhub', 'client_id')
    client_secret = config.get('sentinelhub', 'client_secret')
    sh_config = SHConfig()
    sh_config.sh_base_url = 'https://services.sentinel-hub.com'
    sh_config.sh_client_id = client_id
    sh_config.sh_client_secret = client_secret
    session = SentinelHubSession(sh_config)
    resolution = 10  # 10mの解像度
    latitude = 35.6812  # 緯度（例：東京駅）
    longitude = 139.7671  # 経度（例：東京駅）
    bbox = BBox(bbox=[longitude - 0.01, latitude - 0.01, longitude + 0.01, latitude + 0.01], crs=CRS.WGS84)
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
    today = datetime.now()
    date = today.strftime("%Y%m%d")
    one_month_ago = (datetime.strptime(date, "%Y%m%d") - timedelta(days=90)).strftime("%Y%m%d")
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
    data = request.get_data()
    print(len(data))



if __name__ == '__main__':
    main()
