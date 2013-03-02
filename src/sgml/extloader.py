"""This extension loader can load TagInfo objects which provide implementations
of HTML/SGML element start/end events.
"""
__version__ = '$Revision: 1.4 $'

import grailbase.extloader
from . import SGMLHandler


class TagExtensionLoader(grailbase.extloader.ExtensionLoader):
    def find(self, name):
        mod = self.find_module(name)
        taginfo = None
        if mod is not None:
            self.load_tag_handlers(mod)
            return self.get_extension(name)
        else:
            return None

    def load_tag_handlers(self, mod):
        handlers = {}
        for name, function in mod.__dict__.items():
            parts = name.split("_")
            if len(parts) != 2:
                continue
            if not (parts[0] and parts[1]):
                continue
            [action, tag] = parts
            start = do = end = None
            if handlers.has_key(tag):
                start, do, end = handlers[tag]
            if action == 'start':
                start = function
            elif action == 'end':
                end = function
            elif action == 'do':
                do = function
            handlers[tag] = (start, do, end)
        for tag, (start, do, end) in handlers.items():
            if start or do:
                taginfo = SGMLHandler.TagInfo(tag, start, do, end)
                self.add_extension(tag, taginfo)
