import unittest
from unittest import mock

from core.local_shell_worker import LocalShellConfig, default_shell_command, shell_display_name


class LocalShellWorkerHelpersTest(unittest.TestCase):
    def test_shell_display_name_uses_command_basename(self):
        self.assertEqual(shell_display_name("/bin/bash -l"), "bash")
        self.assertEqual(shell_display_name("powershell.exe"), "powershell")

    def test_default_shell_uses_shell_env_on_posix(self):
        with mock.patch("platform.system", return_value="Linux"):
            with mock.patch.dict("os.environ", {"SHELL": "/bin/zsh"}):
                with mock.patch("os.path.exists", return_value=True):
                    self.assertEqual(default_shell_command(), "/bin/zsh")

    def test_default_shell_detects_windows_shell(self):
        def fake_which(command):
            return command if command == "powershell.exe" else None

        with mock.patch("platform.system", return_value="Windows"):
            with mock.patch("shutil.which", side_effect=fake_which):
                self.assertEqual(default_shell_command(), "powershell.exe -NoLogo -NoProfile")

    def test_config_defaults(self):
        config = LocalShellConfig(command="bash")
        self.assertEqual(config.cols, 80)
        self.assertEqual(config.rows, 24)
        self.assertEqual(config.encoding, "utf-8")


if __name__ == "__main__":
    unittest.main()
