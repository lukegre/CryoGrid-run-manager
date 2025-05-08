function disp(s, varargin)
    st = dbstack;  % Get the calling functions
    if length(st) <= 1
        % Format the message using varargin
        message = sprintf(s, varargin{:});
    else
        func = st(2);  % Get the parent function of disp
        func_info = sprintf('<%s: %d>', func.name, func.line);
        % Format the message using varargin
        formatted_message = sprintf(s, varargin{:});
        % Ensure that spacing of s relative to func_info is consistent
        message = sprintf('%-50s %s\n', func_info, formatted_message);
    end

    fprintf(message);
end
