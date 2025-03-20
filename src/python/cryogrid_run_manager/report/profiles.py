
import pathlib
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from typing import Union
from functools import lru_cache


@lru_cache
def open_profiles(fname_profiles:str, deepest_point:int)->xr.Dataset:
    from cryogrid_pytools import read_OUT_regridded_FCI2_clusters

    ds = read_OUT_regridded_FCI2_clusters(fname_profiles, deepest_point=deepest_point)
    return ds


def get_profiles_as_gdf(fname_runs, fname_spatial):
    from .profiles import get_successful_profiles, get_profile_locations
    from cryogrid_pytools.viz.folium_helpers import gridpoints_to_geodataframe
    
    successful_profile_ids = get_successful_profiles(fname_runs)
    profile_locs = get_profile_locations(fname_spatial, successful_profile_ids)
    
    df = gridpoints_to_geodataframe(profile_locs)
    
    return df


def get_successful_profiles(fname:str)->np.ndarray:
    from glob import glob
    import re

    flist = glob(fname)
    flist_str = "\n".join(flist)

    pattern = r".*_(\d{1,})_[0-9]{8}.mat.*"
    matches = re.findall(pattern, flist_str)
    
    return np.unique(matches).astype(int)


def get_profile_locations(spatial_info_fname: str, succeeded_runs: Union[list, np.ndarray]=[])->xr.Dataset:
    import cryogrid_pytools as cg

    ds_spatial = cg.read_mat_struct_as_dataset(spatial_info_fname, drop_keys=['cluster_idx'])
    
    runs_failed = np.array(list(set(ds_spatial.cluster_idx.values.tolist()) - set(succeeded_runs)))
    
    points_passed = ds_spatial.sel(index=succeeded_runs).assign(run_status=1.)
    points_failed = ds_spatial.sel(index=runs_failed).assign(run_status=0.)

    points = xr.concat([points_passed, points_failed], dim='index')

    return points


def make_profile_plots(fname_profiles:str, deepest_point:int, fig_dest:str, overwrite=False)->tuple[pathlib.Path, ...]:
    """Creates profile plots for the given profiles file pattern.
    
    Parameters
    ----------
    fname_profiles : str
        The file pattern for the profiles to be plotted. When 
        passed through glob should return <experiment_name>_<index>_<date>.mat files.
    deepest_point : int
        The deepest point in the profile grid
    fig_dest : str
        The destination folder for the figures.

    Returns
    -------
    tuple[str]
        The paths to the generated figures.
    """
    import re
    import pathlib
    import matplotlib.pyplot as plt
    from loguru import logger
    from cryogrid_pytools.viz.profiles import plot_profiles

    path_dest = pathlib.Path(fig_dest)
    path_dest.mkdir(parents=True, exist_ok=True)

    flist = get_flist(fname_profiles, exclude='TDD')
    if len(flist) == 0:
        raise FileNotFoundError(f"No files found with pattern {fname_profiles}")
    fname_fmt = flist[0]
    pattern = r".*_(\d{1,})_([0-9]{8}).mat"
    matches = re.findall(pattern, fname_fmt)[0]
    fname_fmt = fname_fmt.replace(matches[0], "{index}").replace(matches[1], "*")

    indexes = sorted(get_gridcell_id_from_fname(flist))

    paths = []
    for index in indexes:
        fname = fname_fmt.format(index=index)
        sname = path_dest / f"{index}.png"
        if sname.exists() and not overwrite:
            logger.debug(f"Profile plot for {index} already exists. Skipping.")
            continue
        else:
            logger.info(f"Creating profile plot for {index}")
        
        ds = open_profiles(fname, deepest_point)
        fig, axs, imgs = plot_profiles(ds.sel(gridcell=index))

        fig.tight_layout()
        fig.savefig(sname, transparent=True, bbox_inches='tight', dpi=100)
        paths.append(sname)
        logger.info(f"Created profile plot at {sname}")
        
        plt.close(fig)

    return tuple(paths)


def get_flist(fname_glob:str, exclude='TDD')->list[str]:
    from glob import glob

    # get the file list
    flist = glob(fname_glob)
    flist = [f for f in flist if exclude not in f]
    flist = sorted(flist)

    return flist


def get_gridcell_id_from_fname(flist:list[str])->list[int]:
    # extract the gridcell from the file name
    gridcells = [int(f.split('_')[-2]) for f in flist]
    gridcells = list(set(gridcells))
    return gridcells


def is_empty_profile_image(fname:str)->bool:
    import PIL.Image
    import numpy as np

    image = PIL.Image.open(fname)
    arr = np.array(image)

    left_half_rgb = arr[:, :arr.shape[1]//2, :3]
    rgb_unique = np.unique(left_half_rgb)
    
    if rgb_unique.size == 2:
        empty_profile = True
    else:
        empty_profile = False
    
    return empty_profile