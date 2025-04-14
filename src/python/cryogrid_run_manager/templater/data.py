import pathlib
from functools import lru_cache
from typing import Union

import xarray as xr
from loguru import logger


def make_data_for_run(run_path, res_m=100, sampling="random"):
    """
    Create the geospatial data for the run. This includes the following:
        - bbox.txt
        - elevation.tif
        - surface_classes.tif
        - geospatial_data.nc
        - era5.mat
    """
    from cryogrid_pytools import excel_config
    from cryogrid_pytools.forcing import era5_to_matlab

    from . import data

    run_path = pathlib.Path(run_path)
    forcing_path = run_path / "forcing"
    run_name = run_path.name

    path_config_xlsx = run_path / f"{run_name}.xlsx"
    path_bbox_txt = forcing_path / "bbox.txt"
    path_era5_mat = forcing_path / "era5.mat"

    bbox = data.get_bbox(path_bbox_txt)
    bbox = tuple(bbox)  # needs to be a tuple for caching

    config = excel_config.CryoGridConfigExcel(
        path_config_xlsx, check_file_paths=False, check_strat_layers=False
    )
    times = config.get_start_end_times()

    if not path_era5_mat.exists():
        ds_era5 = data.get_era5_from_s3_bucket(bbox, times.time_start, times.time_end)
        era5_to_matlab(ds_era5, save_path=str(path_era5_mat))

    ds_geo = data.get_geospatial_data(
        bbox, path_config_xlsx, res_m=res_m, sampling=sampling
    )
    # save the geospatial data required for the run to forcing folder
    # these names work with the template files
    for key in [
        "elevation",
        "albedo",
        "emissivity",
        "snow_index",
        "stratigraphy_index",
        "roughness_length",
    ]:
        ds_geo[key].rio.to_raster(forcing_path / f"{key}.tif")

    # save all spatial data to a netcdf file
    ds_geo = data.make_dataset_netcdf_ready(ds_geo)
    ds_geo.to_netcdf(
        forcing_path / "geospatial_data.nc",
        encoding={k: {"zlib": True} for k in ds_geo.data_vars},
    )

    return path_bbox_txt, path_config_xlsx


def get_geospatial_data(
    bbox: tuple,
    path_config_xlsx: Union[pathlib.Path, str],
    res_m=100,
    sampling="random",
) -> xr.Dataset:
    import xrspatial
    from cryogrid_pytools import data

    from .surface_index import calc_surface_index, exchage_values

    ds_out = xr.Dataset()

    bbox_str = ", ".join([f"{x:.3f}" for x in bbox])
    logger.info(f"Getting geospatial data for bbox [{bbox_str}]")

    # all other datasets are reprojected to the DEM
    dem = data.get_dem_copernicus30(bbox, res_m=res_m).compute()
    ds_out["elevation"] = dem
    ds_out["slope"] = xrspatial.slope(dem)

    # masks based on shapefile polygons
    ds_out["glaciers"] = data.get_randolph_glacier_inventory(dem)
    ds_out["rock_glaciers"] = data.get_TPRoGI_rock_glaciers(dem)

    # ground surface properties - emissivity and albedo to update ground properties
    ds_out["emissivity"] = data.get_aster_ged_emmis_elev(dem).aster_emissivity.mean(
        dim="band", keep_attrs=True
    )
    ds_out["albedo"] = data.get_modis_albedo_500m(dem)

    # used to adjust the snowfall - have to play around with these values
    ds_out["snow_index"] = data.get_snow_melt_doy(dem).mean("year")

    # used to calculate the surface index
    ds_out["land_cover"] = data.get_esri_land_cover(dem).astype("int8")
    ds_out["land_cover"].attrs.pop("class_values", None)

    surface_index = calc_surface_index(
        dem=ds_out.elevation,
        land_cover=ds_out.land_cover,
        glaciers=ds_out.glaciers,
        rock_glaciers=ds_out.rock_glaciers,
    )

    mappings = get_surface_index_mappings(path_config_xlsx, sampling=sampling)
    for k, values_to_exchange in mappings.items():
        ds_out[k] = exchage_values(surface_index, values_to_exchange)

    ds_out = make_dataset_netcdf_ready(ds_out)

    return ds_out


