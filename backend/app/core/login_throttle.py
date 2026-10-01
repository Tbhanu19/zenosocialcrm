"""In-process limit for failed login attempts.

This is a single-process guard, not a distributed lockout service. It keeps
password hashing from being used as an unbounded cost and does not store
passwords.
"""

import threading
import time

from app.core.exceptions import TooManyRequestsError


class LoginThrottle:
    def __init__(self) -> None:
        self.max_identity_failures = 8
        self.max_address_failures = 40
        self.window_seconds = 900
        self._identity: dict[str, list[float]] = {}
        self._address: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._identity.clear()
            self._address.clear()

    def check(self, address: str, email: str) -> None:
        now = time.monotonic()
        with self._lock:
            identity_key = self._identity_key(address, email)
            identity_failures = self._recent(self._identity, identity_key, now)
            address_failures = self._recent(self._address, address, now)
            if (
                len(identity_failures) >= self.max_identity_failures
                or len(address_failures) >= self.max_address_failures
            ):
                raise TooManyRequestsError()

    def record_failure(self, address: str, email: str) -> None:
        now = time.monotonic()
        with self._lock:
            identity_key = self._identity_key(address, email)
            identity_failures = self._recent(self._identity, identity_key, now)
            identity_failures.append(now)
            self._identity[identity_key] = identity_failures
            address_failures = self._recent(self._address, address, now)
            address_failures.append(now)
            self._address[address] = address_failures

    def record_success(self, address: str, email: str) -> None:
        with self._lock:
            self._identity.pop(self._identity_key(address, email), None)

    def _identity_key(self, address: str, email: str) -> str:
        return f"{address}|{email.strip().lower()}"

    def _recent(self, store: dict[str, list[float]], key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        recent = [stamp for stamp in store.get(key, []) if stamp >= cutoff]
        if recent:
            store[key] = recent
        else:
            store.pop(key, None)
        return recent


login_throttle = LoginThrottle()
