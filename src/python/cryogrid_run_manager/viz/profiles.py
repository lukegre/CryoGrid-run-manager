import matplotlib.pyplot as plt
from matplotlib.axes import Axes as _Axes
from matplotlib.figure import Figure as _Figure

__all__ = ["plot_profile_variables", "plot_profile"]


def plot_profile_variables(ds_profile) -> tuple[_Figure, list[_Axes], list]:
    assert ds_profile.gridcell.size == 1, (
        "More than one gridcell found in dataset. Make sure that you're passing only one profile file pattern."
    )

    index = ds_profile.gridcell.item()

    ds_profile = ds_profile.compute()
    fig, axs = plt.subplots(
        4,
        1,
        figsize=(12, 9),
        sharex=True,
        sharey=True,
        dpi=120,
        subplot_kw=dict(facecolor="0.8"),
    )
    axs = list(axs.ravel())

    imgs = []
    imgs += (
        plot_profile(
            ds_profile.T.assign_attrs({"long_name": "temperature", "units": "°C"}),
            ax=axs[0],
            center=0,
            cmap="RdBu_r",
        ),
    )
    imgs += (
        plot_profile(
            ds_profile.water.assign_attrs({"long_name": "Water content", "units": "%"}),
            ax=axs[1],
            cmap="Greens",
        ),
    )
    imgs += (
        plot_profile(
            ds_profile.ice.assign_attrs({"long_name": "Ice content", "units": "%"}),
            ax=axs[2],
            cmap="Blues",
        ),
    )
    imgs += (
        plot_profile(
            ds_profile.class_number.assign_attrs({"long_name": "Stratigraphy"}),
            ax=axs[3],
            cmap="Spectral",
        ),
    )

    [ax.set_title("") for ax in axs]
    axs[0].set_title(f"Profiles at gridcell #{index}", loc="left")

    fig.tight_layout()

    return fig, axs, imgs


def plot_profile(da_profile, **kwargs):
    name = da_profile.name

    long_name = da_profile.attrs.get("long_name", name)
    long_name = long_name.replace("_", " ").capitalize()

    unit = da_profile.attrs.get("units", "")
    unit = f"[{unit}]" if unit else ""

    kwargs["cbar_kwargs"] = dict(label=f"{long_name} {unit}", pad=0.01) | kwargs.pop(
        "cbar_kwargs", {}
    )

    if "ax" in kwargs:
        props = dict(robust=True) | kwargs
    else:
        props = dict(robust=True, aspect=5, size=4) | kwargs

    img = da_profile.plot.imshow(**props)
    img.axes.set_xlabel("")
    img.axes.set_ylabel("Depth [m]")

    return img
