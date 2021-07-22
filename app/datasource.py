import json
from dataclasses import dataclass
from enum import Enum

import pyrebase
from pyrebase.pyrebase import Auth, Database


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


class DogSex(str, Enum):
    FEMALE: str = "female"
    MALE: str = "male"


@dataclass
class DogModel(Serializable):
    uuid: str
    name: str
    race: str
    age: int
    sex: str
    last_out: float = .0

    @classmethod
    def from_json(cls, raw: any):
        return cls(**raw)


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
    user: UserModel

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
            user_model = UserModel(user_auth.uuid, username, email_address, phone_number, [])
            self.db.child("users").child(user_model.uuid).set(user_model.to_json(), user_auth.token)
            return True
        except Exception as e:
            print(e)
            return False

    def login_user(self, email_address: str, password: str) -> bool:
        try:
            user_auth = self.auth.sign_in_with_email_and_password(email_address, password)
            self.user_auth = UserAuth(user_auth)
            users = self.db.child("users").get(self.user_auth.token).val()
            for u in users.values():
                um = UserModel.from_json(u)
                if email_address == um.email_address:
                    um.dogs = [DogModel.from_json(dog) for dog in um.dogs]
                    self.user = um
                    return True
            return False
        except Exception as e:
            print(e)
            return False

    def update_user(self) -> bool:
        try:
            j = self.user.to_json()
            self.db.child("users").child(self.user.uuid).set(j)
            return True
        except Exception as e:
            print(e)
            return False

    def refresh_session(self) -> bool:
        try:
            user_auth = self.auth.refresh(self.user_auth.refresh_token)
            self.user_auth = UserAuth(user_auth)
            return True
        except Exception as e:
            print(e)
            return False


DS = Datasource()
