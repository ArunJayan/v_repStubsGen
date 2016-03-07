def indent(code, level=0, indent_str='    '):
    if isinstance(code, str):
        return '\n'.join(map(lambda x: '{}{}'.format(indent_str*level, x), code.split('\n')))
    if isinstance(code, (list, tuple)):
        return '\n'.join(indent(l, level=level+1, indent_str=indent_str) for l in code)

def unindent(lst):
    if not isinstance(lst, (tuple, list)):
        raise TypeError('argument must be a list')
    ret = []
    for x in lst:
        if not isinstance(x, (tuple, list)):
            raise TypeError('argument items must be list')
        for y in x:
            ret.append(y)
    return ret
