import unittest

from core.login_state_machine import LoginConfig, LoginState, LoginStateMachine


class LoginStateMachineTest(unittest.TestCase):
    def test_login_password_shell_flow(self):
        sent = []
        machine = LoginStateMachine(
            LoginConfig(username="root", password="secret", shell_prompts=["#"])
        )
        machine.set_send_callback(sent.append)

        machine.start()
        self.assertEqual(machine.state, LoginState.WAIT_LOGIN)

        self.assertEqual(machine.feed("device login:"), "root\n")
        self.assertEqual(sent, ["root\n"])
        self.assertEqual(machine.state, LoginState.WAIT_PASSWORD)

        self.assertEqual(machine.feed("Password:"), "secret\n")
        self.assertEqual(sent, ["root\n", "secret\n"])
        self.assertEqual(machine.state, LoginState.WAIT_SHELL)

        self.assertIsNone(machine.feed("[root@device]#"))
        self.assertEqual(machine.state, LoginState.READY)
        self.assertTrue(machine.is_ready())

    def test_detects_existing_shell_prompt(self):
        machine = LoginStateMachine(LoginConfig(shell_prompts=["#"]))
        machine.start()

        self.assertIsNone(machine.feed("[root@device]#"))
        self.assertEqual(machine.state, LoginState.READY)

    def test_resets_state(self):
        machine = LoginStateMachine()
        machine.start()
        machine.reset()

        self.assertEqual(machine.state, LoginState.IDLE)

    def test_failed_after_repeated_login_prompt_while_waiting_password(self):
        machine = LoginStateMachine(LoginConfig(username="root"))
        machine.start()
        machine.feed("login:")

        self.assertEqual(machine.feed("login:"), "root\n")
        self.assertEqual(machine.feed("login:"), "root\n")
        self.assertIsNone(machine.feed("login:"))
        self.assertEqual(machine.state, LoginState.FAILED)


if __name__ == "__main__":
    unittest.main()
