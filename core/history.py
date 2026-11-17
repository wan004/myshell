import json
from pathlib import Path

class History:
    def __init__(self, path):
        self.path = Path(path)
        self.items = []
        self.load()

    def load(self):
        try:
            self.items = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.items = []

    def add(self, command):
        if command.strip():
            self.items.append(command)
            self.items = self.items[-500:]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.items, indent=2), encoding="utf-8")
