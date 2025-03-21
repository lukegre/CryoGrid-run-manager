import pathlib

import click
import dotenv

from . import templater


def parse_bbox(ctx, param, value):
    try:
        w, s, e, n = map(float, value.split(","))
        return (w, s, e, n)
    except ValueError:
        raise click.BadParameter("bbox must be four comma-separated numbers")


@click.command()
@click.option("--name", "-n", required=True, type=str, help="Name of new run")
@click.option(
    "--bbox",
    "-b",
    required=True,
    callback=parse_bbox,
    help="Bounding box as comma-separated values (W,S,E,N)",
)
@click.option(
    "--template-dir",
    "-t",
    default="templates",
    help="Directory containing template files",
)
def create_new_run(name, bbox, template_dir):
    # using find_dotenv to get the project directory
    base_path = pathlib.Path(dotenv.find_dotenv(filename="pyproject.toml")).parent
    run_dir = base_path / "runs"
    assert run_dir.exists(), (
        f"Run directory {run_dir} does not exist - check that you're in the somewhere in CryoGrid-run-manager project directory"
    )
    run_path = run_dir / name

    bbox_WSEN = list(bbox)
    template_dir = pathlib.Path(template_dir)

    fpath_bbox, fpath_config = templater.main(run_path, bbox_WSEN, template_dir)
    click.echo(f"Run created at {run_path}")
    click.echo(f"BBox file: {fpath_bbox}")
    click.echo(f"Config file: {fpath_config}")


@click.command()
@click.option(
    "--experiment-path",
    "-e",
    type=click.Path(),
    default=".",
    help="Path to the experiment folder that contains the excel config",
)
@click.option(
    "--report-path",
    "-o",
    type=click.Path(),
    help="Output path for the report (e.g., ./report.html)",
)
@click.option(
    "--no-profile-plots",
    "-n",
    is_flag=True,
    help="Do not create profile plots in popups",
)
def create_report(experiment_path, report_path, no_profile_plots):
    import pathlib

    from loguru import logger

    from .report.main import create_report

    experiment_path = pathlib.Path(experiment_path).resolve()
    logger.info(f"Creating report for experiment at {experiment_path}")
    create_report(
        experiment_path,
        report_path=report_path,
        with_profile_plots=not no_profile_plots,
    )


if __name__ == "__main__":
    create_new_run()
