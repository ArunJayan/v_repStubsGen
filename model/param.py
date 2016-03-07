class Param(object):
    mapping = {}

    def __init__(self, node):
        if node.tag != 'param':
            raise ValueError('expected <param>, got <%s>' % node.tag)
        self.name = node.attrib['name']
        self.dtype = node.attrib['type']
        self.default = node.attrib.get('default', None)
        self.skip = node.attrib.get('skip', 'false').lower() in ('true', 'yes', '1')
        self.write_in = True
        self.write_out = True

    def mandatory(self):
        return self.default is None

    def optional(self):
        return self.default is not None

    def ctype(self):
        return self.dtype

    def ctype_normalized(self):
        return self.ctype().replace('::', '__')

    def vtype(self):
        return 'sim_script_arg_%s' % self.dtype

    def htype(self):
        return self.dtype

    def lfda(self):
        return '%sData[0]' % self.dtype

    def cdefault(self):
        return self.default

    @staticmethod
    def register_type(dtype, clazz):
        Param.mapping[dtype] = clazz

    @staticmethod
    def factory(node):
        dtype = node.attrib['type']
        return Param.mapping[dtype](node)

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
        self.itype = node.attrib['item-type'] if 'item-type' in node.attrib else None
        self.minsize = int(node.attrib['minsize']) if 'minsize' in node.attrib else 0
        if self.itype is None:
            self.write_in = False
            self.write_out = False

    def item_dummy(self):
        n = type('dummyNode', (object,), dict(tag='param', attrib={'name': 'dummy', 'type': self.itype}))
        return Param.factory(n)

    def ctype(self):
        if self.itype is not None:
            return 'std::vector<%s>' % self.item_dummy().ctype()
        else:
            return 'void *'

    def vtype(self):
        return 'sim_script_arg_table' + ('|%s' % self.item_dummy().vtype() if self.itype is not None else '')

    def htype(self):
        return 'table' + ('_%d' % self.minsize if self.minsize else '')

    def lfda(self):
        return self.item_dummy().lfda()[:-3]

    def cdefault(self):
        if self.default is not None:
            d = self.default
            d = 'boost::assign::list_of' + ''.join(map(lambda x: '(%s)' % x.strip(), d.strip()[1:-1].split(',')))
            return d

Param.register_type('int', ParamInt)
Param.register_type('float', ParamFloat)
Param.register_type('string', ParamString)
Param.register_type('bool', ParamBool)
Param.register_type('table', ParamTable)
