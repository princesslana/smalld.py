from collections import abc


class JsonObject(abc.Mapping):
    __slots__ = ("__data",)

    def __init__(self, data):
        self.__data = data

    def __getitem__(self, key):
        value = self.__data[key]
        if isinstance(value, dict):
            value = JsonObject(value)
        elif isinstance(value, list):
            value = tuple(value)
        return value

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
