import geopandas as gpd


def main(sname=None):
    import pathlib

    df = get_TPRoGI_data()

    name = "TPRoGI"
    link = "https://zenodo.org/records/10732042"
    label = f'<a href="{link}" target="_blank">{name}</a>'

    m = plot_folium_map(df, label)

    if sname is not None:
        m.save(sname)
        return pathlib.Path(sname).absolute().resolve()
    else:
        return m


def get_countries_shapefile(countries):
    import pooch

    url_world_boundaries = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/world-administrative-boundaries/exports/parquet?lang=en&timezone=Europe%2FBerlin"
    fname = pooch.retrieve(url_world_boundaries, None)

    countries_polygons = (
        gpd.read_parquet(fname)
        .drop(columns=['geo_point_2d'])
        .set_geometry('geo_shape')
        .set_index('name')
        .loc[countries]
    )
    return countries_polygons


def read_zenodo_record(zenodo_id, flist=None):
    import pyzenodo3
    import pooch

    z = pyzenodo3.Zenodo()
    record = z.get_record(zenodo_id)

    files = record.data['files']

    out = []
    for i, f in enumerate(files):
        name = f['key']
        if flist is not None:
            if name not in flist:
                continue
        link = f['links']['self']

        if name.endswith('.zip'):
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
    fname = [f for f in flist if f.endswith('.shp')]
    if len(fname) == 0:
        raise ValueError('No shapefile found')
    elif len(fname) > 1:
        return fname
    else:
        return fname[0]


def plot_folium_map(df, name):
    from cryogrid_run_manager import viz

    m = df.explore(control=True, style_kwds=dict(fillOpacity=0.1, stroke=3), tiles=None, name=name)
    m = viz.folium_helpers.finalize_map(m)

    return m


def get_TPRoGI_data()->gpd.GeoDataFrame:
    get_flist = [
        'TPRoGI_Extended_Footprint.prj',
        'TPRoGI_Extended_Footprint.dbf',
        'TPRoGI_Extended_Footprint.cpg',
        'TPRoGI_Extended_Footprint.qmd',
        'TPRoGI_Extended_Footprint.shx',
        'TPRoGI_Extended_Footprint.shp',
    ]

    flist = read_zenodo_record(zenodo_id='10732042', flist=get_flist)
    fname = get_shapefile(flist)

    mask = get_countries_shapefile(['Tajikistan', 'Kyrgyzstan'])
    gdf = gpd.read_file(fname, mask=mask)

    return gdf


if __name__ == '__main__':
    fname_html = main('rock_glaciers-TPRoGI-tajik_kyrgys.html')
