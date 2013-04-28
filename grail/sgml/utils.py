"""Attribute handling and value conversion functions.

This module is safe for 'from sgml.utils import *'.

"""
__version__ = '$Revision: 1.4 $'
__all__ = (
    'extract_attribute', 'extract_keyword',
    'conv_integer', 'conv_float', 'conv_normstring', 'conv_enumeration',
    'conv_normwhitespace', 'conv_exists',
)


import string
from collections import Mapping


def extract_attribute(key, dict, default=None, conv=None, delete=True):
    """Extracts an attribute from a dictionary.

    KEY is the attribute name to look up in DICT.  If KEY is missing
    or cannot be converted, then DEFAULT is returned, otherwise the
    converted value is returned.  CONV is the conversion function, and
    DELETE (if true) says to delete the extracted key from the
    dictionary upon successful extraction.

    """
    if key in dict:
        val = dict[key]
        if delete:
            del dict[key]
        if not conv:
            return val
        try:
            return conv(val)
        except:
            return default
    return default


def extract_keyword(key, dict, default=None, conv=None):
    """Extracts an attribute from a dictionary.

    KEY is the attribute name to look up in DICT.  If KEY is missing
    or cannot be converted, then DEFAULT is returned, otherwise the
    converted value is returned.  CONV is the conversion function.
    """
    if key in dict:
        if conv:
            try:
                return conv(dict[key])
            except:
                return default
        return dict[key]
    return default


def conv_integer(val, conv=int, otherlegal=''):
    val = val.strip()
    l = len(val)
    start = 0
    if val[0] in '+-':
        start = 1
    legalchars = string.digits + otherlegal
    for i in range(start, l):
        if val[i] not in legalchars:
            val = val[:i]
            break
    return conv(val)


def conv_float(val):
    return conv_integer(val, conv=float, otherlegal='.')


def conv_normstring(val):
    return val.strip().lower()


def conv_enumeration(val, mapping_or_list):
    val = conv_normstring(val)
    if not isinstance(mapping_or_list, Mapping):
        if val in mapping_or_list: return val
        else: return None
    else:
        return mapping_or_list.get(val)


def conv_normwhitespace(val):
    return ' '.join(val.split())


def conv_exists(val):
    return True
