from .param import Param

class Command(object):
    def __init__(self, plugin, node):
        if node.tag != 'command':
            raise ValueError('expected <command>, got <%s>' % node.tag)
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

        help_out_args = ','.join('%s %s' % (p.htype(), p.name) for p in self.returns)
        help_in_args = ','.join('%s %s' % (p.htype(), p.name) + ('=%s' % p.default if p.default is not None else '') for p in self.params)
        self.help_text = '{}={}{}({})'.format(help_out_args, plugin.command_prefix, self.name, help_in_args)

