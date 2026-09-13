"""
Desktop Game Automation & Mindful Recharging Controller for MOMO.
Combines PyAutoGUI and Playwright / Desktop Browser to politely launch,
center, and motivate users during anti-burnout game breaks.
"""
import os
import time
import random
import logging
import threading
import webbrowser
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try importing pyautogui safely
_pyautogui_available = None

def is_pyautogui_available() -> bool:
    global _pyautogui_available
    if _pyautogui_available is None:
        try:
            import pyautogui
            # Disable PyAutoGUI fail-safe crash on corner hover for smoother background operation
            pyautogui.FAILSAFE = False
            _pyautogui_available = True
        except Exception as e:
            logger.warning(f"PyAutoGUI not available: {e}")
            _pyautogui_available = False
    return _pyautogui_available


class GameAutomationController:
    """
    Polite desktop automation engine.
    Launches lightweight games, aligns viewports with PyAutoGUI,
    and speaks empathetic motivation.
    """

    SUPPORTED_GAMES = {
        "2048": {
            "name": "2048 Number Puzzle",
            "url": "https://play2048.co/",
            "scroll_amount": -140,
            "description": "Combine the tiles to reach 2048 using your arrow keys!",
        },
        "pacman": {
            "name": "Google Pacman Classic",
            "url": "https://www.google.com/logos/2010/pacman10-hp.html",
            "scroll_amount": -100,
            "description": "Munch the dots, dodge the ghosts, and clear your mind!",
        },
        "wordle": {
            "name": "Wordle Daily Word Game",
            "url": "https://www.nytimes.com/games/wordle/index.html",
            "scroll_amount": -120,
            "description": "Guess the 5-letter word in 6 attempts!",
        },
        "littlealchemy": {
            "name": "Little Alchemy 2",
            "url": "https://littlealchemy2.com/",
            "scroll_amount": -100,
            "description": "Combine basic elements to craft the universe!",
        },
    }

    MOTIVATIONAL_QUOTES = [
        "Take a deep breath and enjoy this breather! You've been working so hard and your mind deserves to reset.",
        "Go for the high score! I'm cheering you on with my OLED eyes and robotic spirit!",
        "Every grand builder needs a quick recharge. Clear your mind, have fun, and make some legendary moves!",
        "Sometimes the best solution to a difficult problem comes right after stepping back for a fun 3-minute game.",
        "Look at that focus! Remember: rest isn't a reward for finishing work, it's a vital part of building great things.",
        "You're doing amazing today. Enjoy this joyful moment, I've got your back!",
    ]

    def __init__(self):
        self._active_session: Optional[Dict[str, Any]] = None

    def get_supported_games(self) -> Dict[str, Any]:
        return self.SUPPORTED_GAMES

    def get_motivational_speech(self, game_key: Optional[str] = None) -> str:
        quote = random.choice(self.MOTIVATIONAL_QUOTES)
        if game_key and game_key in self.SUPPORTED_GAMES:
            game_name = self.SUPPORTED_GAMES[game_key]["name"]
            return f"Opening {game_name} for you! {quote}"
        return quote

    def launch_game(self, game_key: str = "2048", auto_scroll: bool = True) -> Dict[str, Any]:
        """
        Launches the chosen game in the user's browser, uses PyAutoGUI to focus
        and center the canvas, and returns the launch metadata.
        """
        key = game_key.lower().strip()
        if key not in self.SUPPORTED_GAMES:
            key = "2048"

        game_info = self.SUPPORTED_GAMES[key]
        url = game_info["url"]
        scroll_amt = game_info.get("scroll_amount", -120)

        logger.info(f"MOMO launching game break: {game_info['name']} -> {url}")

        # 1. Open the website in the default desktop browser
        try:
            opened = webbrowser.open(url, new=2, autoraise=True)
        except Exception as e:
            logger.warning(f"webbrowser.open failed: {e}")
            opened = False

        # 2. Trigger asynchronous PyAutoGUI window focus & canvas centering in background thread
        if auto_scroll:
            threading.Thread(
                target=self._smooth_center_window,
                args=(scroll_amt,),
                daemon=True
            ).start()

        motivation = self.get_motivational_speech(key)

        self._active_session = {
            "game": key,
            "name": game_info["name"],
            "url": url,
            "started_at": time.time(),
            "motivation": motivation,
        }

        return {
            "status": "launched",
            "game": key,
            "name": game_info["name"],
            "url": url,
            "browser_opened": opened,
            "motivation": motivation,
            "expression": "excited",
            "animation": "celebrate",
            "timestamp": time.time(),
        }

    def _smooth_center_window(self, scroll_amount: int = -120):
        """
        Waits for browser tab initialization, moves cursor gently to center,
        clicks once to ensure keyboard focus, and gently scrolls down to canvas.
        """
        time.sleep(1.2)  # Wait for browser window rendering

        if not is_pyautogui_available():
            logger.info("PyAutoGUI not active; skipped scroll centering.")
            return

        try:
            import pyautogui
            sw, sh = pyautogui.size()
            center_x, center_y = sw // 2, sh // 2

            # Gentle smooth cursor glide to center
            pyautogui.moveTo(center_x, center_y, duration=0.35, tween=pyautogui.easeOutQuad)
            time.sleep(0.1)
            # Click once to capture focus for arrow keys
            pyautogui.click()
            time.sleep(0.15)
            # Smooth scroll to center the game canvas
            pyautogui.scroll(scroll_amount)
            logger.info(f"PyAutoGUI centered game canvas at ({center_x}, {center_y}) with scroll {scroll_amount}")
        except Exception as e:
            logger.debug(f"PyAutoGUI canvas centering caught exception: {e}")


# Singleton instance
_game_controller = GameAutomationController()

def get_game_controller() -> GameAutomationController:
    return _game_controller
