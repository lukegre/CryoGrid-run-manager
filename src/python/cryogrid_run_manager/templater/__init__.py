from . import (
    clustering,
    data,
    files_n_folders,
    plotting,
)


def new_run(
    run_path, bbox_WSEN, template_dir, config_path_or_url=None, sampling="random"
):
    from cryogrid_pytools import CryoGridConfigExcel

    from .data import make_data_for_run
    from .files_n_folders import make_run_folder_structure
    from .plotting import make_forcing_plots

    fpath_config = make_run_folder_structure(
        run_path, bbox_WSEN, template_dir, config_path_or_url
    )

    fpath_bbox, fpath_config = make_data_for_run(run_path, res_m=100, sampling=sampling)

    make_forcing_plots(run_path)

    CryoGridConfigExcel(fpath_config)

    return fpath_bbox, fpath_config
