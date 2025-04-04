import numpy as np
import xarray as xr
import xrspatial as xrs


def calc_surface_classes_4(
    dem: xr.DataArray, land_cover: xr.DataArray, glaciers: xr.DataArray
) -> xr.Dataset:
    """Compute stratigraphy from a DEM"""

    crs = dem.rio.crs

    slope = xrs.slope(dem)

    snow_ice = land_cover == 70
    snow = ~glaciers & snow_ice

    bare_rock = ((land_cover == 60) | snow) & (slope > 30)
    bare_soil = ((land_cover == 60) | snow) & (slope <= 30)
    grassland = land_cover == 30
    moss_lichen = land_cover == 100

    surf_classes = xr.DataArray(np.ones_like(dem), coords=dem.coords, dims=dem.dims)
    surf_classes = surf_classes.where(~glaciers, 0)
    surf_classes = surf_classes.where(~bare_rock, 1)
    surf_classes = surf_classes.where(~bare_soil, 2)
    surf_classes = surf_classes.where(~grassland, 3)
    surf_classes = surf_classes.where(~moss_lichen, 4)
    surf_classes = surf_classes.where(~glaciers, 0)

    ds = xr.Dataset()
    ds["surface_classes"] = surf_classes.assign_attrs(
        long_name="Surface classes for stratigraphy estimation",
        description="Surface classes for stratigraphy estimation based on land cover and slope",
        class_names=["Glaciers", "Bare Rock", "Bare Soil", "Grassland", "Moss/Lichen"],
        class_values=[0, 1, 2, 3, 4],
        class_descriptions=[
            "Glaciers from Randolph Glacier Inventory",
            "Bare ground from land cover and slope > 30 degrees",
            "Bare ground from land cover and slope <= 30 degrees",
            "Grassland from land cover (vegetated areas)",
            "Moss and lichen from land cover (thin soils or rocky terrain)",
        ],
    )
    ds["elevation"] = dem
    ds["slope"] = slope
    ds["land_cover"] = land_cover
    ds["glaciers"] = glaciers

    ds = ds.astype(float).pipe(drop_coords_without_dim).compute()

    for key in ds.data_vars:
        ds[key] = ds[key].rio.write_crs(crs).rio.set_nodata(0)

    return ds


def calc_surface_classes_3(
    dem: xr.DataArray, land_cover: xr.DataArray, glaciers: xr.DataArray
) -> xr.Dataset:
    """Compute stratigraphy from a DEM"""

    crs = dem.rio.crs

    slope = xrs.slope(dem)

    snow_ice = land_cover == 70
    snow = ~glaciers & snow_ice

    bare_rock = ((land_cover == 60) | snow) & (slope > 30)
    bare_soil = ((land_cover == 60) | snow) & (slope <= 30)
    grassland = land_cover == 30
    moss_lichen = land_cover == 100

    surf_classes = xr.DataArray(np.ones_like(dem), coords=dem.coords, dims=dem.dims)
    surf_classes = surf_classes.where(~glaciers, 0)
    surf_classes = surf_classes.where(~bare_rock, 1)
    surf_classes = surf_classes.where(~bare_soil, 2)
    surf_classes = surf_classes.where(~grassland, 3)
    surf_classes = surf_classes.where(~moss_lichen, 3)
    surf_classes = surf_classes.where(~glaciers, 0)

    ds = xr.Dataset()
    ds["surface_classes"] = surf_classes.assign_attrs(
        long_name="Surface classes for stratigraphy estimation",
        description="Surface classes for stratigraphy estimation based on land cover and slope",
        class_names=["Glaciers", "Bare Rock", "Bare Soil", "Grassland/Moss/Lichen"],
        class_values=[0, 1, 2, 3],
        class_descriptions=[
            "Glaciers from Randolph Glacier Inventory",
            "Bare ground from land cover and slope > 30 degrees",
            "Bare ground from land cover and slope <= 30 degrees",
            "Grassland/Moss/Lichen from land cover (vegetated areas)",
        ],
    )
    ds["elevation"] = dem
    ds["slope"] = slope
    ds["land_cover"] = land_cover
    ds["glaciers"] = glaciers

    ds = ds.astype(float).pipe(drop_coords_without_dim).compute()

    for key in ds.data_vars:
        ds[key] = ds[key].rio.write_crs(crs).rio.set_nodata(0)

    return ds


def drop_coords_without_dim(da):
    """Drop coordinates that do not have a corresponding dimension"""
    for c in da.coords:
        if c not in da.dims:
            da = da.drop_vars(c)
    return da


def plot_stratigraphy_count_in_clusters(fname_spatial_info_mat: str):
    import cryogrid_pytools as cg
    import matplotlib.pyplot as plt
    import pandas as pd

    props = dict(fname=fname_spatial_info_mat, drop_keys=["cluster_idx"])

    ds = cg.read_mat_struct_as_dataset(**props, index=["coord_y", "coord_x"])

    ds_flat = cg.read_mat_struct_as_dataset(**props).assign_coords(
        index=lambda x: x.index + 1
    )

    idx = cg.read_mat_struct_flat_as_dict(fname_spatial_info_mat)["cluster_idx"]
    idx = pd.Series(idx, index=range(1, idx.size + 1))

    fig, axs = plt.subplot_mosaic(
        mosaic=[["a", "b"], ["c", "d"]],
        height_ratios=[3, 2],
        figsize=(12, 9),
        dpi=200,
    )

    props = dict(cbar_kwargs=dict(orientation="horizontal", pad=0.01, aspect=15))
    ds.cluster_num.plot(ax=axs["a"], **props)
    ds.stratigraphy_index.plot(ax=axs["b"], **props)
    # adjusting plots
    [axs[s].set_xlabel("") for s in ("a", "b")]
    [axs[s].set_xticks([]) for s in ("a", "b")]
    props = dict(loc="left", color="0.5", x=0.1)
    axs["a"].set_title(f"a) Cluster number (k={idx.size})", **props)
    axs["b"].set_title("b) Stratigraphy index", **props)
    axs["b"].set_ylabel("")

    data_c = ds_flat.sel(index=idx.values).stratigraphy_index.to_series().value_counts()
    data_c.plot.bar(width=0.8, ax=axs["c"])
    # adjusting plot
    axs["c"].set_title(
        f"c) Stratigraphy class dist. in clusters (k={idx.size})",
        loc="left",
        color="0.5",
    )
    axs["c"].set_ylabel("Number of cluster centroids")
    axs["c"].set_xlabel("Stratigraphy index")
    axs["c"].set_xticklabels(axs["c"].get_xticklabels(), rotation=0)
    axs["c"].spines["top"].set_visible(False)
    axs["c"].spines["right"].set_visible(False)

    axs["d"].set_visible(False)

    return fig, axs
