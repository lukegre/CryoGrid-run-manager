%========================================================================
% CryoGrid OUT class OUT_FDD_TDD
% accumulates and stores depth profiles of thawing and freezing degree days
% over the entire simulation period. The resulting output file can e.g. be
% used by the INIT_STEADY_STATE class INIT_TTOP_from_out to initialize
% a steady-state temperature profile for a subsequent TILE class; used in
% the accelerated spin-up procedure.
% S. Westermann, Jan 2021

% L. Gregor commented disp(date) for quieter runs
% 1) moved file_out to finalize_init - doesn't change during runtime
% 2) added 'output' as subdir to result_path
% 3) use fullfile + '/' to avoid problems with missing file separators
% 4) non-numeric tags are now allowed
%========================================================================


classdef OUT_FDD_TDD < matlab.mixin.Copyable


    properties

        TIMESTAMP
        TEMP
        PARA
        OUTPUT_TIME
        SAVE_TIME
        CONST
        STATVAR

	end


    methods

        function out = provide_PARA(out)

            out.PARA.output_timestep = [];
            out.PARA.max_depth = [];

            out.PARA.cell_size = 0.02;
            out.PARA.tag = [];

        end


        function out = provide_CONST(out)

        end

        function out = provide_STATVAR(out)

        end


		function out = finalize_init(out, tile)

            result_path = tile.PARA.result_path;
            run_name = tile.PARA.run_name; %tile.RUN_NUMBER;
            tag = out.PARA.tag;  % LG - added for simplicity

			out.OUTPUT_TIME = tile.FORCING.PARA.start_time + out.PARA.output_timestep;
            out.SAVE_TIME =  tile.FORCING.PARA.end_time;

            out.STATVAR.TDD = 0;
            out.STATVAR.FDD = 0;
            out.STATVAR.time_interval = 0;

            out.TEMP.new_grid = [0:out.PARA.cell_size:out.PARA.max_depth]';
            out.TEMP.new_grid = (out.TEMP.new_grid(2:end,1) + out.TEMP.new_grid(1:end-1,1))./2;

            directory = [result_path '/' run_name '/output/'];
            if isempty(tag) || (isnumeric(tag) && isnan(tag))
                file_out = [directory '/' run_name '_OUT_FDD_TDD.mat'];
            else
                 % LG - num2str(tag) required for numeric tags (read in by ENSEMBLE)
                file_out = [directory '/' run_name '_OUT_FDD_TDD_' num2str(tag) '.mat'];
            end
            out.PARA.file_out = fullfile(file_out);


        end

        %---------------time integration-------------

% 		function out = store_OUT(out, t, TOP, BOTTOM, forcing, run_number, timestep, result_path)

        function out = store_OUT(out, tile)

             t = tile.t;
             TOP = tile.TOP;
             BOTTOM = tile.BOTTOM;
             run_name = tile.PARA.run_name; %tile.RUN_NUMBER;
             result_path = tile.PARA.result_path;
            if t>=out.OUTPUT_TIME

                T=[];
                layerThick=[];
                CURRENT = TOP.NEXT;

                while ~isequal(CURRENT, BOTTOM)
                    class_name=class(CURRENT);
                    if ~strcmp(class_name(1:4), 'SNOW')
                        T=[T; CURRENT.STATVAR.T];
                        layerThick=[layerThick; CURRENT.STATVAR.layerThick];
                    end
                    CURRENT = CURRENT.NEXT;
                end

                depths = [0; cumsum(layerThick)-layerThick./2];
                T_interp = interp1(depths, [T(1,1); T], out.TEMP.new_grid);

                out.STATVAR.TDD = out.STATVAR.TDD + T_interp .* double(T_interp>0) .* out.PARA.output_timestep;
                out.STATVAR.FDD = out.STATVAR.FDD + T_interp .* double(T_interp<0) .* out.PARA.output_timestep;
                out.STATVAR.time_interval = out.STATVAR.time_interval + out.PARA.output_timestep;

                out.OUTPUT_TIME = out.OUTPUT_TIME + out.PARA.output_timestep;
                if t>=out.SAVE_TIME
                    if ~(exist([result_path run_name])==7)
                        mkdir([result_path run_name])
                    end
                    first_stable_cell = find(out.STATVAR.TDD == 0 | out.STATVAR.FDD == 0, 1);

                    out.STATVAR.TTOP = (out.STATVAR.TDD(first_stable_cell,1) + out.STATVAR.FDD(first_stable_cell,1)) ./ out.STATVAR.time_interval;
                    out.STATVAR.TTOP_depth = out.TEMP.new_grid(first_stable_cell, 1);

                    % simplified saving by defining file_out in finalize_init
                    save(out.PARA.file_out, 'out')
                    fprintf('Saved file to %s\n', out.PARA.file_out)
                end
            end
        end

        %-------------param file generation-----
        function out = param_file_info(out)
            out = provide_PARA(out);

            out.PARA.STATVAR = [];
            out.PARA.options = [];
            out.PARA.class_category = 'OUT';

            out.PARA.default_value.output_timestep = {0.25};
            out.PARA.comment.output_timestep = {'timestep of output [days]'};

            out.PARA.default_value.max_depth = {'4'};
            out.PARA.comment.max_depth = {'maximum depth checked for permafrost table'};

            out.PARA.default_value.cell_size = {2e-2};
            out.PARA.comment.cell_size = {'interpolation grid'};

        end

    end
end
