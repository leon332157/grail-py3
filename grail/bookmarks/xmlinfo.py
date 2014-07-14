#! /usr/bin/env python
#  -*- python -*-

"""Support for retrieving useful information about XML data, including the
public and system IDs and the document type name.
"""

__version__ = "$Revision: 1.5 $"

import os
import sys
from xml.parsers import expat


Error = expat.ExpatError


class Record:
    public_id = None
    system_id = None
    doc_elem = None
    standalone = None
    xml_version = None
    encoding = "utf-8"

    def XmlDeclHandler(self, version, encoding, standalone):
        if version is not None:
            self.xml_version = version
        if encoding is not None:
            self.encoding = encoding
        if standalone >= 0:
            self.standalone = "yes" if standalone else "no"
    
    def StartDoctypeDeclHandler(self, doctypeName, systemId, publicId,
    has_internal_subset):
        self.doc_elem = doctypeName
        if publicId is not None:
            self.public_id = publicId
        if systemId is not None:
            self.system_id = systemId


FieldLabels = dict(
    system_id="System ID",
    public_id="Public ID",
    doc_elem="Document Element",
    standalone="Standalone",
    xml_version="XML Version",
    encoding="Encoding",
    )


FieldNames = sorted(FieldLabels.keys())


def get_xml_info(buffer):
    values = Record()
    parser = expat.ParserCreate()
    parser.XmlDeclHandler = values.XmlDeclHandler
    parser.StartDoctypeDeclHandler = values.StartDoctypeDeclHandler
    parser.Parse(buffer)
    return values


def dump_info(values):
    width = max(map(len, FieldLabels.values()))
    for field_name in FieldNames:
        value = getattr(values, field_name)
        label = FieldLabels[field_name]
        if value is not None:
            print("{:>{}}: {}".format(label, width, value))


def main():
    import getopt
    #
    reqs = set()                     # required values (for output)
    #
    get_defaults = True
    full_report = False
    debugging = 0
    program = os.path.basename(sys.argv[0])
    opts, args = getopt.getopt(sys.argv[1:], "ad",
                               ["all", "docelem", "encoding", "public-id",
                                "standalone", "system-id", "version"])
    if opts:
        get_defaults = False
    for opt, arg in opts:
        if opt in ("-a", "--all"):
            full_report = True
        elif opt == "-d":
            debugging = debugging + 1
        elif opt == "--docelem":
            reqs.add("doc_elem")
        elif opt == "--encoding":
            reqs.add("encoding")
        elif opt == "--public-id":
            reqs.add("publib_id")
        elif opt == "--standalone":
            reqs.add("standalone")
        elif opt == "--system-id":
            reqs.add("system_id")
        elif opt == "--version":
            reqs.add("xml_version")
    if get_defaults:
        full_report = True
    #
    if len(args) > 1:
        sys.stderr.write(program + ": too many input sources specified")
        sys.exit(2)
    if args:
        if os.path.exists(args[0]):
            fp = open(args[0], "rb")
        else:
            import urllib
            fp = urllib.urlopen(args[0])
    else:
        fp = sys.stdin.detach()
    #
    with fp:
        buffer = fp.read(10240)
    try:
        values = get_xml_info(buffer)
    except Error as e:
        sys.stderr.write("parse failed: {}\n".format(e))
        if debugging:
            raise
        sys.exit(1)
    #
    # Make the report:
    #
    if full_report:
        dump_info(values)
    else:
        for field_name in FieldNames:
            if field_name in reqs:
                value = getattr(values, field_name)
                if value is None:
                    print()
                else:
                    print(value)


if __name__ == "__main__":
    main()
