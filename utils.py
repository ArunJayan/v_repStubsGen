def indent(code, level=0, indent_str='    '):
    if isinstance(code, str):
        return '\n'.join(map(lambda x: '{}{}'.format(indent_str*level, x), code.split('\n')))
    if isinstance(code, (list, tuple)):
        return '\n'.join(indent(l, level=level+1, indent_str=indent_str) for l in code)
