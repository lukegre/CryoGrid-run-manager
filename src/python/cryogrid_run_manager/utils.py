"""Utility functions for the CryoGrid Run Manager."""
import os
import re

import xarray as xr

__all__ = [
    "set_logger_level",
    "drop_coords_without_dim",
    "year_to_time", 
    "glob_to_regex",
]


def set_logger_level(level='INFO'):
    """Set the logging level for loguru.logger to the specified level.

    Parameters
    ----------
    level : str, optional
        Logging level to set, by default 'INFO'.

    """
    import loguru

    loguru.logger.remove()  # Remove the default logger
    loguru.logger.add(  # Add a new logger with the specified level
        sink=os.sys.stdout,
        level=level,
    )


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


def glob_to_regex(glob_pattern):
    """
    Convert a glob-like pattern to a full-match regex pattern.
    
    This function converts wildcards:
      - '*' becomes '.*' (unless already part of '.*')
      - '?' becomes '.'
    
    The resulting regex is anchored with ^ and $.
    """
    # Check if the pattern contains a '*' that is not already part of '.*' or a '?'
    if re.search(r'(?<!\.)\*', glob_pattern) or '?' in glob_pattern:
        regex = ""
        i = 0
        while i < len(glob_pattern):
            c = glob_pattern[i]
            if c == '*':
                # If already a regex wildcard ".*", leave it
                if glob_pattern[i:i+2] == '.*':
                    regex += '.*'
                    i += 2
                    continue
                else:
                    regex += '.*'
            elif c == '?':
                regex += '.'
            else:
                # Escape regex special characters
                if c in ".^$+{}[]|()\\":
                    regex += '\\' + c
                else:
                    regex += c
            i += 1
        return '^' + regex + '$'
    else:
        # Assume it's already a regex pattern; anchor it for a full match.
        return '^' + glob_pattern + '$'


def regex_glob(pattern, recursive=True):
    """
    Search for files matching a pattern that may use glob wildcards or regex.
    
    The pattern is given as a single string combining the directory and file pattern.
    For example: "path/name_[0-9]*.mat" or "path/name_?[0-9].mat"
    
    If the file pattern part contains glob wildcards '*' or '?'
    (without the user already specifying the regex version, i.e. '.*'),
    they will be converted to regex-compatible wildcards.
    
    Parameters:
        pattern (str): Combined directory and file pattern.
        recursive (bool): If True, search subdirectories recursively.
    
    Returns:
        list: List of matching file paths.
    """
    directory = os.path.dirname(pattern) or '.'
    file_pattern = os.path.basename(pattern)
    # Convert glob wildcards to regex if necessary.
    file_regex_pattern = glob_to_regex(file_pattern)
    regex = re.compile(file_regex_pattern)
    matches = []

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if regex.fullmatch(file):
                    matches.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isfile(full_path) and regex.fullmatch(file):
                matches.append(full_path)

    matches = sorted(matches)
    
    return matches
