import unittest

from core.simple_telnet import SimpleTelnet


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


class SimpleTelnetTest(unittest.TestCase):
    def test_filters_negotiation_commands_and_replies(self):
        telnet = SimpleTelnet()
        telnet._sock = FakeSocket()

        data = bytes([SimpleTelnet.IAC, SimpleTelnet.DO, 1]) + b"login:"

        self.assertEqual(telnet._process_telnet_commands(data), b"login:")
        self.assertEqual(
            telnet._sock.sent,
            [bytes([SimpleTelnet.IAC, SimpleTelnet.WONT, 1])],
        )

    def test_unescapes_literal_iac(self):
        telnet = SimpleTelnet()

        data = b"a" + bytes([SimpleTelnet.IAC, SimpleTelnet.IAC]) + b"b"

        self.assertEqual(telnet._process_telnet_commands(data), b"a\xffb")

    def test_skips_subnegotiation_block(self):
        telnet = SimpleTelnet()

        data = (
            b"a"
            + bytes([SimpleTelnet.IAC, SimpleTelnet.SB, 1, 2, SimpleTelnet.IAC, SimpleTelnet.SE])
            + b"b"
        )

        self.assertEqual(telnet._process_telnet_commands(data), b"ab")


if __name__ == "__main__":
    unittest.main()
