%========================================================================
% CryoGrid DATA_MASK class MASK_stratigraphy
% exclude a stratigraphy index number from the stratigraphy_index file -
% defaults to exclude_index = 0. Is additive by default (a AND b) 
%
% L. Gregor - Sep 2024
%========================================================================

classdef MASK_stratigraphy < matlab.mixin.Copyable

    
    properties
        PARENT
        PARA
        CONST
        STATVAR
    end
    
    methods
        
        function mask = provide_PARA(mask)
            mask.PARA.exclude_index = [];
        end

        function mask = provide_STATVAR(mask)

        end
        
        function mask = provide_CONST(mask)
            
        end
        
        function mask = finalize_init(mask)
            if isempty(mask.PARA.exclude_index) || isnan(mask.PARA.exclude_index)
                mask.PARA.exclude_index = 0;
            end
        end
        

        function mask = apply_mask(mask)

            mask.PARENT.STATVAR.mask = mask.PARENT.STATVAR.mask & mask.PARENT.STATVAR.stratigraphy_index ~= mask.PARA.exclude_index;

        end
        
        
        
        %-------------param file generation-----
        function mask = param_file_info(mask)
            mask = provide_PARA(mask);
            
            mask.PARA.STATVAR = [];
            mask.PARA.class_category = 'DATA_MASK';
            mask.PARA.default_value = [];
            mask.PARA.options = [];
            
            mask.PARA.comment.exclude_index = {'stratigraphy index to exclude from clustering and runs'};
        end
     
            
    end
end

