"""Helpers for carrying the current user's identity into background threads.

`contextvars` are NOT inherited by `threading.Thread` targets, so a worker
spawned from a request must explicitly re-establish the user context before it
touches the database. Capture the id with `current_uid()` while still on the
request thread, then wrap the thread target with `run_with_user(uid, fn)`.
"""

from db import current_user_id


def current_uid():
    """The user id for the current request/thread context (or None)."""
    return current_user_id.get()


def run_with_user(uid, fn, *args, **kwargs):
    """Wrap `fn` so it runs with `current_user_id` set to `uid`.

    Returns a zero-arg callable suitable for use as a Thread target.
    """
    def _wrapped():
        token = current_user_id.set(uid)
        try:
            return fn(*args, **kwargs)
        finally:
            current_user_id.reset(token)
    return _wrapped
