"""Protocol schemes package.

This package supports a high level interface to importation of support
for URL protocol schemes.

Exported functions:

protocol_access(url, mode, params, data=None)
        returns the protocol scheme object for the scheme specified in
        the URL.

protocol_joiner(scheme)
        return a function to implement relative URL joining according
        to the scheme; or None if no such function exists.

"""

from .ProtocolAPI import protocol_access, protocol_joiner
