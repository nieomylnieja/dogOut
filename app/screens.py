import re
from typing import Callable

from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager

from kivymd.theming import ThemableBehavior
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineIconListItem, MDList, OneLineListItem

from email_validator import validate_email, EmailNotValidError

from app.utils import Singleton
from app.datasource import DS, User


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

        MDDialog(
            title="Logout",
            content="",
            type="simple",
            size_hint=[None, None],
            size=[300, 400],
        ).open()
        self.manager.current = "login"


class HomeScreen(MDScreen):
    hello_text: StringProperty()

    def __init__(self, **kw):
        super().__init__(**kw)
        self.hello_text.title = f"Hello {User.username}!"
        for dog in User.dogs:
            self.ids["dogs_list"].add_widget(
                OneLineListItem(text=dog.name)
            )


class DogOutScreen(MDScreen):
    pass


class DrawerList(ThemableBehavior, MDList):
    def set_color_item(self, instance_item):
        '''Called when tap on a menu item.'''

        # Set the color of the icon and text for the menu item.
        for item in self.children:
            if item.text_color == self.theme_cls.primary_color:
                item.text_color = self.theme_cls.text_color
                break
        instance_item.text_color = self.theme_cls.primary_color


class LogoutDialog(MDDialog):

    def __init__(self, **kwargs):
        super().__init__(
            title="Are you sure?",
            size_hint=[None, None],
            size=[300, 400],
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDFlatButton(text="LOGOUT", on_release=lambda x: SM().set_current("login")),
            ], **kwargs)


class SM(ScreenManager):
    __metaclass__ = Singleton

    screens_dict: dict[str:MDScreen] = {
        "login": LoginScreen,
        "register": RegisterScreen,
        "home": HomeScreen,
        "dog_out": DogOutScreen,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for name, screen in self.screens_dict.items():
            self.add_widget(screen(name=name))
        self.set_current("home")

    def set_current(self, current: str):
        self.current = current
