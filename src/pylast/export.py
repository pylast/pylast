#
# pylast -
#     A Python interface to Last.fm and Libre.fm
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# https://github.com/pylast/pylast
"""
Export a user's scrobbles and loved tracks to JSON Lines files.

    from pylast.export import export_scrobbles

    network = pylast.LastFMNetwork(api_key=API_KEY)
    network.enable_rate_limit()
    user = network.get_user("RJ")
    export_scrobbles(user, "RJ.jsonl")

JSON Lines (https://jsonlines.org/) has one JSON object per line, UTF-8
encoded, with the fields of Scrobble (or Love). It is appendable, so an
interrupted export can be resumed, and it keeps the distinction between
missing and empty values. Convert it to anything else afterwards.

Files are written newest scrobble first, the order the Last.fm API returns
them. Resuming continues backwards from the oldest scrobble already in the
file; it never fetches scrobbles newer than the first line. To pick up new
scrobbles, export to a new file with time_from set to the newest timestamp.
"""

from __future__ import annotations

import collections
import contextlib
import dataclasses
import json
import os

from . import PyLastError, Scrobble, User

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import IO, Any, TypeGuard

    ProgressCallback = Callable[[int, int, int, int], None]

__all__ = ["ResumeError", "export_loved", "export_scrobbles"]

_SCROBBLE_FIELDS = frozenset(f.name for f in dataclasses.fields(Scrobble))
# The fields of the first release; fields added later are optional when
# reading, so older export files stay resumable.
_REQUIRED_FIELDS = frozenset(
    {
        "timestamp",
        "artist",
        "title",
        "album",
        "artist_mbid",
        "track_mbid",
        "album_mbid",
        "url",
    }
)


class ResumeError(PyLastError):
    """Raised when an existing export file cannot be resumed."""


def export_scrobbles(
    user: User,
    path: str | os.PathLike[str] | IO[str],
    *,
    time_from: int | None = None,
    time_to: int | None = None,
    resume: bool = True,
    progress: ProgressCallback | None = None,
) -> int:
    """
    Writes every scrobble of user to path as JSON Lines, newest first, and
    returns the number of scrobbles written by this call.

    path may also be an open text file, in which case resume is ignored.

    time_from and time_to are Unix timestamps (UTC seconds), as for
    User.get_scrobbles().

    If resume is true and path already holds scrobbles, the export continues
    from the oldest one in the file instead of starting again: time_to is
    capped at that timestamp and scrobbles already present are skipped, so
    re-running after an interruption appends only what is missing. A torn
    final line from an interrupted write is removed first. ResumeError is
    raised if the file is not a scrobbles export, if time_to is earlier than
    the oldest scrobble in it (which would leave a gap), or if time_from is
    not earlier (the file is newest first, so it can only grow backwards).

    progress is called after every page, once it has been flushed to disk,
    with (page, total_pages, scrobbles_fetched_so_far, total_scrobbles).
    """
    skip: collections.Counter[tuple] = collections.Counter()
    append = False

    if resume and _is_path(path):
        tail = _read_tail(path)
        if tail is not None:
            oldest, skip = tail
            if time_to is not None and time_to < oldest:
                msg = (
                    f"time_to {time_to} is earlier than the oldest scrobble "
                    f"({oldest}) in {os.fspath(path)}, which would leave a gap; "
                    "export to a new file instead"
                )
                raise ResumeError(msg)
            if time_from is not None and time_from >= oldest:
                msg = (
                    f"{os.fspath(path)} already holds scrobbles back to {oldest} "
                    "and can only be extended backwards; export newer scrobbles "
                    "to a new file instead"
                )
                raise ResumeError(msg)
            time_to = oldest + 1
            append = True

    written = 0
    with _open_writer(path, append=append) as writer:
        on_page = _flush_then(writer, progress)
        for scrobble in user.get_scrobbles(time_from, time_to, progress=on_page):
            if skip[key := _scrobble_key(scrobble)] > 0:
                skip[key] -= 1  # already in the file (once per identical copy)
                continue
            writer.write(scrobble.to_dict())
            written += 1

    return written


def export_loved(
    user: User,
    path: str | os.PathLike[str] | IO[str],
    *,
    progress: ProgressCallback | None = None,
) -> int:
    """
    Writes every track user has loved to path as JSON Lines, most recently
    loved first, and returns the number written.

    An existing file is overwritten: the loved tracks API has no time range,
    so there is nothing to resume. path may also be an open text file.

    progress is called after every page, once it has been flushed to disk,
    with (page, total_pages, fetched_so_far, total).
    """
    written = 0
    with _open_writer(path, append=False) as writer:
        on_page = _flush_then(writer, progress)
        for love in user.get_loves(progress=on_page):
            writer.write(love.to_dict())
            written += 1

    return written


