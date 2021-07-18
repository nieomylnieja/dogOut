from os import listdir

from kivy.lang import Builder
from kivymd.app import MDApp

from app.screens import LogoutDialog, SM


class DogOut(MDApp):
    kv_files_dir = "kv"

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Cyan"

        for f in listdir(self.kv_files_dir):
            Builder.load_file(f"{self.kv_files_dir}/{f}")

        return SM()

    @staticmethod
    def show_logout_dialog():
        LogoutDialog().open()
