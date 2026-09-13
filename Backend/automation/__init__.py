"""
Desktop Automation & Interactive Mindful Care Subsystem for MOMO.
Powered by PyAutoGUI and Playwright.
"""
from .game_controller import GameAutomationController, get_game_controller
from .desktop_controller import DesktopAutomationController, get_desktop_controller

__all__ = ["GameAutomationController", "get_game_controller", "DesktopAutomationController", "get_desktop_controller"]
