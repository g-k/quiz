import typing as t
from operator import attrgetter


class Error(Exception):
    """Base error class"""


class FrozenDict(t.Mapping):
    __slots__ = '_inner'

    def __init__(self, inner):
        assert isinstance(inner, dict)
        self._inner = inner

    __len__ = property(attrgetter('_inner.__len__'))
    __iter__ = property(attrgetter('_inner.__iter__'))
    __getitem__ = property(attrgetter('_inner.__getitem__'))
    __repr__ = property(attrgetter('_inner.__repr__'))

    def __hash__(self):
        return hash(frozenset(self._inner.items()))


FrozenDict.EMPTY = FrozenDict({})
