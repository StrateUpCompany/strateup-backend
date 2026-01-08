import json
import os
from pathlib import Path
from backend.utils.logger import logger

class GamificationEngine:
    def __init__(self, data_path="gamification.json"):
        self.data_path = Path(os.getcwd()) / data_path
        self._load_data()

    def _load_data(self):
        if self.data_path.exists():
            try:
                with open(self.data_path, "r") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load gamification data: {e}")
                self.data = self._default_data()
        else:
            self.data = self._default_data()
            self._save_data()

    def _default_data(self):
        return {
            "xp": 0,
            "level": 1,
            "streak": 0,
            "last_active": None,
            "achievements": []
        }

    def _save_data(self):
        try:
            with open(self.data_path, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save gamification data: {e}")

    def get_state(self):
        return self.data

    def add_xp(self, amount: int, reason: str = ""):
        self.data["xp"] += amount
        
        # Calculate Level: Simple formula (Level = 1 + XP // 100) or Logarithmic
        # Let's use 100 * level^1.5 approx, or simple chunks. 
        # For MVP: Level UP every 100 XP * Current Level? 
        # Let's simple: Level = 1 + (XP / 500)
        new_level = 1 + int(self.data["xp"] / 500)
        
        leveled_up = new_level > self.data["level"]
        self.data["level"] = new_level
        self._save_data()
        
        return {
            "xp": self.data["xp"],
            "level": self.data["level"],
            "leveled_up": leveled_up,
            "added": amount,
            "reason": reason
        }
