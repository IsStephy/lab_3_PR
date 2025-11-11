from typing import Optional


class Card:
    def __init__(self, string_value: str, face_down: bool = True,
                 face_up: bool = False, removed: bool = False, player_id: Optional[str] = None) -> None:
        self._string_value = string_value
        self._face_down = face_down
        self._face_up = face_up
        self._removed = removed
        self._player_id = player_id
        self._controller: Optional[str] = None
        self._matched: bool = False

    def checkRep(self) -> None:
        assert self._string_value is not None and len(self._string_value) > 0, \
            "Card string_value must be non-empty"

        if self._removed:
            assert not self._face_up, "Removed card cannot be face up"
            assert not self._face_down, "Removed card cannot be face down"
            assert self._controller is None, "Removed card cannot be controlled"
            assert not self._matched, "Removed card cannot be matched"
        elif self._face_up:
            assert not self._face_down, "Card cannot be both face up and face down"
        elif self._face_down:
            assert not self._face_up, "Card cannot be both face up and face down"
            assert self._controller is None, "Face down card cannot be controlled"
        else:
            assert False, "Card is in an invalid state (not up, down, or removed)"

        if self._controller is not None:
            assert self._face_up, "Controlled card must be face up"

        if self._matched:
            assert self._face_up, "Matched card must be face up"
            assert not self._removed, "Matched card cannot be already removed"

    @property
    def string_value(self) -> str:
        return self._string_value

    @string_value.setter
    def string_value(self, value: str):
        self._string_value = value

    @property
    def face_down(self) -> bool:
        return self._face_down

    @face_down.setter
    def face_down(self, value: bool):
        self._face_down = value

    @property
    def face_up(self) -> bool:
        return self._face_up

    @face_up.setter
    def face_up(self, value: bool):
        self._face_up = value

    @property
    def removed(self) -> bool:
        return self._removed

    @removed.setter
    def removed(self, value: bool):
        self._removed = value

    @property
    def player_id(self) -> Optional[str]:
        return self._player_id

    @player_id.setter
    def player_id(self, value: Optional[str]):
        self._player_id = value

    @property
    def controller(self) -> Optional[str]:
        return self._controller

    @controller.setter
    def controller(self, value: Optional[str]):
        self._controller = value

    @property
    def matched(self) -> bool:
        return self._matched

    @matched.setter
    def matched(self, value: bool):
        self._matched = value

    def __str__(self) -> str:
        if self.removed:
            return "_"
        elif self.face_up:
            return self.string_value
        else:
            return "*"