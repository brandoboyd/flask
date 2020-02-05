# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

def truncate(var, var_type, max_length, substitute_with=None):
    """
    Truncates variable to a given max_length.

    :param var_type: can be 'text', 'number', 'list'
    :param max_length: is in each case:

        text - length of text
        number - number of digits
        list - a tuple (max_length_list, max_length_element)
        list_str - same as list, except, list is in a string separated with ';'

    :param substitute_with: an optional parameter to replace variable
    if it is larger than maximum length
    it works only for text and number

    For number, if number of digits is large than maximum
    it returns '9'*max_length.
    If original number is int, it returns int. If it is a str
    it returns str.

    :returns: var, modified if necessary
    """
    allowed_types = ['text', 'number', 'list', 'list_str']
    if not var_type in allowed_types:
        raise TypeError
    if var_type == 'text':
        if len(var) > max_length:
            if substitute_with is not None:
                return substitute_with
            return var[:max_length]
        else:
            return var
    if var_type == 'number':
        if type(var) == int:
            was_int = True
            var = str(var)
        else:
            was_int = False
        if len(var) > max_length:
            if substitute_with is not None:
                return substitute_with
            var = '9'*max_length
        if was_int:
            var = int(var)
        return var
    if var_type == 'list':
        max_length_list, max_length_element = max_length
        if len(var) > max_length_list:
            var = var[:max_length_list]
        for i, el in enumerate(var):
            if len(el) > max_length_element:
                var[i] = truncate(el, 'text', max_length_element)
        return var
    if var_type == 'list_str':
        var = var.split(';')
        var = [x.strip() for x in var]
        var = truncate(var, 'list', max_length)
        var = '; '.join(var).strip()
        return var
