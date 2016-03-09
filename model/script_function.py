from .param import Param

class ScriptFunction(object):
    def __init__(self, plugin, node):
        if node.tag != 'script-function':
            raise ValueError('expected <script-function>, got <%s>' % node.tag)
        self.plugin = plugin
        self.name = node.attrib['name']
        self.description = node.find('description')

        self.clear_stack_after_reading_input = True

        self.params = []
        for paramNode in node.findall('params/param'):
            param = Param.factory(paramNode)
            if param.skip:
                self.clear_stack_after_reading_input = False
            elif param.write_in:
                self.params.append(param)
        self.mandatory_params = [p for p in self.params if p.mandatory()]
        self.optional_params = [p for p in self.params if p.optional()]
        self.params = self.mandatory_params + self.optional_params

        self.returns = []
        for paramNode in node.findall('return/param'):
            param = Param.factory(paramNode)
            if param.write_out:
                self.returns.append(param)

