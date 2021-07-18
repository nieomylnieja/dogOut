import json
from dataclasses import dataclass

import pyrebase
from pyrebase.pyrebase import Auth, Database
from requests import HTTPError


@dataclass
class UserAuth:
    uuid: str
    token: str
    refresh_token: str

    def __init__(self, user_auth: dict):
        self.uuid = user_auth["localId"]
        self.token = user_auth["idToken"]
        self.refresh_token = user_auth["refreshToken"]


class Serializable:

    def to_json(self) -> any:
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, raw: any):
        return cls(**json.loads(raw))


@dataclass
class DogModel(Serializable):
    uuid: str
    name: str
    race: str


@dataclass
class UserModel(Serializable):
    uuid: str
    username: str
    email_address: str
    phone_number: str
    dogs: list[DogModel]


@dataclass
class Datasource:
    auth: Auth
    db: Database

    user_auth: UserAuth
    user_model: UserModel

    def __init__(self):
        with open("config.local.json") as f:
            config = json.load(f)
            firebase = pyrebase.initialize_app(config)
        self.auth = firebase.auth()
        self.db = firebase.database()

    def create_user(self, username: str, email_address: str, phone_number: str, password: str) -> bool:
        try:
            user_auth = UserAuth(self.auth.create_user_with_email_and_password(email_address, password))
            self.auth.send_email_verification(user_auth.token)
            user_model = UserModel(user_auth.uuid, username, email_address, phone_number)
            self.db.child("users").push(user_model.to_json(), user_auth.token)
            return True
        except HTTPError:
            return False

    def login_user(self, email_address: str, password: str) -> bool:
        try:
            user_auth = self.auth.sign_in_with_email_and_password(email_address, password)
            self.user_auth = UserAuth(user_auth)
            return True
        except HTTPError:
            return False

    def refresh_session(self) -> bool:
        try:
            user_auth = self.auth.refresh(self.user_auth.refresh_token)
            self.user_auth = UserAuth(user_auth)
            return True
        except HTTPError:
            return False


DS = Datasource()
User = UserModel("123", "Benson", "test@gmail.com", "509792751",
                 [DogModel("1", "Bernie", "Husky"), DogModel("2", "Growler", "Shepherd")])
