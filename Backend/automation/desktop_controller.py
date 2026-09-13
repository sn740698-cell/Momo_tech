"""
Desktop and Browser Automation Controller for MOMO.
Executes desktop tasks requested by the user:
- Opening websites (Instagram, YouTube, Google, Twitter/X, GitHub, LinkedIn, etc.)
- Opening custom URLs
- Launching desktop applications (Notepad, Calculator, Terminal, etc.)
- Launching anti-burnout game breaks (2048, Pacman, Wordle)
"""
import os
import re
import sys
import time
import subprocess
import webbrowser
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Known web destinations with canonical URLs
KNOWN_WEB_TARGETS = {
    "instagram": {
        "name": "Instagram",
        "url": "https://www.instagram.com",
        "description": "Instagram social platform"
    },
    "youtube": {
        "name": "YouTube",
        "url": "https://www.youtube.com",
        "description": "YouTube video platform"
    },
    "google": {
        "name": "Google",
        "url": "https://www.google.com",
        "description": "Google Search"
    },
    "github": {
        "name": "GitHub",
        "url": "https://www.github.com",
        "description": "GitHub code hosting platform"
    },
    "twitter": {
        "name": "X (Twitter)",
        "url": "https://x.com",
        "description": "X (formerly Twitter)"
    },
    "x": {
        "name": "X (Twitter)",
        "url": "https://x.com",
        "description": "X (formerly Twitter)"
    },
    "linkedin": {
        "name": "LinkedIn",
        "url": "https://www.linkedin.com",
        "description": "LinkedIn professional network"
    },
    "reddit": {
        "name": "Reddit",
        "url": "https://www.reddit.com",
        "description": "Reddit communities"
    },
    "chatgpt": {
        "name": "ChatGPT",
        "url": "https://chatgpt.com",
        "description": "OpenAI ChatGPT"
    },
    "claude": {
        "name": "Claude AI",
        "url": "https://claude.ai",
        "description": "Anthropic Claude AI Assistant"
    },
    "gemini": {
        "name": "Google Gemini",
        "url": "https://gemini.google.com",
        "description": "Google Gemini AI"
    },
    "perplexity": {
        "name": "Perplexity AI",
        "url": "https://www.perplexity.ai",
        "description": "Perplexity AI Search"
    },
    "whatsapp": {
        "name": "WhatsApp Web",
        "url": "https://web.whatsapp.com",
        "description": "WhatsApp Web Messenger"
    },
    "facebook": {
        "name": "Facebook",
        "url": "https://www.facebook.com",
        "description": "Facebook Social Network"
    },
    "netflix": {
        "name": "Netflix",
        "url": "https://www.netflix.com",
        "description": "Netflix Streaming"
    },
    "amazon": {
        "name": "Amazon",
        "url": "https://www.amazon.com",
        "description": "Amazon Shopping"
    },
    "gmail": {
        "name": "Gmail",
        "url": "https://mail.google.com",
        "description": "Google Mail"
    },
    "spotify": {
        "name": "Spotify Web",
        "url": "https://open.spotify.com",
        "description": "Spotify Web Player"
    },
}

# Add domain aliases to KNOWN_WEB_TARGETS (e.g. instagram.com -> Instagram)
for _base_target in list(KNOWN_WEB_TARGETS.keys()):
    KNOWN_WEB_TARGETS[f"{_base_target}.com"] = KNOWN_WEB_TARGETS[_base_target]

# Windows desktop applications
KNOWN_SYSTEM_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
}


