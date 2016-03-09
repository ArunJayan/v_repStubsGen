from .param import Param

class Command(object):
    def __init__(self, plugin, node):
        if node.tag != 'command':
            raise ValueError('expected <command>, got <%s>' % node.tag)
        self.plugin = plugin
        self.name = node.attrib['name']
        self.description = node.find('description')
        params = [Param.factory(p) for p in node.findall('params/param')]
        self.mandatory_params = [p for p in params if p.mandatory()]
        self.optional_params = [p for p in params if p.optional()]
        self.params = self.mandatory_params + self.optional_params
        self.returns = [Param.factory(p) for p in node.findall('return/param')]
        help_out_args = ','.join('%s %s' % (p.htype(), p.name) for p in self.returns)
        help_in_args = ','.join('%s %s' % (p.htype(), p.name) + ('=%s' % p.default if p.default is not None else '') for p in self.params)
        self.help_text = '{}={}{}({})'.format(help_out_args, plugin.command_prefix, self.name, help_in_args)

