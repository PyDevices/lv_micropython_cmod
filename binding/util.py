from __future__ import print_function

import sys
from functools import lru_cache


def memoize(func):
    @lru_cache(maxsize=1000000)
    def memoized(*args, **kwargs):
        return func(*args, **kwargs)

    return memoized


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
