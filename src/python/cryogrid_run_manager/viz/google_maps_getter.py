from functools import lru_cache

import numpy as np
import rioxarray as rxr  # noqa
import xarray as xr
from loguru import logger
from pygeotile.tile import Tile

logger.warning(
    "Note that you can only use google_maps_viz for non-commercial "
    "visualizations and not for computation and bulk downloads. "
)


class GoogleTile(Tile):
    def __new__(cls, *args, map_layer="s", **kwargs):
        self = super(GoogleTile, cls).__new__(cls, *args, **kwargs)
        self.TILE_SIZE = 256
        self.shape = self.TILE_SIZE, self.TILE_SIZE

        self.x = self.google[0]
        self.y = self.google[1]

        self.set_layer(map_layer)
        self.map_layer = map_layer

        self._xr = None
        self._image = None
        self._data = None

        return self

    def set_layer(self, layer="s"):
        self._url = self._get_url_for_layer(layer)
        self.url = self._url.format(x=self.x, y=self.y, z=self.zoom)

    def _get_url_for_layer(self, layer="s"):
        __doc__ = """
        Returns a URL for a Google Maps tile.

        Parameters
        ----------
        layer : str
            The layer to use. Valid values are:
                s: Google Satellite
                y: Google Satellite Hybrid
                p: Google Terrain Hybrid
                t: Google Terrain
            Invalid that exist, but do not work for this package:
                m: Google Maps
                h: Google Roads
        """
        layer = layer.lower()
        valid = "\n" + "\n".join(__doc__.split("\n")[7:10])
        assert layer in "syp", f"Invalid layer: {layer}, valid layers are {valid}"

        # map tile number to subdomain
        d = 0 if layer in "msy" else 1

        url = f"https://mt{d}.google.com/vt/lyrs={layer}&x={{x}}&y={{y}}&z={{z}}"
        return url

    @property
    def bbox(self):
        lower_left = self.bounds[0]
        upper_right = self.bounds[1]
        bbox_WSEN = [
            lower_left.longitude,
            lower_left.latitude,
            upper_right.longitude,
            upper_right.latitude,
        ]
        return bbox_WSEN

    @property
    def image(self):
        if self._image is None:
            self._image = self.get_image()
        return self._image

    @property
    def data(self):
        if self._data is None:
            self._data = self.get_data()
        return self._data

    @property
    def xr(self):
        if self._xr is None:
            self._xr = self.get_dataarray()
        return self._xr

    @property
    def lat(self):
        y0 = self.y * self.TILE_SIZE
        y1 = y0 + self.TILE_SIZE
        x = self.x * self.TILE_SIZE + self.TILE_SIZE // 2

        pixel_range = np.arange(y0, y1, dtype=float)
        lats = self._from_pixel_loc_to_latlng(x, pixel_range, self.zoom)[0]
        return lats

    @property
    def lon(self):
        x0 = self.x * self.TILE_SIZE
        x1 = x0 + self.TILE_SIZE
        y = self.y * self.TILE_SIZE + self.TILE_SIZE // 2

        pixel_range = np.arange(x0, x1, dtype=float)
        lons = self._from_pixel_loc_to_latlng(pixel_range, y, self.zoom)[1]
        return lons

    @staticmethod
    def _download_url_to_bytes(url):
        from io import BytesIO

        import requests

        response = requests.get(url)
        io = BytesIO(response.content)
        return io

    @staticmethod
    def get_resolution_from_bbox_and_shape(bbox, shape):
        from rasterio.transform import from_bounds

        x, y = shape[:2]
        transform = from_bounds(*bbox, x, y)
        res = abs(transform[0])
        return res

    def get_image(self):
        from PIL import Image

        file_obj = self._download_url_to_bytes(self.url)
        image = Image.open(file_obj)
        return image

    def get_data(self):
        image = self.get_image()
        data = np.array(image)
        return data

    def _from_pixel_loc_to_latlng(self, x, y, zoom):
        import math

        pixels_per_lon_degree = self.TILE_SIZE / 360.0
        pixels_per_lon_radian = self.TILE_SIZE / (2 * math.pi)

        x0 = self.TILE_SIZE / 2.0
        y0 = self.TILE_SIZE / 2.0

        num_tiles = 1 << zoom
        x /= num_tiles
        y /= num_tiles

        lon = (x - x0) / pixels_per_lon_degree

        lat_radians = (y - y0) / -pixels_per_lon_radian
        lat = np.rad2deg(2 * np.arctan(np.exp(lat_radians)) - np.pi / 2)

        return lat, lon

    def get_dataarray(self):
        data = self.get_data()
        da = xr.DataArray(
            data=data,
            dims=["y", "x", "band"],
            coords={
                "y": self.lat,
                "x": self.lon,
                "band": "r g b".split(),
            },
        ).transpose("band", "y", "x")

        da = da.rio.write_crs("EPSG:4326")

        return da


