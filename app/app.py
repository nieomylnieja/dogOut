import datetime
import math
import re
import time
import uuid
from os import listdir
from typing import Callable

import geocoder
from email_validator import validate_email, EmailNotValidError
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.screenmanager import ScreenManager
from kivy_garden.mapview import MapView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.expansionpanel import MDExpansionPanel, MDExpansionPanelOneLine
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget, OneLineAvatarIconListItem, \
    TwoLineAvatarListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.selection import MDSelectionList
from kivymd.uix.snackbar import BaseSnackbar

from app.datasource import DS, DogModel, DogSex


class ErrorsListItem(OneLineIconListItem):
    divider = None
    icon = StringProperty(None)


class LoginScreen(MDScreen):
    email = ObjectProperty(None)
    password = ObjectProperty(None)

    errors: list[ErrorsListItem] = []

    def login(self):
        email_address = self.validate_email()
        password = self.validate_password()

        if len(self.errors) > 0:
            MDDialog(
                title="Errors in the login form!",
                type="simple",
                items=self.errors,
                size_hint=[None, None],
                size=[300, 400],
            ).open()
            self.errors = []
            return

        if not DS.login_user(email_address, password):
            MDDialog(
                title="Invalid credentials!",
                type="simple",
                size_hint=[None, None],
                size=[300, 400],
            ).open()
            return
        dog_out.sm.post_auth_add_widgets()
        self.manager.current = "home"

    def add_error(self, text: str, icon: str):
        self.errors.append(ErrorsListItem(text=text, icon=icon))

    def validate_password(self) -> str:
        if not self.password.text:
            self.add_error("Empty password", "key")
        return self.password.text

    def validate_email(self) -> str:
        if not self.email.text:
            self.add_error("Empty email address", "email")
        else:
            try:
                return validate_email(self.email.text).email
            except EmailNotValidError as e:
                print(e)
                self.add_error("Invalid email address", "email")


class RegisterScreen(MDScreen):
    username = ObjectProperty(None)
    email = ObjectProperty(None)
    phone = ObjectProperty(None)
    password = ObjectProperty(None)
    password_repeat = ObjectProperty(None)

    errors: list[ErrorsListItem] = []

    def add_error(self, text: str, icon: str):
        self.errors.append(ErrorsListItem(text=text, icon=icon))

    def validate_email(self) -> str:
        if not self.email.text:
            self.add_error("Empty email address", "email")
        else:
            try:
                return validate_email(self.email.text).email
            except EmailNotValidError as e:
                print(e)
                self.add_error("Invalid email address", "email")

    def validate_password(self) -> str:
        if not self.password.text:
            self.add_error("Empty password", "key")
        elif self.password.text != self.password_repeat.text:
            self.add_error("Passwords don't match", "key")
        elif not re.fullmatch(r'[A-Za-z0-9@#$%^&+=]{8,}', self.password.text):
            self.add_error("Invalid password pattern", "key")
        return self.password.text

    def validate_phone_number(self) -> str:
        if not self.phone.text:
            self.add_error("Empty phone number", "phone")
        elif len(self.phone.text) != 9 or not self.phone.text.isdigit():
            self.add_error(f"Invalid phone number", "phone")
        return self.phone.text

    def validate_username(self) -> str:
        if not self.username.text:
            self.add_error("Empty username", "account")
        return self.username.text

    def register(self):
        username = self.validate_username()
        email_address = self.validate_email()
        phone_number = self.validate_phone_number()
        password = self.validate_password()

        if len(self.errors) > 0:
            MDDialog(
                title="Errors in the registration form!",
                type="simple",
                items=self.errors,
                size_hint=[None, None],
                size=[300, 400],
            ).open()
            self.errors = []
            return

        if not DS.create_user(username, email_address, phone_number, password):
            MDDialog(
                title="Your registration has failed!",
                type="simple",
                size_hint=[None, None],
                size=[300, 400],
            ).open()
            return

        self.manager.current = "login"
        CustomSnackbar(text="Make sure you to check your email to confirm registration!").show()


