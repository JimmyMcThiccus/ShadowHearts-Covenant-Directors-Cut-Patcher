"""Shared-library strings of the DC and US script builds (present in > 40 scripts of that build)."""
import os, glob, collections, sys
sys.path.insert(0, os.path.dirname(__file__)); import msc
def common(dirpath, n=40):
    c = collections.Counter()
    for f in glob.glob(os.path.join(dirpath, "*.MSC")):
        m = msc.Msc(open(f, "rb").read()); c.update({m.cstr(o) for _, o in m.dref})
    return frozenset(s for s, k in c.items() if k > n)
