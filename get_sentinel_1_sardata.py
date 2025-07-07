import os
import json
import configparser
import time
import numpy as np
from datetime import datetime, timedelta
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    MimeType,
    bbox_to_dimensions,
    DataCollection,
    SentinelHubCatalog,
    DataCollection,
    BBox,
    CRS,
    SentinelHubRequest,
    MimeType,
    bbox_to_dimensions
)
from PIL import Image
from datetime import datetime, timedelta
from pathlib import Path


def get_sentinel_config():
    config_path = Path(__file__).parent / 'config.ini'
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path)
    sh_config = SHConfig()
    sh_config.sh_base_url = 'https://services.sentinel-hub.com'
    sh_config.sh_client_id = config.get('sentinelhub', 'client_id')
    sh_config.sh_client_secret = config.get('sentinelhub', 'client_secret')
    return sh_config


def get_sentinel_1_metadata(sh_config, bbox, time_interval):
    catalog = SentinelHubCatalog(config=sh_config)
    metadata = catalog.search(
        DataCollection.SENTINEL1_IW,
        bbox=bbox,
        time=time_interval,
        fields={
            'include': [
                'properties.datetime',
                'properties.platform',
                'properties.eo:cloud_cover'
            ]
        }
    )
    return metadata


def limit_image_size(size, max_dim=2500):
    """
    画像サイズ(width, height)の上限をmax_dimに制限する
    """
    width = min(size[0], max_dim)
    height = min(size[1], max_dim)
    return (width, height)


def get_sar_data_by_id(sh_config, item_id, bbox, output_dir, resolution=10):
    """
    Sentinel-1のitem_idを指定してSARデータをダウンロードしGeoTIFFで保存
    """
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["VV"],
            output: { bands: 1 }
        };
    }
    function evaluatePixel(sample) {
        return [sample.VV];
    }
    """
    size = bbox_to_dimensions(bbox, resolution)
    size = limit_image_size(size)
    print(size)
    request = SentinelHubRequest(
        data_folder=output_dir,
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL1_IW,
                identifier=item_id
            )
        ],
        responses=[
            SentinelHubRequest.output_response('default', MimeType.TIFF)
        ],
        bbox=bbox,
        size=size,
        config=sh_config
    )
    data = request.get_data(save_data=True)
    return request.get_filename_list()[0] if request.get_filename_list() else None


def get_sar_data(sh_config, bbox, date_time, output_dir):
    """
    指定範囲・日時のSentinel-1 SARデータをダウンロードしGeoTIFFで保存
    """
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["VV"],
            output: { bands: 1 }
        };
    }
    function evaluatePixel(sample) {
        return [sample.VV];
    }
    """
    resolution = 10  # 10m解像度
    size = bbox_to_dimensions(bbox, resolution)
    size = limit_image_size(size)
    print(size)
    print(size)
    request = SentinelHubRequest(
        data_folder=output_dir,
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL1_IW,
                time_interval=(date_time[0], date_time[1])
            )
        ],
        responses=[
            SentinelHubRequest.output_response('default', MimeType.TIFF)
        ],
        bbox=bbox,
        size=size,
        config=sh_config
    )
    request.get_data(save_data=True)
    # res_data = request.get_data(save_data=True)
    # 保存ファイルパスを返す
    if request.get_filename_list()[0]:
        return request.get_filename_list()[0]
    else:
        return None


def main():
    sh_config = get_sentinel_config()
    bbox = BBox(bbox=(139.0, 35.5, 139.5, 36.0), crs=CRS.WGS84)
    time_interval = ('2023-01-01', '2023-01-15')
    metadata = get_sentinel_1_metadata(sh_config, bbox, time_interval)
    os.makedirs('sar_data', exist_ok=True)
    for item in metadata:
        # print(item['bbox'])
        # 小数点4桁に丸める
        rounded_bbox = [round(coord, 4) for coord in item['bbox']]
        tmp_bbox = BBox(
            bbox=(
                rounded_bbox[0], rounded_bbox[1],
                rounded_bbox[2], rounded_bbox[3]
            ),
            crs=CRS.WGS84
        )
        # get_sar_data_by_id(sh_config, item['id'], tmp_bbox, 'sar_data')
        get_sar_data(sh_config, tmp_bbox, time_interval, 'sar_data')


if __name__ == '__main__':
    main()
