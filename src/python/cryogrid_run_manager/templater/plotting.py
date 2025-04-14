import pathlib
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from loguru import logger


def make_forcing_plots(run_path):
    run_path = pathlib.Path(run_path)

    forcing_path = run_path / "forcing"
    path_geospatial_data = forcing_path / "geospatial_data.nc"

    ds_geo = xr.open_dataset(path_geospatial_data)
    ds_geo = ds_geo.set_coords("spatial_ref")

    fig_geo, _ = plot_geospatial_data(ds_geo)
    fig_geo.savefig(
        run_path / "figures" / "geospatial_data.png", dpi=300, bbox_inches="tight"
    )

    html_surf_classes = plot_html_bounds(ds_geo)
    html_surf_classes.save(run_path / "figures" / "surface_classes.html")

    plt.close("all")


def plot_geospatial_data(ds: xr.Dataset):
    plot_props = dict(
        google_earth_image=dict(long_name="RGB Image (Google Earth)"),
        elevation=dict(long_name="DEM (Copernicus 30m)", cmap="terrain"),
        slope=dict(long_name="Slope from DEM", cmap="viridis", vmin=0.00, vmax=50.0),
        snow_index=dict(long_name="Snow melt DOY (Sentinel-2)", cmap="pink"),
        albedo=dict(
            long_name="Albedo (MODIS black-sky)", cmap="bone", vmin=0.10, vmax=0.40
        ),
        emissivity=dict(
            long_name="Emissivity (ASTER 8-11µm)", cmap="Grays_r", vmin=0.94, vmax=0.98
        ),
        stratigraphy_index=dict(
            long_name="Stratigraphy index (ESRI)",
            cmap="turbo",
            vmin=-0.5,
            vmax=10.5,
            levels=12,
        ),
        roughness_length=dict(
            long_name="Roughness length (literature)",
            cmap="Greens",
            vmin=0.00,
            vmax=0.05,
        ),
        esri_land_cover=dict(
            long_name="Land cover (ESRI)",
            cmap="Spectral_r",
            vmin=0.5,
            vmax=11.5,
            levels=12,
        ),
    )

    data_arrays_for_plotting = [
        get_google_scene(ds).assign_attrs(plot_props["google_earth_image"])
    ]
    for k in plot_props.keys():
        if k in ds.data_vars:
            data_arrays_for_plotting.append(ds[k].assign_attrs(plot_props[k]))

    fig, axs, imgs = plot_dataarrays(data_arrays_for_plotting)

    bbox = ", ".join([f"{c:.3f}" for c in ds.elevation.attrs.get("bbox_request")])
    title = f"Geospatial data for bounding box [{bbox}]"
    fig.suptitle(title, y=1.02, fontsize=14, fontweight="bold")

    return fig, axs


