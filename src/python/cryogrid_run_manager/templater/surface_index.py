from typing import Union

import numpy as np
import xarray as xr
import xrspatial as xrs
from cryogrid_pytools.data.utils import _decorator_dataarray_to_bbox
from cryogrid_pytools.utils import drop_coords_without_dim as _drop_coords_without_dim
from loguru import logger


def calc_bedrock_soil_masks(
    slope: xr.DataArray,
    land_cover: xr.DataArray,
    slope_threshold=30,
    land_cover_bare_soil_values=(8,),
) -> tuple[xr.DataArray, xr.DataArray]:
    """
    Compute surface classes based on slope and land cover.
    This function computes two surface classes: bedrock and bare soil.

    Parameters
    ----------
    slope : xr.DataArray
        Slope in degrees calculated from the DEM using xrspatial.slope
    land_cover : xr.DataArray
        Land cover data on the same grid as the DEM
    slope_threshold : float, optional
        Slope threshold to classify the surface, by default 30
    land_cover_bare_soil_values : tuple, optional
        Value representing bare soil in the land cover data, by default (60)
        based on the ESA land cover classification scheme.
        For the ESRI annual product based on Sentinel-2 this value is (8)

    Returns
    -------
    tuple[xr.DataArray, xr.DataArray]
        Two boolean arrays indicating bedrock and bare soil areas.
    """

    steep = slope > slope_threshold
    bare = land_cover.isin(land_cover_bare_soil_values)

    bedrock = steep & bare
    soil = ~steep & bare

    bedrock = (
        bedrock.rename("bedrock")
        .pipe(_drop_coords_without_dim)
        .rio.set_nodata(0)
        .assign_attrs(
            long_name="Bedrock mask",
            description=(
                f"Bedrock mask based on slope (> {slope_threshold}) "
                f"and Bare rock/soil from {land_cover.long_name}"
            ),
        )
    )

    soil = (
        soil.rename("bare_soil")
        .pipe(_drop_coords_without_dim)
        .rio.set_nodata(0)
        .assign_attrs(
            long_name="Bare soil mask",
            description=(
                f"Bare soil mask based on slope (<= {slope_threshold}) "
                f"and Bare rock/soil from {land_cover.long_name}"
            ),
        )
    )

    return bedrock, soil


def calc_vegetation_mask(
    land_cover: xr.DataArray,
    vegetation_values=(11,),
) -> xr.DataArray:
    """
    Compute a vegetation mask based on land cover data - note only
    where permafrost is possible in mountainous areas.

    Parameters
    ----------
    land_cover : xr.DataArray
        Land cover data on the same grid as the DEM
    vegetation_values : tuple, optional
        Values representing vegetation in the land cover data, by default (30, 100)
        based on the ESA land cover classification scheme (grass and mosses).
        For the ESRI annual product based on Sentinel-2 this value is (11,) rangelands

    Returns
    -------
    xr.DataArray
        A boolean array indicating vegetation areas.
    """

    vegetation = land_cover.isin(vegetation_values)
    vegetation = (
        vegetation.pipe(_drop_coords_without_dim)
        .rename("vegetation")
        .assign_attrs(
            long_name="Vegetation mask",
            description=(
                "Vegetation mask based on land cover (grassland and moss/lichen)"
            ),
        )
    )

    return vegetation


def calc_masked_land_types(
    land_cover: xr.DataArray,
    glacier_mask: xr.DataArray,
    land_cover_masked_values=(0, 1, 2, 4, 5, 7),
) -> xr.DataArray:
    """
    Compute a mask for land cover types that are not suitable for
    permafrost modeling, such as glaciers and certain land cover types.

    For large-scale mountain permafrost modelling, I exclude:
        - permanent snow and ice
        - glaciers
        - water bodies and flooded areas
        - croplands and trees
        - build up areas

    Parameters
    ----------
    land_cover : xr.DataArray
        Land cover data on the same grid as the DEM
    glacier_mask : xr.DataArray
        Glacier mask (e.g. from Randolph Glacier Inventory)
    land_cover_masked_values : tuple, optional
        Values representing land cover types to be masked, by default (70,)
        for ESA land cover: (10, 40, 50, 70, 80, 90, 95)
        for ESRI LULC: (0, 1, 2, 4, 5, 7)
    """

    land_cover_name = land_cover.attrs.get("long_name", land_cover.name)
    glacier_name = glacier_mask.attrs.get("long_name", glacier_mask.name)

    land_cover_mask = land_cover.isin(land_cover_masked_values)
    masked = (
        (glacier_mask | land_cover_mask)
        .pipe(_drop_coords_without_dim)
        .rename("masked_values")
        .rio.set_nodata(0)
        .assign_attrs(
            long_name="Masked areas",
            masked_land_type_values=land_cover_masked_values,
            description=(
                f"Land cover mask based on `{land_cover_name}` and `{glacier_name}`. "
                "These masked values will not be run in the CryoGrid model"
            ),
        )
    )

    return masked


