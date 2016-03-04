class Param(object):
    def __init__(self, node):
        if node.tag != 'param':
            raise ValueError('expected <param>, got <%s>' % node.tag)
        self.name = node.attrib['name']
        self.dtype = node.attrib['type']
        self.default = node.attrib.get('default', None)

    def mandatory(self):
        return self.default is None

    def optional(self):
        return self.default is not None

    def ctype(self):

        return self.dtype

    def vtype(self):
        return 'sim_script_arg_%s' % self.dtype

    def htype(self):
        return self.dtype

    def lfda(self):
        return '%sData[0]' % self.dtype

    def cdefault(self):
        return self.default

    @staticmethod
    def factory(node):
        dtype = node.attrib['type']
        if dtype == 'int':
            return ParamInt(node)
        elif dtype == 'float':
            return ParamFloat(node)
        elif dtype == 'string':
            return ParamString(node)
        elif dtype == 'bool':
            return ParamBool(node)
        elif dtype == 'table':
            return ParamTable(node)

class ParamInt(Param):
    def __init__(self, node):
        super(ParamInt, self).__init__(node)

    def vtype(self):
        return 'sim_script_arg_int32'

    def htype(self):
        return 'number'

    def lfda(self):
        return 'int32Data[0]'

class ParamFloat(Param):
    def __init__(self, node):
        super(ParamFloat, self).__init__(node)

    def htype(self):
        return 'number'

class ParamString(Param):
    def __init__(self, node):
        super(ParamString, self).__init__(node)

    def ctype(self):
        return 'std::string'

class ParamBool(Param):
    def __init__(self, node):
        super(ParamBool, self).__init__(node)

class ParamTable(Param):
    def __init__(self, node):
        super(ParamTable, self).__init__(node)
        self.itype = node.attrib['item-type']
        self.minsize = int(node.attrib['minsize']) if 'minsize' in node.attrib else 0

    def item_dummy(self):
        n = type('dummyNode', (object,), dict(tag='param', attrib={'name': 'dummy', 'type': self.itype}))
        return Param.factory(n)

    def ctype(self):
        return 'std::vector<%s>' % self.item_dummy().ctype()

    def vtype(self):
        return 'sim_script_arg_table|%s' % self.item_dummy().vtype()

    def htype(self):
        return 'table' + ('_%d' % self.minsize if self.minsize else '')

    def lfda(self):
        return self.item_dummy().lfda()[:-3]

    def cdefault(self):
        if self.default is not None:
            d = self.default
            d = 'boost::assign::list_of' + ''.join(map(lambda x: '(%s)' % x.strip(), d.strip()[1:-1].split(',')))
            return d