class DogExpansionPanelContent(MDBoxLayout):
    dog_name: StringProperty()
    dog_description: StringProperty()

    dog: DogModel
    rebuild_dogs_list: Callable

    def __init__(self, dog: DogModel, rebuild_dogs_list_f: Callable, **kwargs):
        super().__init__(**kwargs)
        self.dog = dog
        self.rebuild_dogs_list = rebuild_dogs_list_f
        item = self.ids["dog_item"]
        item.text = dog.race
        item.secondary_text = f"{'She' if dog.sex is DogSex.FEMALE else 'He'}'s " \
                              f"{dog.age} {'years' if dog.age > 1 else 'year'} old"

    def delete_dog(self):
        DS.user.dogs.remove(self.dog)
        DS.update_user()
        dog_out.sm.get_screen("dog_out").create_dogs_list()
        self.rebuild_dogs_list()
        CustomSnackbar(text=f"{self.dog.name} has been removed :(").show()

    def show_delete_dog_dialog(self):
        ConfirmationDialog(lambda: self.delete_dog(), title=f"Do you really want to remove {self.dog.name}?").open()


class HomeScreen(MDScreen):
    hello_text = StringProperty()
    time = StringProperty()

    def __init__(self, **kw):
        super().__init__(**kw)
        self.hello_text = f"Hello {DS.user.username}!"
        Clock.schedule_interval(self.update_clock, 0.2)
        self.create_dogs_list()

    def update_clock(self, *largs, **kwargs):
        self.time = datetime.datetime.now().strftime("%H:%M:%S")

    def create_dogs_list(self):
        dogs_list = self.ids["dogs_list"]
        dogs_list.clear_widgets()
        add_a_dog = OneLineAvatarIconListItem(
            text="Add a new dog!",
            on_release=lambda x: self.show_add_dog_dialog(),
        )
        add_a_dog.add_widget(IconLeftWidget(icon="plus", on_release=self.show_add_dog_dialog))
        dogs_list.add_widget(add_a_dog)
        for dog in DS.user.dogs:
            dogs_list.add_widget(
                MDExpansionPanel(
                    icon="dog-side",
                    content=DogExpansionPanelContent(dog, self.create_dogs_list),
                    panel_cls=MDExpansionPanelOneLine(text=dog.name)
                ),
            )

    @staticmethod
    def show_logout_dialog():
        ConfirmationDialog(lambda: dog_out.sm.set_current("login"), yes_text="LOGOUT").open()

    def show_add_dog_dialog(self, *largs, **kwargs):
        DogCreateDialog(self.create_dogs_list).open()


class DogCreateDialog(MDDialog):
    rebuild_dogs_list: Callable

    def __init__(self, rebuild_dogs_list_f: Callable, **kwargs):
        self.dog_create_content = DogCreateContent()
        self.rebuild_dogs_list = rebuild_dogs_list_f
        super().__init__(
            title="New dog!",
            type="custom",
            content_cls=self.dog_create_content,
            size_hint=[None, None],
            size=[300, 400],
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDFlatButton(text="ADD", on_release=self.add_dog),
            ], **kwargs)

    def add_dog(self, *largs, **kwargs):
        if not self.dog_create_content.validate():
            return
        dog = self.dog_create_content.to_dog_model()
        DS.user.dogs.append(dog)
        DS.update_user()
        self.rebuild_dogs_list()
        dog_out.sm.get_screen("dog_out").create_dogs_list()
        self.dismiss()
        CustomSnackbar(text=f"{dog.name} just joined the pack! Auu!").show()


class DogCreateContent(MDBoxLayout):
    name = StringProperty()
    race = StringProperty()
    age = StringProperty()
    sex_female_check = BooleanProperty()
    sex_male_check = BooleanProperty()

    def validate(self) -> bool:
        if not self.name or not self.race or not self.age:
            self.add_widget(DogCreateContentError(), 5)
            return False
        return True

    def to_dog_model(self) -> DogModel:
        return DogModel(
            uuid=uuid.uuid4().hex,
            name=self.name,
            race=self.race,
            age=int(self.age),
            sex=DogSex.FEMALE if self.sex_female_check else DogSex.MALE,
        )


class DogCreateContentError(MDGridLayout):
    pass


