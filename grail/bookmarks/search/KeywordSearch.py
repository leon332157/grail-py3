"""Basic keyword search for bookmarks."""

__version__ = '$Revision: 1.3 $'


class KeywordEditor:

    def __init__(self, frame, options=None):
        if options is None:
            options = KeywordOptions()
        self.__options = options
        self.__frame = frame

    def get_options(self):
        return self.__options


class KeywordMatcher:

    def __init__(self, options):
        self.__keywords = options.keywords()
        self.__case_sensitive = options.case_sensitive()
        self.__and = options.and_keywords()

    def match_Bookmark(self, bookmark):
        return self.__match(bookmark)

    def match_Folder(self, folder):
        return self.__match(folder), True

    __s = ".,-!@#$%^&*(){}[]|+=?'\""
    __tr = str.maketrans(__s, " " * len(__s))

    def __match(self, node):
        keywords = self.__keywords
        if not keywords:
            return False
        text = "{} {}".format(node.description(), node.title())
        if not self.__case_sensitive:
            text = text.lower()
        words = set(text.translate(self.__tr).split())
        if not words:
            return False
        if self.__and:
            # require that all are present:
            return all(kw in words for kw in keywords)
        else:
            # at least one keyword must be present:
            return any(kw in words for kw in keywords)


class KeywordOptions:
    __keywords = ()
    __keywords_text = ""
    __and_keywords = False
    __case_sensitive = False

    def __init__(self):
        # defined in case we need additional stuff later;
        # require subclasses to call it.
        pass

    def set_case_sensitive(self, case_sensitive):
        case_sensitive = bool(case_sensitive)
        if case_sensitive != self.__case_sensitive:
            self.__case_sensitive = case_sensitive
            self.set_keywords(self.__keywords_text)

    def set_keywords(self, keywords=""):
        if keywords != self.__keywords_text:
            self.__keywords_text = keywords
            if not self.__case_sensitive:
                keywords = keywords.lower()
            self.__keywords = tuple(keywords.split())

    def case_sensitive(self):
        return self.__case_sensitive

    def keywords(self):
        return self.__keywords

    def and_keywords(self):
        return self.__and_keywords
