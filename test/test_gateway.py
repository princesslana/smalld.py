from unittest import mock

import pytest
from smalld.smalld import Gateway, GatewayClosedException
from websocket import ABNF

CONNECTION_URL = "ws://example.url/"


@pytest.fixture()
def ws_mock():
    with mock.patch("smalld.smalld.WebSocket", autospec=True) as ws_class_mock:
        instance = ws_class_mock.return_value
        instance.readlock = mock.MagicMock()
        instance.connected = True

        yield instance


def test_gateway_connects_on_iteration(ws_mock):
    ws_mock.recv_data.return_value = ABNF.OPCODE_TEXT, b"{}"
    gateway = Gateway(CONNECTION_URL)

    it = iter(gateway)
    next(it)
    it.close()

    ws_mock.connect.assert_called_once_with(CONNECTION_URL)


def test_gateway_yields_decoded_attrdict(ws_mock):
    test_inputs = [(ABNF.OPCODE_TEXT, b"{}"), (ABNF.OPCODE_TEXT, b'{"key": "value"}')]
    expected_results = [{}, {"key": "value"}]
    ws_mock.recv_data.side_effect = test_inputs
    gateway = Gateway(CONNECTION_URL)

    it = iter(gateway)
    results = [next(it), next(it)]
    it.close()

    assert len(ws_mock.recv_data.mock_calls) == len(test_inputs)
    assert results == expected_results
    assert hasattr(results[1], "key")


def test_gateway_skips_empty_data(ws_mock):
    test_input, expected = (ABNF.OPCODE_TEXT, b"{}"), {}
    ws_mock.recv_data.side_effect = [(ABNF.OPCODE_TEXT, b""), test_input]
    gateway = Gateway(CONNECTION_URL)

    it = iter(gateway)
    result = next(it)
    it.close()

    assert len(ws_mock.recv_data.mock_calls) == 2
    assert result == expected


def test_gateway_closes_on_close_event(ws_mock):
    expected_code, expected_reason = 16, "Reason"
    ws_mock.recv_data.return_value = ABNF.OPCODE_CLOSE, b"\x00\x10Reason"
    gateway = Gateway(CONNECTION_URL)

    it = iter(gateway)
    with pytest.raises(GatewayClosedException) as exc_info:
        next(it)

    e = exc_info.value
    assert e.code == expected_code and e.reason == expected_reason