class DesktopAutomationController:
    """
    Unified Desktop & Browser Automation Engine.
    Safely executes user-requested actions on the host machine.
    """

    def __init__(self):
        self._last_action: Optional[Dict[str, Any]] = None

    @classmethod
    def extract_automation_intent(cls, user_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses natural language to determine whether the user is requesting
        to open a website, application, or game.
        Handles conversational phrasings like:
        - 'open instagram', 'open instagram.com', 'and yaaa open in instagram'
        - 'open youtube', 'open youtube.com', 'can you open youtube'
        - 'open https://...', 'launch game 2048'
        """
        text = user_text.lower().strip()

        # 1. Check for explicit URL in query (e.g. 'open https://example.com')
        url_match = re.search(r'(https?://[^\s]+)', user_text)
        if url_match:
            url = url_match.group(1).rstrip(".,;!?")
            return {
                "type": "open_url",
                "target": url,
                "url": url,
                "name": url
            }

        # 2. Check for game launch commands
        if any(w in text for w in ["play game", "open game", "launch game", "play 2048", "play pacman", "play wordle"]):
            game_key = "2048"
            for g in ["pacman", "wordle", "littlealchemy", "2048"]:
                if g in text:
                    game_key = g
                    break
            return {
                "type": "launch_game",
                "target": game_key,
                "game": game_key,
                "name": f"game {game_key.title()}"
            }

        # Action verbs indicating the user wants something opened
        action_verbs = [
            "open", "launch", "start", "go to", "browse to", "bring up",
            "visit", "show me", "take me to", "access", "navigate to"
        ]
        has_action_verb = any(re.search(rf"\b{v}\b", text) for v in action_verbs)

        # 3. Check for known website names/domains anywhere in query
        for k, v in KNOWN_WEB_TARGETS.items():
            base_k = k.replace(".com", "")
            # Match word boundary for site name, optionally with .com/.org/.in
            pattern = rf"\b{re.escape(base_k)}(?:\.com|\.org|\.in|\.net)?\b"
            if re.search(pattern, text):
                # If there's an action verb or the user literally just named the website
                if has_action_verb or text in (k, base_k, f"{base_k}.com"):
                    return {
                        "type": "open_website",
                        "target": base_k,
                        "url": v["url"],
                        "name": v["name"]
                    }

        # 4. Check for arbitrary internet domain (e.g. 'open google.com', 'visit reddit.com')
        domain_match = re.search(r'\b([a-zA-Z0-9-]+\.(?:com|org|net|io|edu|gov|in|co|ai|dev|app))\b', text)
        if domain_match and has_action_verb:
            domain = domain_match.group(1).lower()
            url = f"https://{domain}"
            return {
                "type": "open_url",
                "target": domain,
                "url": url,
                "name": domain
            }

        # 5. Check system desktop applications
        for app_name, exe in KNOWN_SYSTEM_APPS.items():
            if re.search(rf"\b{re.escape(app_name)}\b", text) and has_action_verb:
                return {
                    "type": "launch_app",
                    "target": app_name,
                    "executable": exe,
                    "name": app_name.title()
                }

        # 6. Fallback regex for direct verbs followed by target (with filler word stripping)
        clean_text = re.sub(r'\b(please|pls|plz|can you|could you|would you|and yaaa|yaaa|yaa|bro|for me|now|website|app|page|site)\b', ' ', text, flags=re.IGNORECASE)
        clean_text = " ".join(clean_text.split()).strip()

        for candidate_text in [clean_text, text]:
            action_match = re.search(r'(?:open|launch|start|go to|browse to|bring up|visit)(?:\s+(?:in|up|the|website|app|page))*\s+([a-z0-9\.\_\-]+)', candidate_text)
            if action_match:
                candidate = action_match.group(1).strip().rstrip(".,;!?")
                if candidate in KNOWN_WEB_TARGETS:
                    info = KNOWN_WEB_TARGETS[candidate]
                    return {
                        "type": "open_website",
                        "target": candidate,
                        "url": info["url"],
                        "name": info["name"]
                    }
                if "." in candidate and not candidate.endswith(".exe"):
                    url = candidate if candidate.startswith("http") else f"https://{candidate}"
                    return {
                        "type": "open_url",
                        "target": candidate,
                        "url": url,
                        "name": candidate
                    }
                if candidate in KNOWN_SYSTEM_APPS:
                    return {
                        "type": "launch_app",
                        "target": candidate,
                        "executable": KNOWN_SYSTEM_APPS[candidate],
                        "name": candidate.title()
                    }
                # Generalized fallback for known brand or internet query
                if len(candidate) >= 3 and candidate not in ["game", "something", "anything", "this", "that", "them", "files"]:
                    return {
                        "type": "open_website",
                        "target": candidate,
                        "url": f"https://www.{candidate}.com",
                        "name": candidate.title()
                    }

        return None

    def execute_automation(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the automation intent and returns execution status.
        """
        itype = intent.get("type")
        target_name = intent.get("name", "requested item")
        ts = time.time()

        is_dry_run = os.getenv("MOMO_AUTOMATION_DRY_RUN") == "1"

        try:
            if itype in ("open_website", "open_url"):
                url = intent.get("url", "")
                if not url:
                    return {"success": False, "error": "No URL provided", "timestamp": ts}

                logger.info(f"DesktopAutomationController opening browser URL: {url} (dry_run={is_dry_run})")
                opened = True if is_dry_run else webbrowser.open(url, new=2, autoraise=True)
                res = {
                    "success": True,
                    "action": "open_website",
                    "target": target_name,
                    "url": url,
                    "opened": opened,
                    "summary": f"Opened {target_name} ({url}) in your default web browser.",
                    "timestamp": ts,
                }
                self._last_action = res
                return res

            elif itype == "launch_game":
                game_key = intent.get("game", "2048")
                if is_dry_run:
                    launch_res = {"name": game_key, "url": f"https://play2048.co"}
                else:
                    from automation.game_controller import GameAutomationController
                    controller = GameAutomationController()
                    launch_res = controller.launch_game(game_key=game_key, auto_scroll=True)
                res = {
                    "success": True,
                    "action": "launch_game",
                    "target": launch_res.get("name", game_key),
                    "game": game_key,
                    "url": launch_res.get("url"),
                    "summary": f"Launched {launch_res.get('name', game_key)} for an anti-burnout break!",
                    "timestamp": ts,
                }
                self._last_action = res
                return res

            elif itype == "launch_app":
                exe = intent.get("executable", "")
                if exe:
                    logger.info(f"DesktopAutomationController launching app: {exe} (dry_run={is_dry_run})")
                    if not is_dry_run:
                        if sys.platform == "win32":
                            subprocess.Popen(exe, shell=True)
                        else:
                            subprocess.Popen([exe])
                    res = {
                        "success": True,
                        "action": "launch_app",
                        "target": target_name,
                        "summary": f"Launched {target_name} on your desktop.",
                        "timestamp": ts,
                    }
                    self._last_action = res
                    return res

        except Exception as e:
            logger.error(f"Desktop automation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "target": target_name,
                "timestamp": ts,
            }

        return {"success": False, "error": f"Unknown automation type: {itype}", "timestamp": ts}


_desktop_controller_instance = None

def get_desktop_controller() -> DesktopAutomationController:
    global _desktop_controller_instance
    if _desktop_controller_instance is None:
        _desktop_controller_instance = DesktopAutomationController()
    return _desktop_controller_instance
