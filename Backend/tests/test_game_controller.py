"""
Unit tests for GameAutomationController and PyAutoGUI integration.
"""
import unittest
from unittest.mock import patch, MagicMock
from automation.game_controller import GameAutomationController, is_pyautogui_available


class TestGameAutomationController(unittest.TestCase):

    def setUp(self):
        self.controller = GameAutomationController()

    def test_supported_games(self):
        games = self.controller.get_supported_games()
        self.assertIn("2048", games)
        self.assertIn("pacman", games)
        self.assertIn("wordle", games)
        self.assertTrue(games["2048"]["url"].startswith("http"))

    def test_motivational_speech(self):
        speech = self.controller.get_motivational_speech("2048")
        self.assertIsInstance(speech, str)
        self.assertGreater(len(speech), 15)
        self.assertIn("2048", speech)

    @patch("webbrowser.open", return_value=True)
    def test_launch_game(self, mock_browser):
        result = self.controller.launch_game("pacman", auto_scroll=False)
        self.assertEqual(result["status"], "launched")
        self.assertEqual(result["game"], "pacman")
        self.assertTrue(result["browser_opened"])
        self.assertEqual(result["expression"], "excited")
        mock_browser.assert_called_once()

    def test_pyautogui_availability_check(self):
        avail = is_pyautogui_available()
        # On Windows desktop, pyautogui should be available after pip install
        self.assertIsInstance(avail, bool)


if __name__ == "__main__":
    unittest.main()
