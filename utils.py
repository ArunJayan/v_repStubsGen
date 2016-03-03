def indent(code, level=1, indent='    '):
    return '\n'.join(map(lambda x: '{}{}'.format(indent*level, x), code.split('\n')))
