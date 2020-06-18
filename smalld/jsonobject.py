from collections import abc


def wrap_value(value):
    if isinstance(value, dict):
        return JsonObject(value)
    if isinstance(value, list):
        return JsonArray(value)
    return value


class JsonObject(abc.Mapping):
    __slots__ = "__data",

    def __init__(self, data):
        self.__data = data

    def __getitem__(self, key):
        return wrap_value(self.__data[key])

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{attr}'"
            ) from None

    def __repr__(self):
        return repr(self.__data)


class JsonArray(abc.Sequence):
    __slots__ = "__data",

    def __init__(self, data):
        self.__data = data
    
    def __getitem__(self, index):
        return wrap_value(self.__data[index])

    def __len__(self):
        return len(self.__data)

    def __repr__(self):
        return repr(self.__data)