def plot_dataarrays(
    ds: Union[dict, xr.Dataset, list[xr.DataArray]],
    n_cols=3,
    fig_width=10,
    aspect_multiplier=0.8,
) -> tuple[plt.Figure, list[plt.Axes], list]:
    """
    Plot multiple DataArrays in a grid layout using plt.imshow

    Parameters
    ----------
    ds : dict or xr.Dataset or list of xr.DataArray
        Dictionary or xarray Dataset containing DataArrays to be plotted.
        Use a dictionary or list of xr.DataArrays if the DataArrays do not
        have the same x, y dimensions (e.g. different resolutions).
        You can add attributes to the DataArrays to customize the plot.
        These include: cmap, vmin, vmax, cbar_kwargs, norm, levels, alpha.
    n_cols : int, optional
        Number of columns in the grid layout. Default is 3.
    fig_width : float, optional
        Width of the figure in inches. Default is 11.
    aspect_multiplier : float, optional
        Multiplier for the aspect ratio of the figure. Default is 1.

    Returns
    -------
    fig : plt.Figure
        The figure object containing the subplots.
    axs : list of plt.Axes
        List of axes objects for each subplot.
    imgs : list of plt.Image
        List of image objects for each subplot.
    """
    n_rows = len(ds) // n_cols + (len(ds) % n_cols > 0)

    if isinstance(ds, (list, tuple)):
        ds = {k: v for k, v in enumerate(ds)}

    da0 = ds[list(ds)[-1]]
    aspect = da0.sizes["x"] / da0.sizes["y"] * aspect_multiplier  # account for colorbar
    w = fig_width
    h = w / aspect

    fig, axs = plt.subplots(n_rows, n_cols, figsize=(w, h), sharex=True, sharey=True)
    axs = axs.flatten()
    fig.subplots_adjust(hspace=0.3)

    props = dict(
        robust=True,
        cbar_kwargs=dict(location="bottom", pad=0.02, fraction=0.1, label=""),
    )

    plot_attrs = ("cmap", "vmin", "vmax", "cbar_kwargs", "norm", "levels", "alpha")
    imgs = []
    for i, key in enumerate(ds):
        da = ds[key]
        ax = axs[i]
        if da.ndim == 3:
            kwargs = {}
        elif da.ndim == 2:
            kwargs = props | {k: da.attrs.get(k) for k in plot_attrs if k in da.attrs}
        imgs += (da.plot.imshow(ax=ax, **kwargs),)

        if imgs[-1].colorbar is not None:
            imgs[-1].colorbar.ax.xaxis.set_tick_params(length=3, pad=2)

        # if levels are set, shift the ticks to the middle of the levels - only when level sizes = 1
        if "levels" in kwargs and ((kwargs.get("vmin", 0) % 1) == 0.5):
            v0 = float(kwargs.get("vmin"))
            v1 = float(max(da.max(), kwargs.get("vmax", -np.inf)))

            # get the tick values
            ticks = np.array(imgs[-1].colorbar.get_ticks())
            ticks += v0 % 1  # shift the ticks by the fraction remainder
            # remove ticks outside the vmin/vmax range
            ticks = ticks[(ticks >= v0) & (ticks <= v1)]
            imgs[-1].colorbar.set_ticks(ticks)
            imgs[-1].colorbar.ax.xaxis.set_tick_params(length=0, pad=5)
            imgs[-1].colorbar.ax.set_xticks([], minor=True)

        [getattr(ax, m)("") for m in ("set_xlabel", "set_ylabel", "set_title")]
        [getattr(ax, m)([]) for m in ("set_xticks", "set_yticks")]

        ax.set_title(da.attrs.get("long_name", da.name), loc="left")
        ax.set_aspect("equal")

    fig.tight_layout()

    p0 = axs[0].get_position()
    p1 = axs[1].get_position()
    p3 = axs[3].get_position()

    axs[0].set_position([p0.x0, p1.y0, p3.width, p1.height])

    if i < len(axs) - 1:
        for ax in axs[i + 1 :]:
            ax.set_visible(False)

    return fig, axs, imgs


def get_google_scene(ds):
    from ..viz.google_maps_getter import GoogleScene

    if isinstance(ds, xr.Dataset):
        da = ds[list(ds.data_vars)[0]]
    elif isinstance(ds, xr.DataArray):
        da = ds
    else:
        raise ValueError("ds must be an xarray Dataset or DataArray")

    bbox = tuple([float(f) for f in da.rv.get_bbox_latlon()])
    scene = GoogleScene(bbox)
    da = scene.xr
    da_crs = da.rio.reproject(dst_crs=ds.rio.crs)

    return da_crs


def plot_html_bounds(ds: xr.Dataset):
    """Convert ds.surface_classes to a geopandas.dataframe and use .explore()"""
    import pandas as pd

    from .. import viz

    da = ds.stratigraphy_index.astype(int).rio.write_crs(ds.rio.crs)

    df = da.rv.to_polygons()

    m = df.explore(column="class", name="Stratigraphy index", cmap="tab20")
    m = viz.folium_helpers.finalize_map(m)

    return m
