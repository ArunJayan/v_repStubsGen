class Enum(object):
    def __init__(self, node):
        if node.tag != 'enum':
            raise ValueError('expected <enum>, got <%s>' % node.tag)
        self.name = node.attrib['name']
        self.item_prefix = note.attrib.get('item-prefix', '')
        self.base = note.attrib.get('base', None)
        self.items = [n.attrib['name'] for n in node.findall('item')]

