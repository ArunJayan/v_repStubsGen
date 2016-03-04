from .param import Param

class Command(object):
    def __init__(self, node):
        if node.tag != 'command':
            raise ValueError('expected <command>, got <%s>' % node.tag)
        self.name = node.attrib['name']
        self.description = node.find('description')
        params = [Param.factory(p) for p in node.findall('params/param')]
        self.mandatory_params = [p for p in params if p.mandatory()]
        self.optional_params = [p for p in params if p.optional()]
        self.params = self.mandatory_params + self.optional_params
        self.returns = [Param.factory(p) for p in node.findall('return/param')]

