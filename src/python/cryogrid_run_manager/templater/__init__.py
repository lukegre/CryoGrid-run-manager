import pathlib

import dotenv

from . import (
    clustering,
    data,
    files_n_folders,
    plotting,
)

BASE = pathlib.Path(dotenv.find_dotenv()).parent


def new_cluster_run(
    bbox_WSEN,
    config_path_or_url=None,
    run_name="{id}-{bbox_str}-smpl{sampling}",
    sampling="random",
    runs_dir=BASE / "runs",
    template_dir=BASE / "templates",
    **kwargs,
):
    from cryogrid_pytools import CryoGridConfigExcel

    from .data import make_data_for_cluster_run
    from .files_n_folders import make_run_folder_structure
    from .plotting import make_forcing_plots

    # bbox_str used to create the run_path (part of locals())
    bbox_str = "".join(
        [f"{coord * 100:.0f}{cardinal}" for coord, cardinal in zip(bbox_WSEN, "wsen")]
    )

    run_path = runs_dir / run_name.format(**locals(), **kwargs)  # uses kwargs too

    fpath_config = make_run_folder_structure(
        run_path, template_dir, config_path_or_url, bbox_WSEN
    )

    fpath_bbox, fpath_config = make_data_for_cluster_run(
        run_path, res_m=30, sampling=sampling
    )

    make_forcing_plots(run_path)

    CryoGridConfigExcel(fpath_config)

    return fpath_bbox, fpath_config


def make_new_ensemble_run(
    run_name, era5_mat_source=BASE / "data/era5-cryogrid-pamirs-1990_2023.mat"
):
    url = "https://docs.google.com/spreadsheets/d/1UCGnO6GmiPtC1jj4s0W8EZiBeaTexZQka5oTU5Xi7JA"

    files_n_folders.make_run_folder_structure(
        run_path=BASE / f"runs/{run_name}",
        template_dir=BASE / "templates/ensemble/",
        config_path_or_url=url,
    )

    era5_dest = pathlib.Path(BASE / f"runs/{run_name}/forcing/era5.mat")
    era5_dest.hardlink_to(era5_mat_source)
