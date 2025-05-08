% Differences from RUN_ENSEMBLE:
% 1) you can set number_of_cores used in the config
% 2) the number of ensembles is automatically computed as the product ensembles[1-3]
% 3) run_member is called by run_model and is used to run the model for each member of the ensemble
% 4) worker_number is now called member_index
% 5) the run_name is no longer changed, now use the tag (meaning that tag is superfluous if given)

classdef RUN_ENSEMBLE2 < matlab.mixin.Copyable

    properties
        PPROVIDER
        PARA
        CONST
        STATVAR
        TILE
        SPATIAL
    end


    methods

        function run_info = provide_PARA(run_info)

            run_info.PARA.ensemble_size = [];
            run_info.PARA.number_of_cores = 1;
            run_info.PARA.tile_class = [];
            run_info.PARA.tile_class_index = [];
            run_info.PARA.number_of_runs_per_tile = []; %vector

            run_info.PARA.point_class = [];
            run_info.PARA.point_class_index = [];
        end

        function run_info = provide_CONST(run_info)

        end

        function run_info = provide_STATVAR(run_info)

        end

        function run_info = finalize_init(run_info)
            % new addition: auto computes the number of runs in the
            % ensemble as the product of ensemble.variables[1-3] row
            % numbers. The number of cores is set as the smaller of the
            % number of runs and number of pre-defined cores to use.

            run_info.SPATIAL.STATVAR.latitude = 60;
            run_info.SPATIAL.STATVAR.longitude = 10;
            run_info.SPATIAL.STATVAR.altitude = 0;
            run_info.SPATIAL.STATVAR.area = 1;
            run_info.SPATIAL.STATVAR.slope_angle = 0;
            run_info.SPATIAL.STATVAR.aspect = 0;
            run_info.SPATIAL.STATVAR.skyview_factor = 0;
            run_info.SPATIAL.STATVAR.horizon_bins = 0;
            run_info.SPATIAL.STATVAR.horizon_angles = 0;

            if ~isempty(run_info.PARA.point_class) && sum(isnan(run_info.PARA.point_class))==0
                run_info.SPATIAL = copy(run_info.PPROVIDER.CLASSES.(run_info.PARA.point_class){run_info.PARA.point_class_index,1});
                run_info.SPATIAL.RUN_INFO = run_info;
                run_info.SPATIAL = finalize_init(run_info.SPATIAL);
            end

            ensemble = run_info.PPROVIDER.CLASSES.ENSEMBLE_fixed_values{1}.PARA;

            % This is a new edition to RUN_ENSEMBLE compute the
            % number of runs as the product of the ensemble groups
            % this can be used in the part below
            n_runs = max(1, size(ensemble.variables1_values, 1)) * ...
                     max(1, size(ensemble.variables2_values, 1)) * ...
                     max(1, size(ensemble.variables3_values, 1));
            run_info.PARA.ensemble_size = n_runs;
            run_info.PARA.number_of_cores = min(n_runs, run_info.PARA.number_of_cores);
        end

        function [run_info, tile] = run_model(run_info)
            % compared with the original RUN_ENSEMBLE, you can set the
            % number of cores in the config file. This is borrowed from
            % RUN_SPATIAL_CLUSTER

            tile = 0;
            if run_info.PARA.number_of_cores > 1 %parallelized
                fprintf( ...
                    'Running CryoGrid in parallel with %d cores and %d members to run', ...
                    run_info.PARA.number_of_cores, run_info.PARA.ensemble_size)
                parpool(run_info.PARA.number_of_cores)
                spmd
                    worker_number = spmdIndex;  % this is used to set the index of the ENSEMBLE_fixed_values index

                    for member_index = worker_number : run_info.PARA.number_of_cores : run_info.PARA.ensemble_size
                        run_member(run_info, member_index);
                    end
                end
                delete(gcp('nocreate'));
            else
                for member_index = 1:run_info.PARA.ensemble_size
                    run_member(run_info, member_index);
                end
            end

        end

        function tile = run_member(run_info, member_index)
            % This function is used to run the model for each member of the
            % ensemble. It is called by the run_model function above.
            %   run_info: the parent class (this class)
            %   member_index: the index of the ensemble member to run
            %
            % This function is also used in the parallelized version of the model.
            % The difference from RUN_ENSEMBLE is that we set the sample number
            % for the tile which is used to set the parameters in the
            % ENSEMBLE_fixed_values class

            run_info = copy(run_info);  % just make sure we don't write to all tiles when parallel

            num_members = run_info.PARA.ensemble_size;
            num_tiles = size(run_info.PARA.tile_class, 1);

            for i=1:num_tiles
                % these definitions are abstractions that make the code easier to read
                tile_index = run_info.PARA.tile_class_index(i,1);
                tile_class = run_info.PARA.tile_class{i,1};
                num_rounds = run_info.PARA.number_of_runs_per_tile(i, 1);

                for j=1:num_rounds  % tiles can be run multiple times

                    fprintf( ...
                        'Started [ member: %d/%d ;  tile: %d/%d ; round: %d/%d ]\n', ...
                        member_index, num_members, i, num_tiles, j, num_rounds);

                    new_tile = copy(run_info.PPROVIDER.CLASSES.(tile_class){tile_index, 1});

                    % also refactored this so it's easier to read
                    new_tile = apply_spatial_vars(run_info, new_tile);

                    new_tile.RUN_INFO = run_info;
                    new_tile.PARA.worker_number = member_index;
                    new_tile.PARA.ensemble_size = run_info.PARA.ensemble_size;

                    new_tile = set_out_tag(run_info, new_tile, sprintf("member%03d", member_index));
                    new_tile = finalize_init(new_tile);

                    tile = new_tile;
                    run_info.TILE = tile;

                    fprintf('running model\n')
                    tile = run_model(tile);  %time integration
                end

            end

        end

    end


    methods (Access = private)
        function tile = apply_spatial_vars(run_info, tile)

            statvar = run_info.SPATIAL.STATVAR;

            %applySpatialVars Copy non-empty STATVAR fields to tile.PARA
            fn = fieldnames(statvar);
            for k = 1:numel(fn)
                if ~isempty(statvar.(fn{k}))
                    tile.PARA.(fn{k}) = statvar.(fn{k});
                end
            end
        end

        function tile = set_out_tag(run_info, tile, tag)
            tag = string(tag);
            tile.RUN_INFO.PPROVIDER.CLASSES.(tile.PARA.out_class){1}.PARA.tag = tag;
            tile.OUT.PARA.tag = tag;
        end
    end

end
