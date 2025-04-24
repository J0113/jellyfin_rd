import json

class Settings:

    def __init__(self, settings_file = "settings.json"):
        with open(settings_file) as f:
            self.options = json.load(f)
    
    def __getitem__(self, name):
        return self.options[name]