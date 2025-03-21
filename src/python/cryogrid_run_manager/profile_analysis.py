import numpy as np
import xarray as xr


def get_profile_properties(profile: xr.DataArray) -> xr.Dataset:
    """ """

    bottom_thawing = detect_bottom_thawing(profile)
    active_layer = detect_active_layer(profile)

    depth = profile.depth

    ds = xr.Dataset()

    # bollean masks
    ds["bottom_thawing_mask"] = bottom_thawing
    ds["active_layer_mask"] = active_layer.sel(year=ds.time.dt.year)
    ds["permafrost_mask"] = ~ds.active_layer_mask & ~ds.bottom_thawing_mask
    ds["permafrost_state"] = (
        ds.permafrost_mask.astype(int) * 1
        + ds.active_layer_mask.astype(int) * 2
        + bottom_thawing.astype(int) * 3
    )

    # derived varaibles
    ds["active_layer_depth"] = detect_active_layer_depth(active_layer)
    ds["bottom_thawing_depth"] = detect_active_layer_depth(
        ~bottom_thawing.groupby("time.year").max()
    ).where(lambda x: x != 0)
    ds["permafrost_thickness"] = ds.active_layer_depth - ds.bottom_thawing_depth.fillna(
        depth.min()
    )

    # layer statistics
    ds["active_layer_temp"] = profile.where(ds.active_layer_mask).pipe(get_annual_stats)
    ds["permafrost_temp"] = profile.where(ds.permafrost_mask).pipe(get_annual_stats)

    return ds


def get_annual_stats(profile, **describe_kwargs):
    def get_group_stats_describe(group):
        from .utils import drop_coords_without_dim

        da = drop_coords_without_dim(group)
        name = da.name

        df = da.to_dataframe()

        stats = (
            df[name]
            .describe(**describe_kwargs)
            .to_xarray()
            .drop_sel(index=["count"])
            .rename({"index": "stat"})
        )

        return stats

    da = profile.groupby("time.year").apply(get_group_stats_describe)
    return da


def get_ground_only(profile: xr.DataArray) -> xr.DataArray:
    da = profile.sortby("depth").sel(depth=slice(-np.inf, 0))
    da = da.dropna("depth", how="all")
    return da


def detect_upper_thaw_layer(ground_temperature: xr.DataArray) -> xr.DataArray:
    """
    Identify the active layer in the ground temperature profile

    The active layer is defined as the layer above the permafrost that thaws
    every year. The active layer is identified as the layer with positive
    temperature that is not thawed from below (see detect_bottom_thawing).

    Parameters
    ----------
    ground_temperature : xr.DataArray
        Ground temperature profile

    Returns
    -------
    xr.DataArray
        True if active layer, False otherwise
    """
    da = ground_temperature.pipe(get_ground_only)

    bottom_thawing = detect_bottom_thawing(ground_temperature)
    active_layer = (da > 0).astype(int) & ~bottom_thawing

    return active_layer


def detect_active_layer(ground_temperature: xr.DataArray) -> xr.DataArray:
    """
    Identify the depth of the active layer in the ground temperature profile

    The active layer depth is the maximum thaw depth for each season.
    When no active layer is detected, the depth is set to 0.

    Parameters
    ----------
    ground_temperature : xr.DataArray
        Ground temperature profile

    Returns
    -------
    xr.DataArray
        Depth of the active layer (m) reported for each year
    """
    da = ground_temperature.pipe(get_ground_only)

    # get active layer by removing bottom thawing and negative temperatures
    thawed = detect_upper_thaw_layer(da)  # depth x time (hours)
    # detect the maximum temperature in the active layer for each year
    max_temp_annual = thawed.groupby("time.year").max()  # depth x year
    depth = max_temp_annual.depth

    active_layer_depth = (
        depth.where(max_temp_annual)  # broadcast depth to thawed_annual
        .pipe(lambda x: x * 0 + 1)
        .ffill("depth")
        .fillna(0)
        .astype(bool)
    )

    return active_layer_depth


def detect_active_layer_depth(active_layer_mask: xr.DataArray) -> xr.DataArray:
    depth = active_layer_mask.depth

    active_layer_depth = (
        depth.where(active_layer_mask)
        .fillna(0)  # fill with 0 where thawed_annual is False
        .idxmin("depth")  # get the deepest thawed layer
        .where(
            lambda x: x != depth.min()
        )  # if the deepest thawed layer is max depth, then no active layer
        .fillna(0)  # fill with 0 where there is no active layer
    )

    return active_layer_depth


def detect_bottom_thawing(
    ground_temperature: xr.DataArray, min_frozen_frac=0, upper_limit=-5
) -> xr.DataArray:
    """
    Identify if the saved profile is thawing from below

    This approach approach assumes no thawing if max depth temperature is above 0
    There must also be a frozen layer above the thawing layer

    Parameters
    ----------
    ground_temperature : xr.DataArray
        Ground temperature profile
    min_frozen_frac : float, optional
        Minimum fraction of the profile that must be frozen to be
        considererd thawing from below, by default 0.25

    Returns
    -------
    xr.DataArray
        True if thawing from below, False otherwise
    """

    da = ground_temperature.pipe(get_ground_only)

    frozen = (da <= 0).astype(int)
    frozen_limit = frozen.sel(depth=slice(None, upper_limit))
    frac_frozen = frozen_limit.sum("depth") / len(frozen_limit.depth)
    groups = (  # a new group is defined each time the temperature crosses 0 (+ve or -ve)
        frozen.diff(dim="depth")  # compute where the freezing starts and ends
        .pipe(np.abs)  # copmute the absolute value so that thaw is also +1
        .cumsum("depth")
    )

    bottom_thawing = (
        (frozen == 0)  # only if the bottom layer is not frozen
        & (groups == 0)  # only if it is the first layer (from the bottom)
        & (frac_frozen > min_frozen_frac)  # only if a frac of the profile is frozen
        # avoids making warm profiles "thawing from below"
    )

    return bottom_thawing
