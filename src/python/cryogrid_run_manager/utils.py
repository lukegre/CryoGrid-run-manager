
def drop_coords_without_dim(da):
    """Drop coordinates that do not have a corresponding dimension"""
    for c in da.coords:
        if c not in da.dims:
            da = da.drop_vars(c)
    return da


def year_to_time(da, offset='175D'):
    """Convert year to time coordinate"""
    import xarray as xr
    import pandas as pd

    time = pd.to_datetime(da.year, format='%Y')
    time_offset = pd.Timedelta(offset)
    out = da.rename(year='time').assign_coords(time=time + time_offset)

    return out