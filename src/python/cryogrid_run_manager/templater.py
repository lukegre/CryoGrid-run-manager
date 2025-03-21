import pathlib
from functools import lru_cache
from typing import Union

import matplotlib.pyplot as plt
import xarray as xr
from loguru import logger


def main(run_path, bbox_WSEN, template_dir, n_land_classes=3):
    fpath_config = make_run_folder_structure(run_path, bbox_WSEN, template_dir)
    fpath_bbox, fpath_config = make_data_for_run(
        run_path, n_land_classes=n_land_classes
    )
    make_forcing_plots(run_path)

    return fpath_bbox, fpath_config


def make_run_folder_structure(
    run_path: Union[str, pathlib.Path],
    bbox_WSEN: list[float],
    template_dir: Union[str, pathlib.Path],
):
    """
    Create the folder structure for a CryoGrid run. This includes the following:
        - README.md
        - run_cryogrid.m
        - <run_name>.xlsx
        - CONSTANTS.xlsx
        - forcing (dir)
            - bbox.txt
            - ...
        - output ...
        - source ...
        - figures ...

    Parameters
    ----------
    run_path : Union[str, pathlib.Path]
        The path to the run folder with the last part of the path being the run name.
    """
    run_path = pathlib.Path(run_path)
    template_dir = pathlib.Path(template_dir)
    run_name = run_path.name

    make_folder_structure(run_path)
    copy_matplab_custom(run_path)

    # Create the README.md file
    readme_str = f"# CryoGrid: `{run_name}`\n\nThis folder contains the files for the CryoGrid run `{run_name}`."
    with open(run_path / "README.md", "w") as f:
        f.write(readme_str)

    # Create the bbox.txt file
    bbox_str = ",".join([str(f) for f in bbox_WSEN])
    with open(run_path / "forcing" / "bbox.txt", "w") as f:
        f.write(bbox_str)

    # now for the templating
    assert template_dir.exists(), f"Could not find the templates folder: {template_dir}"
    fpath_config = run_path / f"{run_name}.xlsx"
    fpath_constants = run_path / "CONSTANTS.xlsx"
    copy_template_file(template_dir / "run_config.xlsx", fpath_config)
    copy_template_file(template_dir / "CONSTANTS.xlsx", fpath_constants)
    copy_template_file(template_dir / "slurm_submit.sh", run_path / "slurm_submit.sh")

    make_run_cryogrid(run_path, template_dir)

    return fpath_config


def make_folder_structure(run_path: Union[str, pathlib.Path]):
    run_path = pathlib.Path(run_path)

    run_path.mkdir(exist_ok=True)
    (run_path / "forcing").mkdir(exist_ok=True)
    (run_path / "output").mkdir(exist_ok=True)
    (run_path / "src/python").mkdir(exist_ok=True, parents=True)
    (run_path / "figures").mkdir(exist_ok=True)


def copy_matplab_custom(run_path):
    import shutil

    import dotenv

    base = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent
    run_path = pathlib.Path(run_path)

    (run_path / "src").mkdir(exist_ok=True, parents=True)

    # copy base/source/matlab/custom to run_path/source/matlab
    custom_matlab_src = base / "src" / "matlab" / "custom/"
    custom_matlab_dst = run_path / "src" / "custom/"
    shutil.copytree(custom_matlab_src, custom_matlab_dst)
    custom_matlab_dst.rename(run_path / "src" / "matlab")


