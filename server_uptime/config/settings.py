from importlib import import_module


class Settings:
    def __init__(self):
        module = import_module("server_uptime.config.settings_file")
        for setting in dir(module):
            if setting.isupper():
                setting_value = getattr(module, setting)
                setattr(self, setting, setting_value)


settings = Settings()
