
cluster_num = run_info.CLUSTER.STATVAR.cluster_number;

data.coord_x = run_info.SPATIAL.STATVAR.X;
data.coord_y = run_info.SPATIAL.STATVAR.Y;
data.lat = run_info.SPATIAL.STATVAR.latitude;
data.lon = run_info.SPATIAL.STATVAR.longitude;

data.mask = run_info.SPATIAL.STATVAR.mask;

data.elevation = run_info.SPATIAL.STATVAR.altitude;
data.slope_angle = run_info.SPATIAL.STATVAR.slope_angle;
data.aspect = run_info.SPATIAL.STATVAR.aspect;
data.skyview_factor = run_info.SPATIAL.STATVAR.skyview_factor;
data.stratigraphy_index = run_info.SPATIAL.STATVAR.stratigraphy_index;
% data.snow_index = run_info.SPATIAL.STATVAR.snow_index;
% data.roughness_length = run_info.SPATIAL.STATVAR.roughness_length;
% data.albedo = run_info.SPATIAL.STATVAR.albedo;
% data.emissivity = run_info.SPATIAL.STATVAR.emissivity;
data.matlab_index = [1 : size(data.elevation, 1)]';

data.cluster_num = run_info.CLUSTER.STATVAR.cluster_number;
data.cluster_idx = run_info.CLUSTER.STATVAR.sample_centroid_index;

sname = strcat(provider.PARA.result_path, provider.PARA.run_name, '/run_spatial_info.mat');
save(sname, 'data');

disp(sprintf('Saved spatial data for Python reading: %s\n', sname))
