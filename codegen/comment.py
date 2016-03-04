class Comment:
    def __init__(self, text, in_declaration=True, in_definition=False):
        self.text = text
        self.in_declaration = in_declaration
        self.in_definition = in_definition

    def is_long(self):
        return len(self.text) > 70

    def break_text(self, txt):
        last_good = None
        for i, c in enumerate(txt):
            if i > 78 and last_good:
                return [txt[:last_good]] + self.break_text(txt[last_good+1:])
            if c == ' ':
                last_good = i
                if i > 78:
                    return [txt[:last_good]] + self.break_text(txt[last_good+1:])
        return [txt]

    def get(self):
        if self.is_long():
            return '/* ' + '\n * '.join(self.break_text(self.text)) + '\n */\n\n'
        else:
            return '// ' + self.text + '\n\n'

    def declaration(self, include_defaults=True):
        return self.get() if self.in_declaration else ''

    def definition(self, include_defaults=False):
        return self.get() if self.in_definition else ''

