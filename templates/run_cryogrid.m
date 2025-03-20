%% TEMPLATE NOTES
% This template will be created at CryoGrid-run-manager/run/{{ run_name }}/run_cryogrid.m
% it assumes that the source code lives in CryoGrid-run-manager/src/matlab/source/...
% code that lives in CryoGrid-run-manager/src/matlab/custom/... will be preferentially used
% {{ run_name }} will be replaced by the actual run name given during creation

% start with a clean workspace
clear
restoredefaultpath

%% ADDING PATHS

init_format = 'EXCEL3D'; %choose the option corresponding to the parameter file format

% the parent path of the folder containing the parameter file
% run_cryogrid.m will be in the same folder as the parameter file
% so the result_path is one level up
result_path = '../';  

% run_name = name of parameter file (without file extension) and 
% name of subfolder (in result_path) within which it is located
% both the folder and the file should have the same name
% e.g., ../{{ run_name }}/{{ run_name }}.xlsx
% templating with jinja2 will replace { run_name } with the actual run name
run_name = '{{ run_name }}'; 

% filename of file storing constants lives in the same folder as the parameter file
% e.g., ../{{ run_name }}/CONSTANTS.xlsx
constant_file = 'CONSTANTS'; 

% add source code path
% current location should be ../{{ run_name }}/
addpath(genpath('../../src/matlab/source'));  % should be the same path on remote and local runs
addpath(genpath('./src/matlab'));  % add custom functions

%% read PARAMETERS from excel config file 

% create and load PROVIDER
provider = PROVIDER;
provider = assign_paths(provider, init_format, run_name, result_path, constant_file);
provider = read_const(provider);
provider = read_parameters(provider);

%% create RUN_INFO class

[run_info, provider] = run_model(provider);

% saves cluster and spatial information to a mat file that Python can read
post_process_clusters  

% if running locally, set number of cores to 1
% comment this out when running on a cluster
run_info.PARA.number_of_cores = 1;  

%% run model
[run_inf, tile] = run_model(run_info);
