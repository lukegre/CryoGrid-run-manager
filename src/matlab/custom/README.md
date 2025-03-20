## CryoGrid custom classes

Contains custom functions that I've adapted for my own runs. These are not intended to be submitted to the CryoGrid community model repository, but are rather for my own use. 

### New functions
- `post_process_clusters.m`: saves spatial parameters from the run to run_spatial_info.mat so that it can be read by Python
- `K_MEANS_custom.m`: adds a scaling factor to the features after doing the Z-scaling
- `MASK_stratigraphy.m`: when stratigraphy index is used, if values == 0, then masked out


### Modified functions
- `disp.m`: replaces the MATLAB standard so that the file and line number are displayed in the command window when disp is called
- `OUT_FDD_TDD.m`: commented out the print statement of the date for quieter runs
- `process_topoScale.m`: Fixes a small bug on line 212 where "double()" is called for era5.
- `OUT_regridded_FCI2.m`: moved the print statement for quieter runs


### Archived replacements
- `TILE_1D_standard.m`: should not require modifications if the run config is set up properly
- `OUT_regridded.m`: From Sebastian - removes FCI and saves output to relative depth - !!! For some reason, the TAG isn't assigned when using this output class meaning that cluster runs are not written correctly. Further, the way the depths are set is confusing. Sticking with the OUT_regridded_FCI2.m
- `OUT_regridded2.m`: A modification of OUT_regridded_FCI2.m, with the FCI part removed. However, still has the same tag issue... something goes wrong with the initialisation. 