def _is_path(path: object) -> TypeGuard[str | os.PathLike[str]]:
    return isinstance(path, (str, os.PathLike))


def _flush_then(
    writer: _JsonlWriter, progress: ProgressCallback | None
) -> ProgressCallback:
    """Returns a page callback that flushes the file before reporting progress."""

    def on_page(page: int, total_pages: int, count: int, total: int) -> None:
        writer.flush()
        if progress is not None:
            progress(page, total_pages, count, total)

    return on_page


def _scrobble_key(scrobble: Scrobble) -> tuple:
    return scrobble.timestamp, scrobble.artist, scrobble.title, scrobble.album


class _JsonlWriter:
    def __init__(self, file: IO[str]) -> None:
        self._file = file

    def write(self, record: dict[str, Any]) -> None:
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def flush(self) -> None:
        self._file.flush()


@contextlib.contextmanager
def _open_writer(
    path: str | os.PathLike[str] | IO[str], *, append: bool
) -> Iterator[_JsonlWriter]:
    """Opens path for writing. An open file object is used as is and left open."""
    if _is_path(path):
        file = open(  # noqa: SIM115
            path,
            "a" if append else "w",
            encoding="utf-8",
            newline="\n",
        )
        close = True
    else:
        file = path  # type: ignore[assignment]
        close = False

    writer = _JsonlWriter(file)
    try:
        yield writer
    finally:
        writer.flush()
        if close:
            file.close()


def _parse_scrobble(line: str) -> Scrobble:
    """Parses one export line; raises ValueError or TypeError if it is not one."""
    record = json.loads(line)
    if not isinstance(record, dict) or not (
        _REQUIRED_FIELDS <= set(record) <= _SCROBBLE_FIELDS
    ):
        msg = "not the fields of a scrobble"
        raise ValueError(msg)
    if not isinstance(record["timestamp"], int) or isinstance(
        record["timestamp"], bool
    ):
        msg = "timestamp is not an integer"
        raise TypeError(msg)
    for name, value in record.items():
        if name == "timestamp":
            continue
        if not isinstance(value, str) and (
            value is not None or name in ("artist", "title")
        ):
            msg = f"{name} is not a string"
            raise TypeError(msg)
    return Scrobble(**record)


def _read_tail(
    path: str | os.PathLike[str],
) -> tuple[int, collections.Counter[tuple]] | None:
    """
    Returns (oldest_timestamp, counted keys of records with timestamp <=
    oldest + 1) from an existing export, or None if the file is missing or
    empty.

    Raises ResumeError if the file is not an export. The one exception is a
    torn final line left by an interrupted write: a last line with no newline
    that is not a record is removed.
    """
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None

    oldest: int | None = None
    candidates: list[tuple] = []
    offset = 0
    torn = False
    try:
        with open(path, encoding="utf-8", newline="") as f:
            for number, line in enumerate(f, 1):
                if not line.strip():
                    offset += len(line.encode("utf-8"))
                    continue
                try:
                    scrobble = _parse_scrobble(line)
                except (ValueError, TypeError) as e:
                    if not line.endswith("\n"):
                        torn = True
                        break
                    msg = (
                        f"{os.fspath(path)}, line {number}: not a scrobble record ({e})"
                    )
                    raise ResumeError(msg) from None
                offset += len(line.encode("utf-8"))
                key = _scrobble_key(scrobble)
                if oldest is None or scrobble.timestamp < oldest:
                    oldest = scrobble.timestamp
                    candidates = [c for c in candidates if c[0] <= oldest + 1]
                if scrobble.timestamp <= oldest + 1:
                    candidates.append(key)
    except UnicodeDecodeError as e:
        msg = f"{os.fspath(path)} is not UTF-8 text ({e})"
        raise ResumeError(msg) from None

    if torn:
        # Drop the torn final line left by an interrupted write.
        with open(path, "r+b") as f:
            f.truncate(offset)
    if oldest is None:
        if torn:
            return None  # the torn line was the only one: start afresh
        msg = f"{os.fspath(path)} is not empty but contains no scrobbles"
        raise ResumeError(msg)
    if not torn and not line.endswith("\n"):
        # A complete final record lacking its newline: add one before appending.
        with open(path, "ab") as f:
            f.write(b"\n")
    return oldest, collections.Counter(candidates)
