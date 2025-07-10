import requests
from pathlib import Path

def download_opentopo_dem(bbox, out_path, apikey):
    min_lon, min_lat, max_lon, max_lat = bbox
    url = (
        "https://portal.opentopography.org/API/globaldem?"
        f"demtype=SRTMGL1"
        f"&south={min_lat}&north={max_lat}&west={min_lon}&east={max_lon}"
        f"&outputFormat=GTiff"
        f"&API_Key={apikey}"
    )
    print(f"Requesting DEM from: {url}")
    r = requests.get(url)
    if r.status_code == 200 and r.headers['Content-Type'] in ['image/tiff', 'application/octet-stream']:
        Path(out_path).parent.mkdir(exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(r.content)
        print(f"DEM saved to {out_path}")
    else:
        print("DEMダウンロード失敗。OpenTopographyのAPI制限や範囲指定エラーの可能性があります。")
        print(r.status_code)
        print(r.headers)
        #print(r.text)

if __name__ == '__main__':
    bbox = (138.17, 37.81, 138.61, 38.34)
    out_path = 'dem/dem.tif'
    apikey = '0aad4e5666d5e7e2ea07b8456ac9599c'
    download_opentopo_dem(bbox, out_path, apikey)