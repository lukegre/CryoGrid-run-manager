from functools import lru_cache


@lru_cache(maxsize=1)
def get_excel_config(fname_excel):
    from cryogrid_pytools import CryoGridConfigExcel

    return CryoGridConfigExcel(
        fname_excel, check_strat_layers=False, check_file_paths=False
    )


def get_stratigraphy_info(fname_excel):
    import pandas as pd

    config = get_excel_config(fname_excel)
    strat_info = config.get_class("STRAT_layers").T.apply(
        lambda x: pd.DataFrame(x.iloc[0][0]).iloc[0], axis=1
    )
    strat_info.index = strat_info.index.str.replace("STRAT_layers_", "").str.zfill(2)

    return strat_info


def get_max_depth(fname_excel, var_name="lower_elevation", class_name="OUT_regridded"):
    config = get_excel_config(fname_excel)
    df = config.get_class(class_name)
    depth = df.loc[var_name].iloc[0]
    return int(depth)
