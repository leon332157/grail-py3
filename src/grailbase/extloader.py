"""Simple extension loader.  Specializations should override the get() method
to do the right thing."""

__version__ = '$Revision: 1.2 $'

import os


class ExtensionLoader:
    def __init__(self, package):
        self.__package = package
        self.__extensions = {}

    def get(self, name):
        try:
            ext = self.get_extension(name)
        except KeyError:
            ext = self.find(name)
            if ext is not None:
                self.add_extension(name, ext)
        return ext

    def find(self, name):
        return self.find_module(name)

    def find_module(self, name):
        try:
            mod = __import__(name, vars(self.__package), level=1)
        except ImportError:
            mod = None
        return mod

    def add_directory(self, path):
        path = os.path.normpath(os.path.join(os.getcwd(), path))
        if path not in self.__package.__path__:
            self.__package.__path__.insert(0, path)
            return 1
        else:
            return 0

    def add_extension(self, name, extension):
        self.__extensions[name] = extension

    def get_extension(self, name):
        return self.__extensions[name]
