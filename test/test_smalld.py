from unittest.mock import Mock, patch

import pytest
from attrdict import AttrDict
from smalld.gateway import CloseReason
from smalld.smalld import SmallD, recoverable_error_codes


def prepare_gateway_mock(
    gateway_mock, smalld, side_effects=[()], close_reason=None, auto_close=True
):
    """Configures __iter__ for gateway.

    Each call to __iter__ is represented by an iterable in the side_effects list.
    If the iterable yields an exception, the exception is raised and iteration halts.

    By default this configuration:
      - closes gracefully
      - iterates once
    """

    side_effects = list(side_effects)
    finished = False

    def iter_gateway():
        nonlocal finished
        assert not finished, "infinite loop prevention"

        if not side_effects:
            finished = True
            if auto_close:
                smalld.close()
            return

        values = side_effects.pop(0)
        for value in values:
            if (
                isinstance(value, BaseException)
                or isinstance(value, type)
                and issubclass(value, BaseException)
            ):
                raise value
            yield AttrDict(value)

        if close_reason:
            gateway_mock.close_reason.return_value = CloseReason(*close_reason)

    gateway_mock.__iter__.side_effect = iter_gateway


@pytest.fixture(autouse=True)
def gateway_mock():
    with patch("smalld.smalld.Gateway") as gateway_cls:
        yield gateway_cls.return_value


@pytest.fixture(autouse=True)
def client_mock():
    with patch("smalld.smalld.HttpClient", autospec=True) as client_cls:
        instance = client_cls.return_value
        # for get gateway request
        instance.get.return_value = AttrDict({"url": "url/to/gateway"})
        yield instance


@pytest.fixture(autouse=True)
def sleep_mock():
    with patch("time.sleep") as sleep_mock:
        yield sleep_mock


test_data = [
    {"op": 1, "t": None, "d": {"key1": "value1"}, "s": 0},
    {"op": 0, "t": "EVENT", "d": {"key1", "value1"}, "s": 0},
]


@pytest.mark.parametrize(
    "payload_type, expected_data",
    [({"op": 1}, test_data[0]), ({"t": "EVENT"}, test_data[1])],
)
def test_smalld_calls_listener_on_payload(payload_type, expected_data, gateway_mock):
    callback = Mock()
    smalld = SmallD("token")
    prepare_gateway_mock(gateway_mock, smalld, [test_data])

    smalld.on_gateway_payload(**payload_type)(callback)
    smalld.run()

    callback.assert_called_once_with(expected_data)


def test_smalld_calls_event_listener_on_payload(gateway_mock):
    data = {"key", "value"}
    payload = {"op": 0, "t": "CREATE_MESSAGE", "d": data, "s": 0}
    callback = Mock()
    smalld = SmallD("token")
    prepare_gateway_mock(gateway_mock, smalld, [[payload]])

    smalld.on_create_message()(callback)
    smalld.run()

    callback.assert_called_once_with(data)


def test_smalld_ends_for_non_recoverable_gateway_errors(gateway_mock):
    smalld = SmallD("token")

    assert -1 not in recoverable_error_codes  # sanity check
    prepare_gateway_mock(gateway_mock, smalld, close_reason=(-1, "reason"))

    smalld.run()


@pytest.mark.parametrize("code", list(recoverable_error_codes))
def test_smalld_handles_recoverable_error(code, gateway_mock):
    smalld = SmallD("token")
    prepare_gateway_mock(gateway_mock, smalld, close_reason=(code, "reason"))

    smalld.run()  # doesn't raise


def test_smalld_closes_properly(gateway_mock, client_mock):
    smalld = SmallD("token")
    prepare_gateway_mock(gateway_mock, smalld)

    with smalld:
        smalld.run()

    assert smalld.closed is True
    gateway_mock.close.assert_called_once()
    client_mock.close.assert_called_once()


def test_smalld_closes_properly_with_exception(gateway_mock, client_mock):
    smalld = SmallD("token")
    exception = Exception()
    prepare_gateway_mock(gateway_mock, smalld, [[exception]], auto_close=False)

    with pytest.raises(Exception) as exc_info:
        with smalld:
            smalld.run()

    assert exc_info.value is exception
    assert smalld.closed is True
    gateway_mock.close.assert_called_once()
    client_mock.close.assert_called_once()
