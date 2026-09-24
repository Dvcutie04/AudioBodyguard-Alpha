from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class SelectionMenuItem:
    identifier: str
    label: str
    accessibility_identifier: str


class TVSelectionFeedbackMenu:
    """Menu interaction state; rendering and gesture detection belong to the UI."""

    def __init__(self,store,profile_id,device_id,*,approved):
        if type(approved) is not bool:
            raise ValueError("approval must be boolean")
        for identifier in (profile_id,device_id):
            if type(identifier) is not str or not identifier.strip() or identifier!=identifier.strip():
                raise ValueError("invalid feedback identifier")
        self._store=store
        self._profile_id=profile_id
        self._device_id=device_id
        self._approved=approved
        self._closed=False
        self._lock=Lock()
        if approved:
            options=(("rating","Good choice"),("keep_this_tv","Keep this TV"))
        else:
            options=(("rating","Bad choice"),("never_switch_automatically","Never switch automatically"))
        prefix="tv_selection_thumbs_up_" if approved else "tv_selection_thumbs_down_"
        self._items=tuple(SelectionMenuItem(identifier,label,prefix+identifier) for identifier,label in options)

    @property
    def items(self):
        return self._items

    def dismiss(self):
        with self._lock:
            self._closed=True

    def select(self,identifier):
        with self._lock:
            if self._closed:
                raise ValueError("menu is closed")
            if type(identifier) is not str or identifier not in tuple(item.identifier for item in self._items):
                raise ValueError("option is not available in this menu")
            self._store.record_feedback(self._profile_id,device_id=self._device_id,approved=self._approved,reason=identifier)
            self._closed=True
