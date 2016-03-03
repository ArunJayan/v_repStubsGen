from utils import indent

class Function:
    def __init__(self, name, ret='void', args=[], body=None):
        self.name = name
        self.ret = ret
        self.args = args
        self.body = body

    def arglist(self, include_defaults=True):
        getdef = lambda a: ' = %s' % a.default if include_defaults and a.default else ''
        return ', '.join('{} {}{}'.format(a.ctype, a.name, getdef(a)) for a in self.args)

    def signature(self, include_defaults=True):
        return '{} {}({})'.format(self.ret, self.name, self.arglist(include_defaults))

    def declaration(self, include_defaults=True):
        return '{};\n\n'.format(self.signature(include_defaults))

    def definition(self, include_defaults=False):
        return '{}\n{{\n{}\n}}\n\n'.format(self.signature(include_defaults), indent(self.body)) if self.body is not None else ''

