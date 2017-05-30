#! /usr/bin/env python

"""Script to print profiling reports from the command line.

Usage:  pinfo.py [profile-file] [callees | callers | stats]
                 [sorts] [restrictions]
"""
__version__ = '$Revision: 2.8 $'


import os
import pstats
import sys

legal_sorts = 'calls', 'cumulative', 'file', 'module', 'pcalls', 'line', \
              'name', 'nfl', 'stdname', 'time'
legal_reports = 'stats', 'callers', 'callees'

restrictions = (20,)
sorts = ('time', 'calls')
fileName = "@grail.prof"
report = 'stats'

if sys.argv[1:]:
    args = sys.argv[1:]
    if os.path.exists(args[0]):
        fileName = args.pop(0)
    if args:
        args = ','.join(args).split(',')
        if args and args[0] in legal_reports:
            report = args.pop(0)
        new_sorts = []
        while args and args[0] in legal_sorts:
            new_sorts.append(args.pop(0))
        if new_sorts:
            sorts = tuple(new_sorts)
        for i, arg in enumerate(args):
            try:
                args[i] = int(arg)
            except:
                pass
        restrictions = filter(None, args)


if not os.path.exists(fileName):
    import glob
    files = glob.glob("*.prof")
    if len(files) == 1:
        fileName = files[0]


p = pstats.Stats(fileName).strip_dirs()
p.sort_stats(*sorts)
getattr(p, 'print_' + report)(*restrictions)
