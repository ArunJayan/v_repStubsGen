from utils import indent

class Struct:
    def __init__(self, name, fields=[]):
        self.name = name
        self.fields = fields

    def declaration(self):
        fieldlist = '\n'.join('{} {};'.format(a.ctype, a.name) for a in self.fields)
        fieldlist += '\n\n{}();'.format(self.name)
        return 'struct {}\n{{\n{}\n}};\n'.format(self.name, indent(fieldlist))

    def definition(self):
        sd = '\n'.join('{} = {};'.format(a.name, a.default) for a in self.fields if a.default)
        return '{n}::{n}()\n{{\n{setdef}\n}}\n'.format(n=self.name, setdef=indent(sd))

