class Variable:
    def __init__(self, name, ctype, default=None, const=False):
        self.name = name
        self.ctype = ctype
        self.default = default
        self.const = const

    def declaration(self, include_default=True):
        return ''

    def definition(self):
        return '{}{} {} = {};\n\n'.format('const ' if self.const else '', self.ctype, self.name, self.default) if self.default else ''

