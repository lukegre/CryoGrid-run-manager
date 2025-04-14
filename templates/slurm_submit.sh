#!/bin/bash

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=36
#SBATCH --time=32:00:00
#SBATCH --job-name="cryogrid"
#SBATCH --mem-per-cpu=2304
#SBATCH --tmp=64000
#SBATCH --output="log_slurm_job.out"
#SBATCH --error="log_slurm_job.err"
#SBATCH --open-mode=truncate

# load modules and run simulation using srun for proper job execution
srun bash -c '
    module load matlab
    echo "Loaded modules (including MATLAB)"
    echo "Starting MATLAB and running run_cryogrid.m"
    matlab -batch "run_cryogrid"
'

# NOTES:
# this runs the matlab script run_cryogrid.m in the current directory
# as a batch job on the cluster assuming that your cluster uses the SLURM scheduler

# MODIFICATIONS:
# 2025-03-14: mem-per-cpu reduced from 3084 to 2304 as only 63% of memory used in 36 CPU run