class DogOutListItem(TwoLineAvatarListItem):
    dog: DogModel
    dog_name = StringProperty()
    last_out = StringProperty()

    def __init__(self, dog: DogModel, **kwargs):
        self.dog = dog
        super().__init__(**kwargs)
        self.dog_name = dog.name
        Clock.schedule_interval(self.set_last_out, 60)
        self.set_last_out()

    def set_last_out(self, *largs, **kwargs):
        self.last_out = f"{'She' if self.dog.sex == DogSex.FEMALE else 'He'} " \
                        f"{self._last_out_str() if self.dog.last_out else 'was never out yet!'}"

    def _last_out_str(self) -> str:
        d = time.time() - self.dog.last_out
        hours = math.floor(d / 3600)
        minutes = math.floor(math.remainder(d, 3600) / 60)
        if minutes == 0 and hours == 0:
            return "was just taken out!"
        if hours == 0:
            return f"was last out {minutes} minute{'s' if minutes > 1 else ''} ago"
        return f"was last out {hours} hour{'s' if hours > 1 else ''} and {'s' if minutes > 1 else ''} minutes ago"


class CustomSnackbar(BaseSnackbar):
    text = StringProperty(None)

    def show(self):
        self.size_hint_x = (Window.width - (self.snackbar_x * 2)) / Window.width
        self.open()


class DogOutScreen(MDScreen):
    map: MapView
    selection_list: MDSelectionList

    def __init__(self, **kw):
        super().__init__(**kw)
        self.map = self.ids.map
        self.map.lat = geocoder.ip("me").lat
        self.map.lon = geocoder.ip("me").lng
        self.selection_list = self.ids.selection_list
        self.create_dogs_list()

    def create_dogs_list(self):
        self.selection_list.clear_widgets()
        for dog in DS.user.dogs:
            self.ids.selection_list.add_widget(DogOutListItem(dog))

    @staticmethod
    def show_logout_dialog():
        ConfirmationDialog(lambda: dog_out.sm.set_current("login"), yes_text="LOGOUT").open()

    def dog_out(self, *largs, **kwargs):
        selected_dogs = list(map(lambda x: x.instance_item.dog, self.selection_list.get_selected_list_items()))
        if len(selected_dogs) == 0:
            CustomSnackbar(text="You haven't selected any dogs :)").show()
            return
        now = time.time()
        for dog in selected_dogs:
            dog.last_out = now
        DS.update_user()
        self.create_dogs_list()
        CustomSnackbar(text=f"{len(selected_dogs)} dog{'s' if len(selected_dogs) > 1 else ''}"
                            f" {'s have' if len(selected_dogs) > 1 else 'has'} taken out!").show()


class ConfirmationDialog(MDDialog):

    def __init__(self, on_confirm_f: Callable, yes_text: str = "YES", no_text: str = "CANCEL",
                 title: str = "Are you sure?", **kwargs):
        super().__init__(
            title=title,
            size_hint=[None, None],
            size=[300, 400],
            buttons=[
                MDFlatButton(text=no_text, on_release=self.dismiss),
                MDFlatButton(text=yes_text, on_release=lambda x: self.on_confirm(on_confirm_f)),
            ], **kwargs)

    def on_confirm(self, on_confirm_f: Callable):
        on_confirm_f()
        self.dismiss()


class SM(ScreenManager):
    pre_auth_screens_dict: dict[str:MDScreen] = {
        "login": LoginScreen,
        "register": RegisterScreen,
    }

    post_auth_screens_dict: dict[str:MDScreen] = {
        "home": HomeScreen,
        "dog_out": DogOutScreen,
    }

    def __init__(self, current: str = "login", **kwargs):
        super().__init__(**kwargs)
        for name, screen in self.pre_auth_screens_dict.items():
            self.add_widget(screen(name=name))
        self.set_current(current)

    def post_auth_add_widgets(self):
        for name, screen in self.post_auth_screens_dict.items():
            if self.has_screen(name):
                self.remove_widget(self.get_screen(name))
            self.add_widget(screen(name=name))

    def set_current(self, current: str):
        self.current = current


class DogOut(MDApp):
    sm: ScreenManager
    kv_files_dir = "kv"

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Cyan"

        for f in listdir(self.kv_files_dir):
            Builder.load_file(f"{self.kv_files_dir}/{f}")

        self.sm = SM(current="login")
        return self.sm


dog_out = DogOut()
