import pathlib
from functools import lru_cache
from typing import Union

import matplotlib.pyplot as plt
import xarray as xr
from loguru import logger


def make_run_folder_structure(
    run_path: Union[str, pathlib.Path],
    template_dir: Union[str, pathlib.Path],
    config_path_or_url: Union[str, pathlib.Path] = None,
    bbox_WSEN: list[float] = None,
):
    """
    Create the folder structure for a CryoGrid run. This includes the following:
        - README.md
        - run_cryogrid.m
        - <run_name>.xlsx
        - CONSTANTS.xlsx
        - forcing (dir)
            - bbox.txt
            - ...
        - output ...
        - source ...
        - figures ...

    Parameters
    ----------
    run_path : Union[str, pathlib.Path]
        The path to the run folder with the last part of the path being the run name.
    bbox_WSEN : list[float]
        The bounding box for the run in the format [W, S, E, N].
        Only supports Central Asia due to ERA5 data stored on S3 bucket
    template_dir : Union[str, pathlib.Path]
        The path to the folder containing the templates.
    config_path_or_url : Union[str, pathlib.Path], optional
        The path to the config file. If not provided, the config file will be created
        from the template folder with the default name 'run_config.xlsx'
        If a google sheets url is passed, then will download an excel version of the
        file to <run_path>/<run_name>.xlsx
    """
    run_path = pathlib.Path(run_path)
    template_dir = pathlib.Path(template_dir)
    run_name = run_path.name

    make_directories(run_path)
    copy_matplab_custom(run_path)

    # Create the README.md file
    readme_str = f"# CryoGrid: `{run_name}`\n\nThis folder contains the files for the CryoGrid run `{run_name}`."
    with open(run_path / "README.md", "w") as f:
        f.write(readme_str)

    # Create the bbox.txt file
    if bbox_WSEN is not None:
        bbox_str = ",".join([str(f) for f in bbox_WSEN])
        with open(run_path / "forcing" / "bbox.txt", "w") as f:
            f.write(bbox_str)

    # now for the templating
    assert template_dir.exists(), f"Could not find the templates folder: {template_dir}"

    # allows for template_dir/run_config.xlsx, any local xlsx file, or a Google Sheets url
    fpath_config = get_config_file(run_path, template_dir, config_path_or_url)

    copy_template_file(template_dir / "CONSTANTS.xlsx", run_path / "CONSTANTS.xlsx")
    render_template(
        template_dir / "slurm_submit.sh",
        run_path / "slurm_submit.sh",
        job_name=run_name,
    )
    make_run_cryogrid(run_path, template_dir)

    return fpath_config


def get_config_file(
    run_path: Union[str, pathlib.Path],
    template_dir: Union[str, pathlib.Path],
    config_path_or_url: Union[str, pathlib.Path] = None,
):
    """
    Get the config file for the run. If the config file is not provided, it will be created
    from the template folder with the default name 'run_config.xlsx'

    Parameters
    ----------
    run_path : Union[str, pathlib.Path]
        The path to the run folder with the last part of the path being the run name.
    template_dir : Union[str, pathlib.Path]
        The path to the folder containing the templates.
    config_path_or_url : Union[str, pathlib.Path]
        The path to the config file. If not provided, the config file will be created
        from the template folder with the default name 'run_config.xlsx'
        If a google sheets url is passed, then will download an excel version of the
        file to <run_path>/<run_name>.xlsx

    Returns
    -------
    fpath_config : Union[str, pathlib.Path]
        The path to the config file.
    """
    from .googlesheets import download_google_sheet_as_excel

    run_path = pathlib.Path(run_path)
    template_dir = pathlib.Path(template_dir)
    run_name = run_path.name

    fpath_config = run_path / f"{run_name}.xlsx"

    if config_path_or_url is None:
        # Create the config file from the template
        copy_template_file(template_dir / "run_config.xlsx", fpath_config)
    elif isinstance(config_path_or_url, str) and config_path_or_url.startswith(
        "https://"
    ):
        download_google_sheet_as_excel(config_path_or_url, fpath_config)
    elif isinstance(config_path_or_url, (str, pathlib.Path)) and str(
        config_path_or_url
    ).endswith(".xlsx"):
        # Copy the config file from the provided path
        config_path = pathlib.Path(config_path_or_url)
        assert config_path.exists(), f"Could not find the config file: {config_path}"
        copy_template_file(config_path, fpath_config)
    else:
        raise ValueError(
            "The config file must be a path to an Excel file or a Google Sheets URL."
        )

    return fpath_config


def make_directories(run_path: Union[str, pathlib.Path]):
    run_path = pathlib.Path(run_path)

    run_path.mkdir(exist_ok=True)
    (run_path / "forcing").mkdir(exist_ok=True)
    (run_path / "output").mkdir(exist_ok=True)
    (run_path / "src/python").mkdir(exist_ok=True, parents=True)
    (run_path / "figures").mkdir(exist_ok=True)


def copy_matplab_custom(run_path):
    import shutil

    import dotenv

    base = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent
    run_path = pathlib.Path(run_path)

    (run_path / "src").mkdir(exist_ok=True, parents=True)

    # copy base/source/matlab/custom to run_path/source/matlab
    custom_matlab_src = base / "src" / "matlab" / "custom/"
    custom_matlab_dst = run_path / "src" / "custom/"
    shutil.copytree(custom_matlab_src, custom_matlab_dst)
    custom_matlab_dst.rename(run_path / "src" / "matlab")


def copy_template_file(src_fname, dst_fname):
    """
    Copy a file from the templates folder to the run folder

    Parameters
    ----------
    src_fname : str
        The name of the file in the templates folder
    dst_fname : str
        The name of the file in the run folder
    """
    from shutil import copyfile

    src_fname = pathlib.Path(src_fname)
    dst_fname = pathlib.Path(dst_fname)

    assert src_fname.exists(), f"Could not find the file {src_fname}"
    assert dst_fname.parent.exists(), (
        f"Could not find the parent folder for {dst_fname}"
    )

    copyfile(src_fname, dst_fname)


def render_template(template_fname, out_name, **kwargs) -> str:
    """
    Render a template file with the provided arguments.

    Parameters
    ----------
    template_fname : str
        The name of the template file
    kwargs : dict
        The arguments to pass to the template

    Returns
    -------
    str
        The rendered template as a string
    """
    import jinja2

    env = jinja2.Environment()
    raw_str = open(template_fname).read()
    rendered_str = env.from_string(raw_str).render(**kwargs)

    with open(out_name, "w") as f:
        f.write(rendered_str)

    return rendered_str


def make_run_cryogrid(run_path, template_dir):
    import os

    template_fname = pathlib.Path(template_dir) / "run_cryogrid.m"
    run_path = pathlib.Path(run_path)
    run_name = run_path.name
    out_name = run_path / "run_cryogrid.m"

    # get the username of the current user
    username = os.environ.get("USERNAME", "unknown")
    render_template(
        template_fname, out_name=out_name, run_name=run_name, username=username
    )

    return out_name


def make_slurm_submit(run_path, template_dir):
    """
    Create the slurm submit file for the run.

    Parameters
    ----------
    run_path : str
        The path to the run folder
    template_dir : str
        The path to the templates folder
    """
    template_fname = pathlib.Path(template_dir) / "slurm_submit.sh"
    run_path = pathlib.Path(run_path)
    out_name = run_path / "slurm_submit.sh"

    rendered_str = render_template(template_fname, job_name=run_path.name)

    return out_name
