import time

from collections import OrderedDict
from threading import Condition


class SimpleCache(object):
    def __init__(self, timeout=None, max_items=1000, lru=True, force_expiry_multiple=10):
        if max_items is None or max_items <= 0:
            raise Exception("max_items must be a positive integer")

        self._d = OrderedDict()
        self._timeout = timeout
        self._max_items = max_items
        self._lru = lru
        self._last_expiry_check = time.time()
        self._force_exipry_multiple = force_expiry_multiple

    def __len__(self):
        self.__expire_all_if_necessary()
        return len(self._d)

    def __contains__(self, k):
        self.__expire_all_if_necessary()
        if k in self._d:
            v, t = self._d[k]
            self.__expire_key_if_necessary(k, t)
            return k in self._d
        else:
            return False

    def __getitem__(self, k):
        self.__expire_all_if_necessary()
        v, t = self._d[k]
        if self.__expire_key_if_necessary(k, t):
            raise KeyError(k)

        if self._lru:
            del self._d[k]
            self[k] = v

        return v

    def __setitem__(self, k, v):
        self.__expire_all_if_necessary()
        timeout = time.time() + self._timeout if self._timeout else None
        self._d[k] = (v, timeout)
        self.__prune_if_necessary()

    def __delitem__(self, k):
        self.__expire_all_if_necessary()
        del self._d[k]

    def __iter__(self):
        self.__expire_all_if_necessary()
        return self._d.iterkeys()

    def __expire_key_if_necessary(self, k, t):
        if t and time.time() > t:
            del self._d[k]
            return True
        else:
            return False

    def __expire_all_if_necessary(self):
        if self._timeout and time.time() > self._last_expiry_check + (self._timeout * self._force_exipry_multiple):
            for k, v in reversed(self._d.items()):
                value, timeout = v
                if timeout and time.time() > timeout:
                    del self._d[k]

    def __prune_if_necessary(self):
        if len(self._d) > self._max_items:
            self._d.popitem(last=False)


class ThreadSafeSimpleCache(SimpleCache):
    def __init__(self, timeout=None, max_items=1000, lru=True, force_expiry_multiple=10):
        super(ThreadSafeSimpleCache, self).__init__(timeout=timeout, max_items=max_items, lru=lru,
                                                    force_expiry_multiple=force_expiry_multiple)
        self._c = Condition()

    def __len__(self):
        self._c.acquire()
        try:
            return SimpleCache.__len__(self)
        finally:
            self._c.release()

    def __contains__(self, k):
        self._c.acquire()
        try:
            return SimpleCache.__contains__(self, k)
        finally:
            self._c.release()

    def __getitem__(self, k):
        self._c.acquire()
        try:
            return SimpleCache.__getitem__(self, k)
        finally:
            self._c.release()

    def __setitem__(self, k, v):
        self._c.acquire()
        try:
            SimpleCache.__setitem__(self, k, v)
        finally:
            self._c.release()

    def __delitem__(self, k):
        self._c.acquire()
        try:
            SimpleCache.__delitem__(self, k)
        finally:
            self._c.release()

    def __iter__(self):
        self._c.acquire()
        try:
            return SimpleCache.__iter__(self)
        finally:
            self._c.release()
