
function save_run_info_spatial(run_info)
    % Save run_info.SPATIAL.STATVAR variables to a .mat file
    % for Python reading. Exclude the 'key' field.

    skip_fields = {'key'};
    for field = fieldnames(run_info.SPATIAL.STATVAR)'
        field_item_spatial = field{1}; % Extract string

        if ~ismember(field_item_spatial, skip_fields)
            data.(field_item_spatial) = run_info.SPATIAL.STATVAR.(field_item_spatial);
        end

    end

    for field = fieldnames(run_info.CLUSTER.STATVAR)'
        field_item_cluster = field{1}; % Same fix here
        data.(field_item_cluster) = run_info.CLUSTER.STATVAR.(field_item_cluster);
    end

    sname = fullpath([run_info.PPROVIDER.PARA.result_path '/' run_info.PPROVIDER.PARA.run_name '/run_spatial_info.mat']);
    save(sname, 'data');

    fprintf('Saved spatial data for Python reading: %s\n', sname)
end