def calc_surface_index(
    dem: xr.DataArray,
    land_cover: xr.DataArray,
    glaciers: xr.DataArray,
    rock_glaciers: xr.DataArray,
    land_cover_vegetation_values=(11,),
    land_cover_bare_soil_values=(8,),
    land_cover_masked_values=(0, 1, 2, 4, 5, 7),
) -> xr.DataArray:
    """
    Compute stratigraphy from a DEM
    """
    from collections import defaultdict

    slope = xrs.slope(dem)

    masked_land_types = calc_masked_land_types(
        land_cover=land_cover,
        glacier_mask=glaciers,
        land_cover_masked_values=land_cover_masked_values,
    )

    bedrock, bare_soil = calc_bedrock_soil_masks(
        slope=slope,
        land_cover=land_cover,
        slope_threshold=30,
        land_cover_bare_soil_values=land_cover_bare_soil_values,
    )

    vegetated = calc_vegetation_mask(
        land_cover=land_cover, vegetation_values=land_cover_vegetation_values
    )

    mask_values = {
        1: bedrock,
        3: bare_soil,
        4: vegetated,
        2: rock_glaciers,
        0: masked_land_types,
    }

    # pre-define the surface classes as ones
    strat_index = xr.DataArray(
        data=np.zeros_like(dem) * np.nan,
        coords={k: dem.coords[k] for k in dem.dims},
        dims=dem.dims,
        attrs={
            "long_name": "Surface index",
            "description": "Surface index based on land cover and slope",
        },
    )

    attrs = defaultdict(list)
    for value, mask in mask_values.items():
        strat_index = strat_index.where(~mask, value)

        attrs["index_values"] += (value,)
        attrs["index_names"] += (mask.attrs.get("long_name", mask.name),)
        attrs["index_descriptions"] += (mask.attrs.get("description", ""),)

    strat_index.attrs.update(attrs)

    # fill in the gaps using stepwise nearest neighbour filling
    strat_index = stepwise_nearest_neighbour_filling(strat_index)

    return strat_index


def stepwise_nearest_neighbour_filling(da: xr.DataArray, max_iter=5):
    """
    Fill NaN values in a DataArray using nearest neighbour filling.

    This has to be done in a stepwise manner since interpolate_na doesn't always
    work on data where the x, y dimensions aren't monotonically increasing.
    Thus, we first bfill/ffill in the y/x directions always with a limit of 1.

    Parameters
    ----------
    da : xarray.DataArray
        The input data as an xarray DataArray.
    max_iter : int, optional
        The maximum number of iterations to fill NaN values, by default 5
        Will log a warning if not all NaN values are filled after this many iterations.

    Returns
    -------
    xarray.DataArray
        The filled data as an xarray DataArray.
    """
    if not da.isnull().any():
        return da.astype(np.uint8)
    else:
        logger.debug(
            f"Filling NaN values in {da.name} using stepwise nearest neighbour filling."
        )

    n_iters = 0
    while da.isnull().any() and n_iters < max_iter:
        da = (
            da.bfill(dim="y", limit=1)
            .ffill(dim="y", limit=1)
            .bfill(dim="x", limit=1)
            .ffill(dim="x", limit=1)
        )
        n_iters += 1

    if da.isnull().any():
        logger.warning(
            "Stepwise nearest neighbour filling did not fill all "
            f"NaN values in {da.name} after {max_iter} iterations."
        )

    da = (
        da.astype(np.uint8)
        .rename("surface_classes")
        .assign_attrs(
            history=(
                da.attrs.get("history", "") + f"stepwise_nearest_neighbour_filling "
                f"completed after {n_iters} iterations; "
            )
        )
    )

    return da


