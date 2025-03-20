# CryoGrid run manager

This is a class that sets up CryoGrid runs by creating forcing, and by copying existing templates. This is optimized for the `RUN_SPATIAL_SPINUP_CLUSTERING` runs. 

It is designed to work with the specific folder structure, so don't move things around. 

## Installation

**Prerequiste**  
Install uv as a package manager for Python (https://docs.astral.sh/uv/getting-started/installation/#installation-methods)
  - MacOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

**Steps**

1. Clone this repository: `git clone https://github.com/lukegre/CryoGrid-run-manager.git`
3. Navigate into the project direcotry: `cd CryoGrid-run-manager`
4. Install Python dependencies with: `uv sync`
5. Download CryoGrid (https://github.com/sebastianwestermann/CryoGrid.git) and copy the `source` folder to `CryoGrid-run-manager/src/matlab/`

If you are running MacOS or Linux, you can skip steps 4, 5 and simply run: `make env`

## Usage

To create the setup for a new run: 

`uv run new-run --name abramov-test --bbox 71.537796,39.62768,71.680705,39.707624`

You will now find a new folder called `CryoGrid-run-manager/runs/abramov-test`. In this folder, you will find a forcing folder containing the files that correspond with the pathnames defined in <run-name>.xlsx. You will need to configure the Excel config file to adjust years, and other settings. 

Open up MATLAB, navigate to this new folder, and run the run_cryogrid.m file that is in this folder. It is also configured to simply run from this directory. 

Note that there are also some custom scripts that are copied to src/matlab in this run-folder. Feel free to adjust these. 


## TO DO

- [x] copy src/matlab/custom to each run directory and then change run_cryogrid.m to source the folder version
- [ ] change OUT_regridded.m so that forcing is also saved at the same resolution as the output