def make_data_for_run(run_path, n_land_classes=3):
    from cryogrid_pytools import excel_config
    from cryogrid_pytools.forcing import era5_to_matlab

    run_path = pathlib.Path(run_path)
    forcing_path = run_path / "forcing"
    run_name = run_path.name

    path_config_xlsx = run_path / f"{run_name}.xlsx"
    path_bbox_txt = forcing_path / "bbox.txt"
    path_era5_mat = forcing_path / "era5.mat"

    bbox = get_bbox(path_bbox_txt)
    bbox = tuple(bbox)  # needs to be a tuple for caching

    config = excel_config.CryoGridConfigExcel(path_config_xlsx, check_file_paths=False)
    times = config.get_start_end_times()

    if not path_era5_mat.exists():
        ds_era5 = get_era5_from_s3_bucket(bbox, times.time_start, times.time_end)
        era5_to_matlab(ds_era5, save_path=str(path_era5_mat))

    ds_geo = get_geospatial_data(bbox, n_land_classes=n_land_classes)
    # save the geospatial data required for the run to forcing folder
    # these names work with the template files
    ds_geo.elevation.rio.to_raster(forcing_path / "elevation.tif")
    ds_geo.surface_classes.rio.to_raster(forcing_path / "surface_classes.tif")
    # save all spatial data to a netcdf file
    ds_geo = make_dataset_netcdf_ready(ds_geo)
    ds_geo.to_netcdf(
        forcing_path / "geospatial_data.nc",
        encoding={k: {"zlib": True} for k in ds_geo.data_vars},
    )

    return path_bbox_txt, path_config_xlsx


def make_forcing_plots(run_path):
    run_path = pathlib.Path(run_path)

    forcing_path = run_path / "forcing"
    path_geospatial_data = forcing_path / "geospatial_data.nc"

    ds_geo = xr.open_dataset(path_geospatial_data)

    fig_geo, axs_geo = plot_geospatial_data(ds_geo)
    html_surf_classes = plot_html_bounds(ds_geo)

    fig_geo.savefig(
        run_path / "figures" / "geospatial_data.png", dpi=300, bbox_inches="tight"
    )
    html_surf_classes.save(run_path / "figures" / "surface_classes.html")

    plt.close("all")


def copy_template_file(src_fname, dst_fname):
    """
    Copy a file from the templates folder to the run folder

    Parameters
    ----------
    src_fname : str
        The name of the file in the templates folder
    dst_fname : str
        The name of the file in the run folder
    """
    from shutil import copyfile

    src_fname = pathlib.Path(src_fname)
    dst_fname = pathlib.Path(dst_fname)

    assert src_fname.exists(), f"Could not find the file {src_fname}"
    assert dst_fname.parent.exists(), (
        f"Could not find the parent folder for {dst_fname}"
    )

    copyfile(src_fname, dst_fname)