def exchage_values(
    da: xr.DataArray,
    values_to_change: dict[Union[int, float], Union[int, float]],
) -> xr.DataArray:
    """
    Exchange values in a DataArray based on a dictionary of values to change.

    Parameters
    ----------
    da : xarray.DataArray
        The input data as an xarray DataArray.
    values_to_change : dict
        A dictionary where the keys are the values to change and the values are the new values.
        The keys and values must be of the same type (int or float).
        The keys must be unique and not present in the original data.

    Returns
    -------
    xarray.DataArray
        The modified data as an xarray DataArray.

    Raises
    ------
        ValueError if the DataArray is not of integer type or has more than 100 unique values.
    """

    unique_vals = np.unique(da.values)
    n_unique_vals = unique_vals.size
    n_new_vals = len(values_to_change)

    if ("int" not in str(da.dtype)) and (n_unique_vals > 100):
        raise ValueError(
            "The DataArray must be of integer type, or have less than 100 unique values. "
            "Please check the input data."
        )

    # in order to avoid overwriting the original data, we need to create an overlap
    # between the original and new values. This is done by adding an offset to the new values
    offset = max(unique_vals) + 1
    da_offset = da + offset

    # then we need to adjust our values_to_change to account for the offset
    adjusted_values_to_change = {}
    # we loop through the values in the dataset rather than in the given dictionary
    # so that all values are accounted for - slower but safer
    for val in unique_vals:
        # create a new key with the offset
        source_value = val + offset
        # if the value needs to be changed, then use the user-defined value
        # otherwise, use the original value without the offset
        if val in values_to_change:
            target_value = values_to_change[val]
        else:
            target_value = val
        # add the new key to the dictionary
        adjusted_values_to_change[source_value] = target_value

    # we create a new array to avoid overwriting the original data
    for old_val, new_val in adjusted_values_to_change.items():
        da_offset = da_offset.where(da_offset != old_val, new_val)

    da_out = da_offset.assign_attrs(
        history=da.attrs.get("history", "") + f"exchanged values {values_to_change}; "
    )

    return da_out


def get_ground_info_table(
    excel_config_fname: str,
    sheet_name=1,
    sampling="random",
    grouping_col="surface_index",
):
    """
    Assumes that the second tab in the excel file contains some info about the ground classes.
    Sampling from each group is random if not defined.

    The table has the following columns

    | surface_class | stratigraphy_index | roughness_length | ... |
    | ------------- | ------------------ | ---------------- | --- |
    | 1             | 1                  | 0.05             |     |
    | 1             | 2                  | 0.03             |     |
    | 2             | 1                  | 0.03             |     |


    Parameters
    ----------
    excel_config_fname : str
        Path to the excel file containing the ground information.
    sheet_name : str or int, optional
        The name or index of the sheet to read, by default 1 (the second sheet)
    sampling : str or int, optional
        The sampling method to use. If 'random', a random sample is taken from each group.
        If an integer is provided, it specifies the index of the sample to take from each group.
        If the index is larger than the number of samples in the group, it will wrap around.
    grouping_col : str, optional
        The column name to group by, by default 'surface_index' - i.e., the column that
        defines the spatial index of which the stratigraphy_index and roughness_length are
        members, and are sampled from.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the sampled values for each surface index.
    """
    import pandas as pd

    df = pd.read_excel(excel_config_fname, sheet_name=sheet_name, skiprows=2)
    key = df.columns[0]  # first column is the key

    grouped = (
        df.groupby(grouping_col)[  # multiple strat_idx for each surface_index
            key
        ]  # use one of roughness_length or stratigraphy_index
    )

    if sampling == "random":
        idx = grouped.sample(1, random_state=0)
    elif isinstance(sampling, int):
        i = sampling
        idx = [int(g.index[i % g.size]) for k, g in grouped]

    df = (
        df.loc[idx].set_index(grouping_col).copy(deep=True)
    )  # copy the dataframe so that we can modify it

    return df
