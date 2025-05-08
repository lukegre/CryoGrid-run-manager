import xarray as xr


def open_spatial_data(fname_spatial_mat: str, crs: str) -> xr.Dataset:
    """
    Opens run_spatial_info.mat that contains the spatial information for the run

    Parameters
    ----------
    fname_spatial_mat : str
        Path to the run_spatial_info.mat file

    Returns
    -------
    ds : xr.Dataset
        Dataset with the spatial information
    """
    import cryogrid_pytools as cg
    import numpy as np
    import pandas as pd

    print(fname_spatial_mat)
    spatial_dict = cg.read_mat_struct_flat_as_dict(fname_spatial_mat)

    cluster_idx = spatial_dict.pop("cluster_idx")

    df = pd.DataFrame.from_dict(spatial_dict).set_index(["coord_y", "coord_x"])

    ds = df.to_xarray()

    ds["gridcell_flat"] = xr.DataArray(
        data=np.r_[0, cluster_idx],
        coords={"index": np.arange(cluster_idx.size + 1)},
        dims=("index",),
    )

    ds["mask"] = ds["mask"].fillna(0).astype("bool")
    # dtypes to uint32
    for var in ["cluster_num", "stratigraphy_index", "gridcell_flat", "matlab_index"]:
        ds[var] = ds[var].astype("uint32")

    ds["gridcell"] = ds.gridcell_flat.sel(index=ds.cluster_num).astype("uint32")

    ds = ds.rename(coord_x="x", coord_y="y")
    ds = ds.rio.write_crs(crs)

    return ds


def profiles_to_spatial(da: xr.DataArray, gridcells_2D: xr.DataArray) -> xr.DataArray:
    """
    Maps the single depth selection of the profiles to the 2D gridcells

    """

    # make sure profiles_single_depth has gridcell dimension only
    assert list(da.sizes) == ["gridcell"], (
        "da must have gridcell dimension only (i.e., single timestep and depth)"
    )

    if 0 in gridcells_2D:
        dummy0 = xr.DataArray(data=0, dims=("gridcell",), coords=dict(gridcell=[0]))
        da = xr.concat([dummy0, da], dim="gridcell")

    da_2d = da.sel(gridcell=gridcells_2D).where(gridcells_2D != 0)

    return da_2d
