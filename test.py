import matplotlib.pyplot as plt
from sentinelhub import SHConfig
from sentinelhub import CRS, BBox, bbox_to_dimensions
from sentinelhub import MimeType, SentinelHubRequest, SentinelHubDownloadClient, DataCollection, DownloadRequest

config = SHConfig()
config.sh_client_id = "bc6ce102-f635-4d82-9890-e8bd7ea69873"
config.sh_client_secret = "j9eLbr9tCNKEOmjGVmPNGa4EGcwyTpz6"


# WGS84
target_coords = [
    -0.3273582458496094,
    51.45892724311225,
    -0.2847862243652344,
    51.48801054716568
]

res = 2
target_bbox = BBox(bbox=target_coords, crs=CRS.WGS84)
target_size = bbox_to_dimensions(target_bbox, resolution=res)

print(f'Image shape at {res} m resolution: {target_size} pixels')


evalscript_true_color = """
 //VERSION=3

    function setup() {
        return {
            input: [{
                bands: ["B02", "B03", "B04"]
            }],
            output: {
                bands: 3
            }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02];
    }
"""


request_true_color = SentinelHubRequest(
    evalscript=evalscript_true_color,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L1C,
            time_interval=('2020-12-1', '2020-12-31'),
            mosaicking_order='leastCC'
        )
    ],
    responses=[
        SentinelHubRequest.output_response('default', MimeType.PNG)
    ],

    bbox=target_bbox,
    size=target_size,
    config=config
)

rue_color_imgs = request_true_color.get_data()

plt.imshow(rue_color_imgs[0]*3.5/255)
plt.axis(False)
plt.show()
