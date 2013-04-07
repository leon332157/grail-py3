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


FieldLabels = Record(
    system_id="System ID",
    public_id="Public ID",
    doc_elem="Document Element",
    standalone="Standalone",
    xml_version="XML Version",
    encoding="Encoding",
    )


FieldNames = dir(Record)
for _name in FieldNames[:]:
    if _name[:2] == "__":
        FieldNames.remove(_name)


def get_xml_info(buffer):
    values = Record()
    parser = expat.ParserCreate()
    parser.XmlDeclHandler = values.XmlDeclHandler
    parser.StartDoctypeDeclHandler = values.StartDoctypeDeclHandler
    parser.Parse(buffer)
    return values


def dump_info(values):
    format = "%%%ds: %%s" % max(map(len, FieldLabels.__dict__.values()))
    for field_name in FieldNames:
        value = getattr(values, field_name)
        label = getattr(FieldLabels, field_name)
        if value is not None:
            print format % (label, value)


def main():
    import getopt
    #
    reqs = set()                     # required values (for output)
    #
    get_defaults = 1
    full_report = 0
    debugging = 0
    program = os.path.basename(sys.argv[0])
    opts, args = getopt.getopt(sys.argv[1:], "ad",
                               ["all", "docelem", "encoding", "public-id",
                                "standalone", "system-id", "version"])
    if opts:
        get_defaults = 0
    for opt, arg in opts:
        if opt in ("-a", "--all"):
            full_report = 1
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
        full_report = 1
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
    buffer = fp.read(10240)
    fp.close()
    try:
        values = get_xml_info(buffer)
    except Error, e:
        sys.stderr.write("parse failed: %s\n" % e)
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
                    print
                else:
                    print value


if __name__ == "__main__":
    main()