@lru_cache(maxsize=3)
class GoogleScene:
    def __init__(self, bbox, load=False, max_pixels=2048, map_layer="s"):
        self.bbox = bbox
        self.max_pixels = max_pixels
        self.map_layer = map_layer

        self._data = None
        self._xr = None

        self._zoom_res = self._get_zoom_level_resolution()
        self.zoom = self._get_zoom_level()

        self._tiles = None

        if load:
            _ = self.xr

    @property
    def tiles(self):
        if self._tiles is None:
            self._tiles = self.get_tiles()
        return self._tiles

    @property
    def xr(self):
        if self._xr is None:
            self._xr = self._get_dataarray()
        return self._xr

    @property
    def data(self):
        if self._data is None:
            self._data = self.xr.data
        return self._data

    def plot(self, ax=None, dpi=100, **kwargs):
        import matplotlib.pyplot as plt

        da = self.xr

        if ax is None:
            ry, rx = da.y.size, da.x.size
            pixel_ratio = ry / rx

            width = 10
            fig, ax = plt.subplots(figsize=(width, width * pixel_ratio), dpi=dpi)
        else:
            fig = ax.get_figure()

        props = {}
        props.update(kwargs)
        da.plot.imshow(ax=ax, **props)

        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.set_title("")

        ax.set_position([0, 0, 1, 1])

        return fig, ax

    def _get_zoom_level_resolution(self):
        zoom_levels = range(20)
        res_m = {}
        for z in zoom_levels:
            tile = GoogleTile.for_latitude_longitude(0, 0, z)
            bbox = tile.bbox
            tile.shape
            res_deg = GoogleTile.get_resolution_from_bbox_and_shape(bbox, (256, 256))
            res_m[z] = res_deg * 111139

        return res_m

    def _get_zoom_level(self):
        dx = abs(self.bbox[2] - self.bbox[0])
        dy = abs(self.bbox[3] - self.bbox[1])
        bbox_size_m = max(dx, dy) * 111139

        for z, res in self._zoom_res.items():
            n_pixels_in_bbox_at_res = bbox_size_m / res
            if n_pixels_in_bbox_at_res > self.max_pixels:
                return z

    def get_tiles(self):
        zoom = 19 if self.zoom is None else self.zoom
        west, south, east, north = self.bbox
        ll = GoogleTile.for_latitude_longitude(south, west, zoom)
        ur = GoogleTile.for_latitude_longitude(north, east, zoom)

        x0, x1 = min(ll.x, ur.x), max(ll.x, ur.x)
        y0, y1 = min(ll.y, ur.y), max(ll.y, ur.y)

        x_range = range(x0, x1 + 1)
        y_range = range(y0, y1 + 1)

        tiles = []
        for x in x_range:
            for y in y_range:
                tile = GoogleTile.from_google(x, y, zoom)
                tile.set_layer(self.map_layer)
                tiles += (tile,)

        return tiles

    def _parallel_tile_download(self, tiles, n_jobs=12):
        import joblib

        func = joblib.delayed(lambda tile: tile.xr)
        tasks = [func(tile) for tile in tiles]
        _ = joblib.Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(tasks)

    def _get_dataarray(self):
        n_tiles = len(self.tiles)
        n_jobs = min(24, n_tiles)

        logger.info(f"Downloading {n_tiles} tiles with {n_jobs} jobs")
        self._parallel_tile_download(self.tiles, n_jobs=n_jobs)

        da_list = [tile.xr for tile in self.tiles]

        logger.info("Combining tiles with xarray.combine_by_coords")
        da = xr.combine_by_coords(da_list)

        da = da.sortby("y").sortby("x")
        da = da.sel(
            x=slice(self.bbox[0], self.bbox[2]), y=slice(self.bbox[1], self.bbox[3])
        )

        return da

    def _repr_html_(self):
        if self._xr is None:
            pass
        else:
            fig, ax = self.plot()

    def __repr__(self):
        n_tiles = len(self.tiles)
        return f"GoogleScene({self.bbox}, max_pixels={self.max_pixels}, zoom={self.zoom}, n_tiles={n_tiles})"
