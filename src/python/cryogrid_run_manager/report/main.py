import pathlib
import warnings

import folium
from loguru import logger


def create_report(dirname_experiment, dirname_profiles='{dirname_experiment}/output/', fname_report=None, with_profile_plots=True):
    from .excel import get_excel_config, get_max_depth
    from .profiles import make_profile_plots

    dirname_experiment = pathlib.Path(dirname_experiment).resolve()
    dirname_profiles = pathlib.Path(dirname_profiles.format(str(dirname_experiment)))
    if fname_report is None:
        experiment_name = dirname_experiment.name
        fname_report = dirname_experiment / f"figures/report-{experiment_name}.html"

    fname_excel = str(dirname_experiment / f"{dirname_experiment.name}.xlsx")
    config = get_excel_config(fname_excel)

    last_run = config.get_start_end_times().time_end

    fname_spatial = dirname_profiles / "run_spatial_info.mat"
    fname_profiles_last = str(dirname_profiles / f"*_*_{last_run:%Y%m%d}.mat")
    fname_profiles_all = str(dirname_profiles / ".*_[0-9]{1,}_[0-9]{8}.mat")
    fname_dem = config.get_dem_path()
    
    fpath_figures = dirname_experiment / "figures/profiles"

    if with_profile_plots:
        deepest_point = get_max_depth(fname_excel)
        logger.info(f"Deepest point: {deepest_point}")
        make_profile_plots(
            fname_profiles_all,
            deepest_point=-deepest_point,
            fig_dest=str(fpath_figures),
            overwrite=False,
        )
        fpath_figures = fpath_figures.relative_to(fname_report.parent)
    else:
        fpath_figures = None

    crs = get_crs_from_dem(fname_dem)

    m = make_interactive_map(
        fname_spatial=fname_spatial,
        crs=crs,
        fname_profiles=fname_profiles_last,
        fname_excel=fname_excel,
        profile_figure_path=fpath_figures,
    )

    logger.info(f"Saving report to {fname_report.resolve()}")
    m.save(fname_report)


def get_crs_from_dem(fname_dem):
    import rasterio

    with rasterio.open(fname_dem) as src:
        crs = src.crs.to_string()

    return crs


def make_interactive_map(
    fname_spatial, crs, fname_profiles=None, fname_excel=None, profile_figure_path=None
):
    from cryogrid_pytools.viz.folium_helpers import (
        TILES,
        make_tiles,
        plot_map,
        spatial_discrete_to_polyons,
    )

    from .. import spatial
    from .excel import get_stratigraphy_info
    from .profiles import get_profiles_as_gdf, is_empty_profile_image

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        logger.info(f"Reading spatial data: {fname_spatial}")
        ds_spatial_2d = spatial.open_spatial_data(fname_spatial, crs)

    logger.info("Creating interactive map")

    tile_layers = ["OpenStreetMap", "Google Terrain", "Esri Satellite"]
    tiles = [tile for tile in TILES if tile["name"] in tile_layers]
    m = make_tiles(tiles=tiles)

    logger.info("Adding stratigraphy to map")
    df = spatial_discrete_to_polyons(ds_spatial_2d.stratigraphy_index)
    name = df.columns[-1]
    if fname_excel is not None:
        strat_info = get_stratigraphy_info(fname_excel)
        df = df.set_index(name)
        df = df.join(strat_info).reset_index()
    df.explore(m=m, column=name, name=name)

    continuous_cmaps = {
        "elevation": "terrain",
        "slope_angle": "viridis",
        "aspect": "twilight",
        "skyview_factor": "cividis",
        "cluster_num": "Spectral_r",
    }

    for key in continuous_cmaps:
        logger.info(f"Adding {key} to map")
        m = plot_map(ds_spatial_2d[key], m=m, cmap=continuous_cmaps[key])

    if fname_profiles is not None:
        logger.info("Adding profile locations to map")
        df = get_profiles_as_gdf(fname_profiles, fname_spatial)
        if profile_figure_path is not None:
            df["image"] = df.index.map(
                lambda x: f"<img src='{profile_figure_path}/{x}.png' width=800>"
            )
            for row in df.index:
                fname = "figures/" + str(df.loc[row, "image"]).split("'")[1]
                if not pathlib.Path(fname).exists():
                    continue
                df.loc[row, "run_status"] = 0.5 if is_empty_profile_image(fname) else 1
        m = add_profiles_to_map(df, m=m)

    folium.LayerControl(collapsed=False).add_to(m)

    return m


def add_profiles_to_map(df, m=None):
    from cryogrid_pytools.viz import MARKER_STYLES as marker_styles
    from cryogrid_pytools.viz import make_tiles
    from cryogrid_pytools.viz.folium_helpers import (
        plot_geodataframe_with_image_popups as plot_gdf,
    )

    status = df.run_status

    df_success = df[status == 1]
    df_empty = df[status == 0.5]
    df_failed = df[status == 0]

    if m is None:
        m = make_tiles()
    n_success = len(df_success)
    n_empty = len(df_empty)
    n_failed = len(df_failed)

    m = plot_gdf(
        df_success,
        m=m,
        name=f"Profiles: success ({n_success})",
        **marker_styles.blue_circle["style_kwds"],
    )
    m = plot_gdf(
        df_empty,
        m=m,
        name=f"Profiles: empty ({n_empty})",
        **marker_styles.orange_circle["style_kwds"],
    )
    m = plot_gdf(
        df_failed,
        m=m,
        name=f"Profiles: failed ({n_failed})",
        **marker_styles.red_circle["style_kwds"],
    )

    return m
