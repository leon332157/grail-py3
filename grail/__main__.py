import sys
from . import main


if sys.argv[1:] and sys.argv[1][:2] == '-p':
    p = sys.argv.pop(1)
    from ast import literal_eval
    if p[2:]:
        n = literal_eval(p[2:])
    else:
        n = 20
    sys.modules[__package__].KEEPALIVE_TIMER = 50000
    import profile
    profile.run('main()', '@grail.prof')
    import pstats
    p = pstats.Stats('@grail.prof')
    p.strip_dirs().sort_stats('time').print_stats(n)
    p.print_callers(n)
    p.strip_dirs().sort_stats('cum').print_stats(n)
else:
    main()
