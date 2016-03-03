class Include:
    def __init__(self, filename, local=False, in_declaration=True, in_definition=False):
        self.filename = filename
        self.local = local
        self.in_declaration = in_declaration
        self.in_definition = in_definition

    def quoted_filename(self):
        return ('"{}"' if self.local else '<{}>').format(self.filename)

    def declaration(self, include_defaults=True):
        return '#include {}\n\n'.format(self.quoted_filename()) if self.in_declaration else ''

    def definition(self, include_defaults=False):
        return '#include {}\n\n'.format(self.quoted_filename()) if self.in_definition else ''

