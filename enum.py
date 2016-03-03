from utils import indent

class Enum:
    def __init__(self, name, fields=[], base=None):
        self.name = name
        self.fields = fields
        self.base = base

    def declaration(self):
        getbase = lambda i: ' = %s' % self.base if i == 0 and self.base else ''
        fieldlist = ['{}{}{}'.format(a, getbase(i), ',' if i < len(self.fields)-1 else '') for i, a in enumerate(self.fields)]
        return 'enum {}\n{{\n{}\n}};\n\n'.format(self.name, indent(fieldlist))

    def definition(self):
        return ''

