"""Utility functions for the CryoGrid Run Manager."""
import xarray as xr


def drop_coords_without_dim(da: xr.DataArray) -> xr.DataArray:
    """Drop coordinates that do not have a corresponding dimension.

    Parameters
    ----------
    da : xr.DataArray
        Input DataArray from which coordinates without dimensions will be dropped.

    Returns
    -------
    xr.DataArray
        DataArray with coordinates without dimensions removed.

    """
    for c in da.coords:
        if c not in da.dims:
            da = da.drop_vars(c)  # Drop the coordinate if it is not a dimension
    return da


def year_to_time(da: xr.DataArray, offset: str = "175D") -> xr.DataArray:
    """Convert a 'year' coordinate in a DataArray to a 'time' coordinate.

    Parameters
    ----------
    da : xr.DataArray
        Input DataArray with a 'year' coordinate to be converted.
    offset : str, optional
        Offset to add to the converted time coordinate, by default "175D".

    Returns
    -------
    xr.DataArray
        DataArray with the 'year' coordinate renamed to 'time' and converted
        to datetime.

    """
    import pandas as pd

    time = pd.to_datetime(da.year, format="%Y")  # Convert year to datetime
    time_offset = pd.Timedelta(offset)  # Parse the offset

    # Assign new time coordinate
    return da.rename(year="time").assign_coords(time=time + time_offset)
