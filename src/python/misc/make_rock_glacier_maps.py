import geopandas as gpd
import dotenv
import pathlib

# Define the base directory using the location of the pyproject.toml file
base = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent


def main(sname=None):
    """
    Main function to generate and optionally save an interactive map of rock glaciers.

    This function retrieves TPRoGI (The Permafrost Region of the Globe Inventory) data,
    creates an interactive map using Folium, and optionally saves the map to a specified
    file path.

    Parameters
    ----------
    sname : str, optional
        The file path where the generated map should be saved. If None, the map is returned
        as a Folium map object.

    Returns
    -------
    pathlib.Path or folium.Map
        If `sname` is provided, returns the absolute path to the saved map file as a `pathlib.Path` object.
        Otherwise, returns the generated Folium map object.

    Notes
    -----
    - The map includes a label with a clickable link to the TPRoGI dataset.
    - The TPRoGI dataset is attributed to Zhangyu et al., 2024.

    Examples
    --------
    >>> main("output_map.html")
    PosixPath('/absolute/path/to/output_map.html')
    """
    import pathlib

    # Retrieve the TPRoGI dataset
    df = get_TPRoGI_data()

    # Define the dataset name and link
    name = "TPRoGI (Zhangyu et al., 2024)"
    link = "https://zenodo.org/records/10732042"
    label = f'<a href="{link}" target="_blank"><h3>{name}</h3></a>'

    # Generate the interactive map
    m = plot_folium_map(df, label)

    # Save the map to the specified file path or return the map object
    if sname is not None:
        m.save(sname)
        return pathlib.Path(sname).absolute().resolve()
    else:
        return m


def get_countries_shapefile(countries):
    """
    Retrieves and processes a shapefile containing the boundaries of specified countries.

    Parameters
    ----------
    countries : list of str
        A list of country names for which the shapefile data is to be retrieved.

    Returns
    -------
    geopandas.GeoDataFrame
        A GeoDataFrame containing the geometries of the specified countries.

    Notes
    -----
    - The function uses the `pooch` library to download the dataset.
    - The dataset is sourced from OpenDataSoft and is in Parquet format.
    - The "geo_point_2d" column is dropped, and the "geo_shape" column is used as the geometry.

    Examples
    --------
    >>> get_countries_shapefile(["Tajikistan", "Kyrgyzstan"])
    GeoDataFrame containing geometries for Tajikistan and Kyrgyzstan.
    """
    import pooch

    # URL for the world administrative boundaries dataset
    url_world_boundaries = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/world-administrative-boundaries/exports/parquet?lang=en&timezone=Europe%2FBerlin"
    fname = pooch.retrieve(url_world_boundaries, None)

    # Process the dataset and extract geometries for the specified countries
    countries_polygons = (
        gpd.read_parquet(fname)
        .drop(columns=["geo_point_2d"])
        .set_geometry("geo_shape")
        .set_index("name")
        .loc[countries]
    )
    return countries_polygons


def read_zenodo_record(zenodo_id, flist=None):
    """
    Downloads files from a Zenodo record and optionally filters them by a specified list of filenames.

    Parameters
    ----------
    zenodo_id : str
        The Zenodo record ID to retrieve files from.
    flist : list of str, optional
        A list of filenames to filter the files to be downloaded. If None, all files in the record will be downloaded.

    Returns
    -------
    list of str
        A list of file paths to the downloaded (and possibly extracted) files.

    Raises
    ------
    Exception
        If there are issues accessing the Zenodo record or downloading the files.

    Examples
    --------
    >>> read_zenodo_record("10732042", ["file1.shp", "file2.shp"])
    ['/path/to/file1.shp', '/path/to/file2.shp']
    """
    import pyzenodo3
    import pooch

    # Access the Zenodo record
    z = pyzenodo3.Zenodo()
    record = z.get_record(zenodo_id)

    files = record.data["files"]

    out = []
    for i, f in enumerate(files):
        name = f["key"]
        if flist is not None:
            if name not in flist:
                continue
        link = f["links"]["self"]

        # Handle ZIP files and other formats
        if name.endswith(".zip"):
            processor = pooch.Unzip()
        else:
            processor = None

        fname = pooch.retrieve(link, None, name, processor=processor)
        if isinstance(fname, list):
            out += fname
        else:
            out.append(fname)
    return out


def get_shapefile(flist):
    """
    Filters a list of files to find a shapefile.

    Parameters
    ----------
    flist : list of str
        A list of file paths.

    Returns
    -------
    str
        The path to the shapefile.

    Raises
    ------
    ValueError
        If no shapefile is found.

    Examples
    --------
    >>> get_shapefile(["file1.shp", "file2.dbf"])
    'file1.shp'
    """
    fname = [f for f in flist if f.endswith(".shp")]
    if len(fname) == 0:
        raise ValueError("No shapefile found")
    elif len(fname) > 1:
        return fname
    else:
        return fname[0]


def plot_folium_map(df, name):
    """
    Plots an interactive map using Folium.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        The GeoDataFrame containing the data to be plotted.
    name : str
        The name of the map layer.

    Returns
    -------
    folium.Map
        The generated Folium map.

    Examples
    --------
    >>> plot_folium_map(gdf, "Example Map")
    Folium map object.
    """
    from cryogrid_run_manager import viz

    # Round float columns for better readability
    float_cols = df.select_dtypes(include=["float"]).columns
    df[float_cols] = df[float_cols].round(2)

    # Create the map
    m = df.explore(
        control=True, style_kwds=dict(fillOpacity=0.1, stroke=3), tiles=None, name=name
    )
    m = viz.folium_helpers.finalize_map(m)

    return m


def get_TPRoGI_data() -> gpd.GeoDataFrame:
    """
    Retrieves the TPRoGI dataset and applies a mask for specific countries.

    Returns
    -------
    geopandas.GeoDataFrame
        The GeoDataFrame containing the TPRoGI dataset.

    Examples
    --------
    >>> get_TPRoGI_data()
    GeoDataFrame containing TPRoGI data for Tajikistan and Kyrgyzstan.
    """
    get_flist = [
        "TPRoGI_Extended_Footprint.prj",
        "TPRoGI_Extended_Footprint.dbf",
        "TPRoGI_Extended_Footprint.cpg",
        "TPRoGI_Extended_Footprint.qmd",
        "TPRoGI_Extended_Footprint.shx",
        "TPRoGI_Extended_Footprint.shp",
    ]

    # Download and filter the dataset
    flist = read_zenodo_record(zenodo_id="10732042", flist=get_flist)
    fname = get_shapefile(flist)

    # Apply a mask for Tajikistan and Kyrgyzstan
    mask = get_countries_shapefile(["Tajikistan", "Kyrgyzstan"])
    gdf = gpd.read_file(fname, mask=mask)

    return gdf


if __name__ == "__main__":
    # Define the output directory and file name
    fig_dir = base / "figures"
    fig_dir.mkdir(exist_ok=True)
    fname_html = main(fig_dir / "rock_glaciers-TPRoGI-tajik_kyrgys.html")
    print(f"Figure saved to {fname_html}")