def get_surface_index_mappings(
    path_config_xlsx: str,
    mapping_names=["stratigraphy_index", "roughness_length"],
    sampling="random",
) -> dict:
    from .surface_index import get_ground_info_table

    ds_ground_info = get_ground_info_table(path_config_xlsx, sampling=sampling)
    mappings = {k: ds_ground_info[k].to_dict() for k in mapping_names}

    return mappings


def get_bbox(fpath: pathlib.Path) -> list[str]:
    import numpy as np

    assert fpath.name.endswith("bbox.txt"), "File must be named bbox.txt"

    try:
        bbox = np.loadtxt(fpath, delimiter=",", dtype=float).tolist()
    except ValueError as e:
        bbox = np.loadtxt(fpath, delimiter=",", dtype=str).tolist()
        if "W" in str(e):
            raise TypeError(
                f"Could not read {fpath} as floats for the following: {bbox}"
            )

    return bbox


@lru_cache
def get_era5_from_s3_bucket(bbox: tuple, time_start: str, time_end: str):
    from copy import deepcopy

    import dotenv
    import pandas as pd
    import xarray as xr

    bbox = list(deepcopy(bbox))

    if not dotenv.load_dotenv():
        raise FileNotFoundError("Could not find .env file with S3 credentials")

    t0 = pd.Timestamp(time_start)
    t1 = pd.Timestamp(time_end)
    year0 = t0.year
    year1 = t1.year

    fname_era5_s3 = (
        "s3://spi-pamir-c7-sdsc/era5_data/central_asia/central_asia-{year}.zarr"
    )
    flist_era5_zarr = [
        fname_era5_s3.format(year=year) for year in range(year0, year1 + 1)
    ]

    ds_central_asia = xr.open_mfdataset(
        flist_era5_zarr,
        parallel=True,
        engine="zarr",
        combine="by_coords",  # combines by time dime
        compat="override",  # fastest option
        coords="all",  # keep all coordinates
    )  # make sure that .env is set up correctly

    logger.info(
        f"Downloading ERA5 data for bbox {bbox} from {time_start} to {time_end}"
    )

    ds = (
        ds_central_asia.sel(  # contains all central asia data from 1940 to 2024-10-01
            time=slice(time_start, time_end)
        )  # there are some values in 1959-01-01 that are nans
        .rio.write_crs(4326)  # set the crs to epsg:4326 so we can clip using rioxarray
        .rename(z_surf="Zs")  # prepare for the cg.era5_to_matlab function
    )

    # clip to our bbox
    ds_bbox = ds.rio.clip_box(*bbox, crs="epsg:4326", allow_one_dimensional_raster=True)

    if ds_bbox.latitude.size == 0 or ds_bbox.longitude.size == 0:
        raise ValueError(
            f"Could not find any data for bbox {bbox} from {time_start} to {time_end}"
        )

    if ds_bbox.latitude.size <= 1 or ds_bbox.longitude.size <= 1:
        logger.warning(
            f"Only one point found for bbox {bbox}, expanding the bbox to include more data"
        )
        if ds_bbox.latitude.size <= 1:
            # expand_bbox to have two points
            bbox[1] -= 0.2
            bbox[3] += 0.2
        if ds_bbox.longitude.size <= 1:
            bbox[0] -= 0.2
            bbox[2] += 0.2

        ds_bbox = ds.rio.clip_box(*bbox, crs="epsg:4326").isel(
            latitude=slice(0, 2), longitude=slice(0, 2)
        )

    # load the data into memory (takes ~20 secs with fast connection)
    ds_bbox = ds_bbox.load()

    return ds_bbox


def make_dataset_netcdf_ready(ds):
    import numpy as np
    from cryogrid_pytools.utils import drop_coords_without_dim

    for key in ds:
        if "spec" in ds[key].attrs:
            ds[key].attrs.pop("spec")
        for attr_key in ds[key].attrs:
            attr = ds[key].attrs[attr_key]
            if isinstance(attr, np.ndarray):
                ds[key].attrs[attr_key] = attr.tolist()
        if key in ds.data_vars:
            da = ds[key]
            ds[key] = da.astype("float32")

    # remove coordinates that are not in the data array
    crs = ds.rio.crs
    ds = drop_coords_without_dim(ds)
    ds = ds.rio.write_crs(crs)

    return ds
