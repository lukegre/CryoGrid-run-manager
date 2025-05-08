function provider = ensemble_injector(provider)

    name = 'variables1_values';

    fname_excel = provider.PARA.parameter_file;
    sheets = sheetnames(fname_excel);
    if any(sheets == name)

        values = readmatrix(fname_excel, 'Sheet', name);

        if any(any(isnan(values)))
            error('The provided table (%s :: %s) contains missing data. Note that any strings will be seen as missing - must be float or integer', fname_excel, name)
        end

        ensemble_params = provider.CLASSES.ENSEMBLE_fixed_values{1}.PARA;
        n_cols_params = size(ensemble_params.(name), 2);
        n_cols_excel = size(values, 2);

        if n_cols_excel ~= n_cols_params
            error('The number of columns in "provider" and %s.variables1_values must match', fname_excel)
        end
        provider.CLASSES.ENSEMBLE_fixed_values{1}.PARA.(name) = values;
    else
        disp('The given excel sheet does not contain %s', name)
    end

end
