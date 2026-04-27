import time
from unittest.mock import patch

from cyberdeck import device


def test_boot_time_is_set_at_module_load():
    assert isinstance(device.BOOT_TIME, float)
    assert device.BOOT_TIME <= time.time()


def test_uptime_seconds_grows():
    first = device.uptime_seconds()
    time.sleep(0.05)
    second = device.uptime_seconds()
    assert second >= first


def test_uptime_seconds_clamped_to_zero_when_clock_moves_backward():
    with patch("cyberdeck.device.time.time", return_value=device.BOOT_TIME - 30.0):
        assert device.uptime_seconds() == 0.0


def test_uptime_seconds_unchanged_when_time_ahead_of_boot():
    with patch("cyberdeck.device.time.time", return_value=device.BOOT_TIME + 123.0):
        assert device.uptime_seconds() == 123.0


def test_get_lan_ip_returns_string():
    ip = device.get_lan_ip()
    assert isinstance(ip, str)
    assert ip  # non-empty


def test_get_lan_ip_falls_back_to_loopback_on_socket_error():
    with patch("cyberdeck.device.socket.socket", side_effect=OSError("no network")):
        assert device.get_lan_ip() == "127.0.0.1"


def test_format_uptime_short():
    assert device.format_uptime(0) == "0m"
    assert device.format_uptime(60) == "1m"
    assert device.format_uptime(3600) == "1h 0m"
    assert device.format_uptime(3600 * 26 + 60 * 5) == "1d 2h"
    assert device.format_uptime(3600 * 24 * 4 + 3600 * 11) == "4d 11h"
