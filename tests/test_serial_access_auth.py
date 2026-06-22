import unittest

from core.serial_access_auth import SerialAccessAuthState


class SerialAccessAuthStateTest(unittest.TestCase):
    def test_client_is_authorized_when_password_is_empty(self):
        auth = SerialAccessAuthState(lambda: "")

        self.assertTrue(auth.add_client("client"))
        self.assertTrue(auth.is_authorized("client"))

    def test_payload_password_updates_authorization(self):
        auth = SerialAccessAuthState(lambda: "secret")
        auth.add_client("client")

        self.assertFalse(auth.authenticate_payload("client", '{"password": "bad"}'))
        self.assertFalse(auth.is_authorized("client"))
        self.assertTrue(auth.authenticate_payload("client", '{"password": "secret"}'))
        self.assertTrue(auth.is_authorized("client"))

    def test_param_password_updates_authorization(self):
        auth = SerialAccessAuthState(lambda: "secret")
        auth.add_client("client")

        self.assertTrue(auth.authenticate_params("client", {"password": "secret"}))
        self.assertTrue(auth.is_authorized("client"))


if __name__ == "__main__":
    unittest.main()
