import re
from enum import Enum, auto

URL_REGEX = re.compile(
    "(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
)
LYRICS_URL = "https://some-random-api.ml/lyrics?title="
HZ_BANDS = (
    20,
    40,
    63,
    100,
    150,
    250,
    400,
    450,
    630,
    1000,
    1600,
    2500,
    4000,
    10000,
    16000,
)
TIME_REGEX = re.compile("([0-9]{1,2})[:ms](([0-9]{1,2})s?)?")


OPTIONS = {
    "1️⃣": 1,
    "2️⃣": 2,
    "3️⃣": 3,
    "4️⃣": 4,
    "5️⃣": 5,
}


class RepeatMode(Enum):
    NONE = auto()
    ONE = auto()
    ALL = auto()