def make_run_cryogrid(run_path, template_dir):
    import os

    import jinja2

    env = jinja2.Environment()

    template_fname = pathlib.Path(template_dir) / "run_cryogrid.m"
    run_path = pathlib.Path(run_path)
    run_name = run_path.name
    out_name = run_path / "run_cryogrid.m"

    # get the username of the current user
    username = os.environ.get("USERNAME", "unknown")

    raw_str = open(template_fname).read()
    rendered_str = env.from_string(raw_str).render(run_name=run_name, username=username)

    with open(out_name, "w") as f:
        f.write(rendered_str)

    return out_name


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
    import xarray as xr

    bbox = list(deepcopy(bbox))

    if not dotenv.load_dotenv():
        raise FileNotFoundError("Could not find .env file with S3 credentials")

    fname_era5_s3 = "s3://spi-pamir-c7-sdsc/era5_data/central_asia.zarr/"

    ds_central_asia = xr.open_zarr(
        fname_era5_s3
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


def get_geospatial_data(bbox: tuple, n_land_classes=3) -> xr.Dataset:
    from cryogrid_pytools import data

    from .stratigraphy import calc_surface_classes_3, calc_surface_classes_4

    bbox_str = ", ".join([f"{x:.3f}" for x in bbox])
    logger.info(f"Getting geospatial data for bbox [{bbox_str}]")

    dem = data.get_dem_copernicus30(bbox_WSEN=bbox)
    land_cover = data.get_esa_land_cover(dem)
    glaciers = data.get_randolph_glacier_inventory(dem)

    if n_land_classes == 3:
        ds = calc_surface_classes_3(dem, land_cover, glaciers)
    elif n_land_classes == 4:
        ds = calc_surface_classes_4(dem, land_cover, glaciers)

    return ds


def make_dataset_netcdf_ready(ds):
    import numpy as np

    for key in ds:
        if "spec" in ds[key].attrs:
            ds[key].attrs.pop("spec")
        for attr_key in ds[key].attrs:
            attr = ds[key].attrs[attr_key]
            if isinstance(attr, np.ndarray):
                ds[key].attrs[attr_key] = attr.tolist()
        if key in ds.data_vars:
            ds[key] = ds[key].astype("float32")

    return ds


def plot_geospatial_data(ds: xr.Dataset) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot the stratigraphy classes generated with `calc_simple_surface_classes`

    Args:
        ds (xr.Dataset): Dataset with the variables
        - elevation
        - surface_classes
        - slope, and
        - snow_melt_doy

    Returns:
        tuple[plt.Figure, plt.Axes]: Figure and axes of the plot
    """
    import numpy as np

    n_surface_classes = len(ds.surface_classes.attrs["class_values"])

    aspect = (
        ds.elevation.sizes["x"] / ds.elevation.sizes["y"] * 1.15
    )  # account for colorbar
    w = 11
    h = w / aspect
    fig, axs = plt.subplots(2, 2, figsize=(w, h), sharex=True, sharey=True)
    axs = axs.flatten()

    imgs = []
    imgs += (get_google_scene(ds).plot.imshow(ax=axs[0]),)
    imgs += (
        ds.elevation.plot(ax=axs[1], cmap="terrain", robust=True, add_colorbar=False),
    )
    imgs += (ds.slope.plot(ax=axs[2], robust=True, add_colorbar=False),)
    imgs += (
        ds.surface_classes.plot(
            ax=axs[3],
            cmap="RdYlBu_r",
            levels=np.arange(-0.5, n_surface_classes),
            add_colorbar=False,
        ),
    )

    [ax.set_xlabel("") for ax in axs]
    [ax.set_ylabel("") for ax in axs[1::2]]

    [ax.set_title("") for ax in axs]
    [ax.set_aspect("equal") for ax in axs]

    axs[0].set_title("a) Google Maps RGB", loc="left", x=0.1)
    axs[1].set_title("b) Elevation (Copernicus 30m)", loc="left", x=0.1)
    axs[2].set_title("c) Slope", loc="left", x=0.1)
    axs[3].set_title(f"d) Surface classes (n = {n_surface_classes})", loc="left", x=0.1)

    fig.tight_layout()
    plt.colorbar(
        imgs[1],
        ax=axs[:2],
        label="Elevation [m]",
        pad=0.01,
        location="right",
        fraction=0.05,
    )
    cbar3 = plt.colorbar(
        imgs[3],
        ax=axs[2:],
        label="Surface class",
        pad=0.01,
        location="right",
        fraction=0.05,
    )

    ticks = [float(f) for f in range(n_surface_classes)]
    cbar3.set_ticks(ticks)
    cbar3.set_ticklabels(
        [
            f"{i}) {n}"
            for i, n in zip(
                ds.surface_classes.attrs["class_values"],
                ds.surface_classes.attrs["class_names"],
            )
        ]
    )

    return fig, axs


def get_google_scene(ds):
    from .viz.google_maps_getter import GoogleScene

    bbox = [float(f) for f in ds.elevation.rv.get_bbox_latlon()]
    scene = GoogleScene(bbox)
    da = scene.xr
    da_crs = da.rio.reproject_match(ds.elevation)

    return da_crs


def plot_html_bounds(ds: xr.Dataset):
    """Convert ds.surface_classes to a geopandas.dataframe and use .explore()"""
    import pandas as pd

    from . import viz

    da = ds.surface_classes.astype(int)

    df = da.rv.to_polygons()
    names = pd.Series(da.class_names, index=da.class_values)
    df["names"] = names.loc[df["class"].values.astype(int)].values

    m = df.explore(column="names", name="Surface Classes", cmap="tab20")
    m = viz.folium_helpers.finalize_map(m)

    return m
