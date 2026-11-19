"""
Tests for exporting scrobbles and loved tracks.
"""

from __future__ import annotations

import datetime as dt
import io
import itertools
import json
import re
from unittest.mock import Mock, patch
from xml.dom import minidom
from xml.sax.saxutils import escape

import pytest

import pylast
from pylast.__main__ import _parse_when, main
from pylast.export import ResumeError, export_loved, export_scrobbles

from .test_pylast import TestPyLastWithLastFm


def _track(
    timestamp: int,
    artist: str = "Artist",
    title: str = "Song",
    album: str | None = "Album",
    artist_mbid: str = "",
    track_mbid: str = "",
    album_mbid: str = "",
    *,
    nowplaying: bool = False,
    dated: bool = True,
) -> str:
    attrs = ' nowplaying="true"' if nowplaying else ""
    date = (
        f'<date uts="{timestamp}">16 Nov 2023</date>'
        if dated and not nowplaying
        else ""
    )
    return (
        f"<track{attrs}>"
        f'<artist mbid="{artist_mbid}">{escape(artist)}</artist>'
        f"<name>{escape(title)}</name>"
        f"<mbid>{track_mbid}</mbid>"
        f'<album mbid="{album_mbid}">{escape(album or "")}</album>'
        f"<url>https://www.last.fm/music/{escape(artist)}/_/{escape(title)}</url>"
        f"{date}</track>"
    )


def _recent(
    tracks: list[str],
    page: int = 1,
    total_pages: int = 1,
    total: int | None = None,
    attr: str = "totalPages",
) -> bytes:
    total = len(tracks) if total is None else total
    return (
        '<?xml version="1.0"?><lfm status="ok">'
        f'<recenttracks user="alice" page="{page}" perPage="200" '
        f'{attr}="{total_pages}" total="{total}">'
        + "".join(tracks)
        + "</recenttracks></lfm>"
    ).encode()


def _loved_track(
    timestamp: int,
    artist: str = "Artist",
    title: str = "Song",
    artist_mbid: str = "",
    track_mbid: str = "",
) -> str:
    return (
        f"<track><name>{escape(title)}</name><mbid>{track_mbid}</mbid>"
        f"<url>https://www.last.fm/music/{escape(artist)}/_/{escape(title)}</url>"
        f'<date uts="{timestamp}">04 Apr 2016</date>'
        f"<artist><name>{escape(artist)}</name><mbid>{artist_mbid}</mbid>"
        f"<url>https://www.last.fm/music/{escape(artist)}</url></artist>"
        "</track>"
    )


def _loved(tracks: list[str], page: int = 1, total_pages: int = 1) -> bytes:
    return (
        '<?xml version="1.0"?><lfm status="ok">'
        f'<lovedtracks user="alice" page="{page}" perPage="200" '
        f'totalPages="{total_pages}" total="{len(tracks)}">'
        + "".join(tracks)
        + "</lovedtracks></lfm>"
    ).encode()


LOGIN_REQUIRED_BODY = (
    b'<?xml version="1.0"?>'
    b'<lfm status="failed">'
    b'<error code="17">Login: User required to be logged in</error></lfm>'
)


def _ok(body: bytes) -> Mock:
    return Mock(status_code=200, read=Mock(return_value=body))


def _user() -> pylast.User:
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    return network.get_user("alice")


def _plain(text: str) -> str:
    """Strips the ANSI colours argparse adds on Python 3.14+ when FORCE_COLOR is set."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _first_track(body: bytes) -> minidom.Element:
    return minidom.parseString(body).getElementsByTagName("track")[0]


def _record(**overrides) -> bytes:
    """One export line, matching _track()'s defaults so resume keys line up."""
    record = pylast.Scrobble(300, "Artist", "Song", "Album").to_dict() | overrides
    return (json.dumps(record) + "\n").encode()


def _lines(*timestamps: int) -> bytes:
    return b"".join(_record(timestamp=t) for t in timestamps)


# Parsing


def test_extract_scrobble() -> None:
    # Arrange
    node = _first_track(
        _recent(
            [
                _track(
                    1230999581,
                    "Tricky",
                    "Overcome",
                    "Maxinquaye",
                    artist_mbid="5bf64d94",
                    track_mbid="48c62935",
                    album_mbid="1959f7a2",
                )
            ]
        )
    )

    # Act
    scrobble = pylast._extract_scrobble(node)

    # Assert
    assert scrobble == pylast.Scrobble(
        timestamp=1230999581,
        artist="Tricky",
        title="Overcome",
        album="Maxinquaye",
        artist_mbid="5bf64d94",
        track_mbid="48c62935",
        album_mbid="1959f7a2",
        url="https://www.last.fm/music/Tricky/_/Overcome",
    )
    assert scrobble.datetime == dt.datetime(2009, 1, 3, 16, 19, 41, tzinfo=dt.UTC)
    assert pylast.Scrobble(**scrobble.to_dict()) == scrobble


def test_extract_scrobble_empty_values_are_none() -> None:
    # Arrange
    node = _first_track(_recent([_track(1, "A & B", "Song", album=None)]))

    # Act
    scrobble = pylast._extract_scrobble(node)

    # Assert
    assert scrobble.artist == "A & B"
    assert scrobble.album is None
    assert scrobble.artist_mbid is None
    assert scrobble.track_mbid is None
    assert scrobble.album_mbid is None


def test_extract_love() -> None:
    # Arrange
    node = _first_track(
        _loved(
            [
                _loved_track(
                    1459767227,
                    "The Black Seeds",
                    "Fire",
                    artist_mbid="dc76f538",
                    track_mbid="6db5b17c",
                )
            ]
        )
    )

    # Act
    love = pylast._extract_love(node)

    # Assert
    assert love == pylast.Love(
        timestamp=1459767227,
        artist="The Black Seeds",
        title="Fire",
        artist_mbid="dc76f538",
        track_mbid="6db5b17c",
        url="https://www.last.fm/music/The Black Seeds/_/Fire",
    )
    assert pylast.Love(**love.to_dict()) == love


def test_extract_love_empty_mbids_are_none() -> None:
    # Arrange
    node = _first_track(_loved([_loved_track(1)]))

    # Act
    love = pylast._extract_love(node)

    # Assert
    assert love.artist_mbid is None
    assert love.track_mbid is None


# Fetching


def test_get_scrobbles_skips_now_playing_and_undated() -> None:
    # Arrange
    body = _recent(
        [
            _track(0, title="Now", nowplaying=True),
            _track(0, title="Undated", dated=False),
            _track(300, title="Played"),
        ]
    )

    # Act
    with patch("httpx2.Client.post", return_value=_ok(body)) as post:
        scrobbles = list(_user().get_scrobbles(time_to=1000))

    # Assert
    assert [s.title for s in scrobbles] == ["Played"]
    data = post.call_args.kwargs["data"]
    assert data["limit"] == "200"
    assert data["to"] == "1000"
    assert data["page"] == "1"
    assert "from" not in data


def test_get_scrobbles_defaults_time_to_to_now() -> None:
    # Arrange
    body = _recent([_track(300)])

    # Act
    with (
        patch("httpx2.Client.post", return_value=_ok(body)) as post,
        patch("pylast.time.time", return_value=1234.9),
    ):
        list(_user().get_scrobbles(time_from=100, page_size=50))

    # Assert
    data = post.call_args.kwargs["data"]
    assert data["to"] == "1234"
    assert data["from"] == "100"
    assert data["limit"] == "50"


@pytest.mark.parametrize(
    "pages, expected",
    [
        pytest.param(
            [[_track(300), _track(200)], [_track(200), _track(100)]],
            [300, 200, 100],
            id="boundary-repeat",
        ),
        pytest.param(
            [[_track(300), _track(200)], [_track(300), _track(100)]],
            [300, 200, 100],
            id="shifted-page-repeat",
        ),
        pytest.param(
            [[_track(300), _track(200)], [_track(250), _track(100)]],
            [300, 200, 250, 100],
            id="unseen-out-of-order-item-kept",
        ),
        pytest.param(
            [[_track(200, title="A"), _track(200, title="B"), _track(200, title="A")]],
            [200, 200, 200],
            id="identical-items-within-a-page-kept",
        ),
        pytest.param(
            # page 1 ends with two identical scrobbles; page 2 re-serves them
            # and then has a third genuine copy
            [
                [_track(300), _track(200), _track(200)],
                [_track(200)] * 3 + [_track(100)],
            ],
            [300, 200, 200, 200, 100],
            id="identical-repeats-counted",
        ),
    ],
)
def test_get_scrobbles_dedupes_across_pages(pages, expected) -> None:
    # Arrange
    total = sum(len(page) for page in pages)
    responses = [
        _ok(_recent(tracks, page=n, total_pages=len(pages), total=total))
        for n, tracks in enumerate(pages, 1)
    ]

    # Act
    with patch("httpx2.Client.post", side_effect=responses) as post:
        scrobbles = list(_user().get_scrobbles(time_to=1000))

    # Assert
    assert [s.timestamp for s in scrobbles] == expected
    assert post.call_count == len(pages)


@pytest.mark.parametrize(
    "responses, posts, sleeps, error",
    [
        pytest.param(
            [Mock(status_code=503), Mock(status_code=503), _ok(_recent([_track(1)]))],
            3,
            [1, 2],
            None,
            id="transient-errors-then-ok",
        ),
        pytest.param(
            [Mock(status_code=503)] * 8,
            8,
            [1, 2, 4, 8, 16, 32, 60],
            "503",
            id="gives-up-after-eight-tries",
        ),
        pytest.param(
            [_ok(LOGIN_REQUIRED_BODY)], 1, [], "17", id="login-required-not-retried"
        ),
    ],
)
def test_get_scrobbles_retries_with_backoff(responses, posts, sleeps, error) -> None:
    with (
        patch("httpx2.Client.post", side_effect=responses) as post,
        patch("pylast.time.sleep") as sleep,
    ):
        if error is None:
            assert len(list(_user().get_scrobbles(time_to=1000))) == 1
        else:
            with pytest.raises(pylast.WSError) as excinfo:
                list(_user().get_scrobbles(time_to=1000))
            assert str(excinfo.value.get_id()) == error

    assert post.call_count == posts
    assert [c.args[0] for c in sleep.call_args_list] == sleeps


@pytest.mark.parametrize(
    "body, expected",
    [
        pytest.param(
            _recent([_track(1)], attr="totalpages"), [1], id="libre.fm-casing"
        ),
        pytest.param(
            # Last.fm reports totalPages="0" for an empty history, but may still
            # include a now playing track
            _recent([_track(0, nowplaying=True)], total_pages=0, total=0),
            [],
            id="empty-history",
        ),
    ],
)
def test_get_scrobbles_odd_pages(body, expected) -> None:
    with patch("httpx2.Client.post", return_value=_ok(body)) as post:
        scrobbles = list(_user().get_scrobbles(time_to=1000))

    assert [s.timestamp for s in scrobbles] == expected
    assert post.call_count == 1


def test_get_scrobbles_reports_progress_per_page() -> None:
    # Arrange
    pages = [
        _ok(_recent([_track(400), _track(300)], page=1, total_pages=2, total=4)),
        _ok(_recent([_track(200), _track(100)], page=2, total_pages=2, total=4)),
    ]
    progress = Mock()

    # Act
    with patch("httpx2.Client.post", side_effect=pages):
        list(_user().get_scrobbles(time_to=1000, progress=progress))

    # Assert
    assert [c.args for c in progress.call_args_list] == [(1, 2, 2, 4), (2, 2, 4, 4)]


def test_get_loves() -> None:
    # Arrange
    pages = [
        _ok(_loved([_loved_track(300, title="A")], page=1, total_pages=2)),
        _ok(_loved([_loved_track(300, title="A"), _loved_track(200, title="B")], 2, 2)),
    ]
    progress = Mock()

    # Act
    with patch("httpx2.Client.post", side_effect=pages) as post:
        loves = list(_user().get_loves(page_size=1, progress=progress))

    # Assert
    assert [(love.timestamp, love.title) for love in loves] == [(300, "A"), (200, "B")]
    assert post.call_args_list[0].kwargs["data"]["limit"] == "1"
    assert progress.call_count == 2


# Exporting


def test_export_scrobbles_jsonl(tmp_path) -> None:
    # Arrange
    path = tmp_path / "alice.jsonl"
    body = _recent([_track(300, "Björk", "Jóga", album=None), _track(200)])

    # Act
    with patch("httpx2.Client.post", return_value=_ok(body)):
        written = export_scrobbles(_user(), path, time_to=1000)

    # Assert
    assert written == 2
    raw = path.read_bytes()
    assert "Björk".encode() in raw
    assert raw.endswith(b"\n")
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert [r["timestamp"] for r in records] == [300, 200]
    assert records[0]["album"] is None
    assert pylast.Scrobble(**records[0]).title == "Jóga"


def test_export_scrobbles_to_file_object() -> None:
    # Arrange
    buffer = io.StringIO()
    body = _recent([_track(300)])

    # Act
    with patch("httpx2.Client.post", return_value=_ok(body)):
        written = export_scrobbles(_user(), buffer, time_to=1000)

    # Assert
    assert written == 1
    assert json.loads(buffer.getvalue())["timestamp"] == 300


@pytest.mark.parametrize(
    "existing, page, kwargs, written, timestamps, to",
    [
        pytest.param(
            _lines(300, 200)
            + b"\n",  # blank lines, as from hand editing, are tolerated
            [200, 195],
            {"time_to": 5000},
            1,
            [300, 200, 195],
            "201",
            id="continues-from-oldest",
        ),
        pytest.param(_lines(300, 200), [200], {}, 0, [300, 200], "201", id="complete"),
        pytest.param(
            _lines(300, 200) + b'{"timestamp": 19',
            [195],
            {},
            1,
            [300, 200, 195],
            "201",
            id="torn-last-line-dropped",
        ),
        pytest.param(
            _lines(300, 200).rstrip(b"\n"),
            [195],
            {},
            1,
            [300, 200, 195],
            "201",
            id="unterminated-last-line-completed",
        ),
        pytest.param(
            b'{"timestamp": 30',
            [300],
            {"time_to": 1000},
            1,
            [300],
            "1000",
            id="only-line-torn-starts-afresh",
        ),
        pytest.param(
            _lines(300, 200),
            [200, 200, 195],
            {},
            2,
            [300, 200, 200, 195],
            "201",
            id="identical-copy-skipped-once",
        ),
        pytest.param(
            _lines(300, 200),
            [100],
            {"resume": False, "time_to": 1000},
            1,
            [100],
            "1000",
            id="no-resume-overwrites",
        ),
    ],
)
def test_export_scrobbles_resume(
    tmp_path, existing, page, kwargs, written, timestamps, to
) -> None:
    # Arrange
    path = tmp_path / "alice.jsonl"
    path.write_bytes(existing)
    body = _recent([_track(t) for t in page])

    # Act
    with patch("httpx2.Client.post", return_value=_ok(body)) as post:
        assert export_scrobbles(_user(), path, **kwargs) == written

    # Assert
    assert post.call_args.kwargs["data"]["to"] == to
    assert path.read_bytes().endswith(b"\n")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert [json.loads(line)["timestamp"] for line in lines] == timestamps


@pytest.mark.parametrize(
    "content, message",
    [
        pytest.param(
            _record().replace(b'"title"', b'"nope"'),
            r"alice\.jsonl, line 1: not a scrobble record",
            id="wrong-field-name",
        ),
        pytest.param(
            _record(timestamp="300"), "timestamp is not an integer", id="str-timestamp"
        ),
        pytest.param(
            _record(timestamp=None), "timestamp is not an integer", id="null-timestamp"
        ),
        pytest.param(
            _record(timestamp=300.5),
            "timestamp is not an integer",
            id="float-timestamp",
        ),
        pytest.param(_record(artist=None), "artist is not a string", id="null-artist"),
        pytest.param(_record(album=1), "album is not a string", id="int-album"),
        pytest.param(
            (json.dumps(pylast.Love(300, "Artist", "Song").to_dict()) + "\n").encode(),
            "not the fields of a scrobble",
            id="loved-tracks-file",
        ),
        pytest.param(
            b"timestamp,artist,title\n300,Artist,Song\n",
            "not a scrobble record",
            id="csv-file",
        ),
        pytest.param(
            b"timestamp,artist,title\n300,Artist,Song",
            "not a scrobble record",
            id="csv-file-without-final-newline",
        ),
        pytest.param(b"\xff\xfe not text\n", "not UTF-8", id="binary-file"),
        pytest.param(b"  \n\t", "contains no scrobbles", id="whitespace-only"),
    ],
)
def test_export_scrobbles_resume_rejects_bad_files(tmp_path, content, message) -> None:
    # Arrange
    path = tmp_path / "alice.jsonl"
    path.write_bytes(content)

    # Act
    with patch("httpx2.Client.post") as post, pytest.raises(ResumeError, match=message):
        export_scrobbles(_user(), path)

    # Assert: nothing fetched, file left exactly as it was
    assert post.call_count == 0
    assert path.read_bytes() == content


@pytest.mark.parametrize(
    "kwargs, message",
    [
        pytest.param({"time_to": 100}, "would leave a gap", id="time_to-before-oldest"),
        pytest.param(
            {"time_from": 250}, "export newer scrobbles to a new file", id="time_from"
        ),
    ],
)
def test_export_scrobbles_resume_rejects_time_range(tmp_path, kwargs, message) -> None:
    # Arrange
    path = tmp_path / "alice.jsonl"
    path.write_bytes(_lines(300, 200))

    # Act
    with patch("httpx2.Client.post") as post, pytest.raises(ResumeError, match=message):
        export_scrobbles(_user(), path, **kwargs)

    # Assert
    assert post.call_count == 0
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_export_scrobbles_resume_accepts_older_files_missing_new_fields(tmp_path):
    # Arrange: simulate a file written before a (hypothetical) new optional field
    path = tmp_path / "alice.jsonl"
    record = pylast.Scrobble(300, "Artist", "Song").to_dict()
    with patch("pylast.export._SCROBBLE_FIELDS", frozenset(record) | {"newer"}):
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        body = _recent([_track(200)])

        # Act
        with patch("httpx2.Client.post", return_value=_ok(body)):
            written = export_scrobbles(_user(), path)

    # Assert
    assert written == 1


def test_export_scrobbles_flushes_before_progress(tmp_path) -> None:
    # Arrange
    path = tmp_path / "alice.jsonl"
    pages = [
        _ok(_recent([_track(300)], page=1, total_pages=2, total=2)),
        _ok(_recent([_track(200)], page=2, total_pages=2, total=2)),
    ]
    seen: list[int] = []

    def progress(page: int, total_pages: int, count: int, total: int) -> None:
        seen.append(len(path.read_text(encoding="utf-8").splitlines()))

    # Act
    with patch("httpx2.Client.post", side_effect=pages):
        export_scrobbles(_user(), path, time_to=1000, progress=progress)

    # Assert
    assert seen == [1, 2]


def test_export_loved_overwrites(tmp_path) -> None:
    # Arrange
    path = tmp_path / "alice-loved.jsonl"
    path.write_text("stale\n", encoding="utf-8")
    body = _loved([_loved_track(300, title="A"), _loved_track(200, title="B")])

    # Act
    with patch("httpx2.Client.post", return_value=_ok(body)):
        written = export_loved(_user(), path)

    # Assert
    assert written == 2
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert [r["title"] for r in records] == ["A", "B"]
    assert list(records[0]) == [
        "timestamp",
        "artist",
        "title",
        "artist_mbid",
        "track_mbid",
        "url",
    ]


# Command line


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1700000000", 1700000000),
        ("2024-01-01", 1704067200),
        ("2024-01-01T12:00:00+02:00", 1704103200),
        ("2024-01-01T10:00:00Z", 1704103200),
        ("2024", 1704067200),
    ],
)
def test_parse_when(value: str, expected: int) -> None:
    assert _parse_when(value) == expected


@pytest.mark.parametrize(
    "value, message",
    [
        ("yesterday", "not a Unix timestamp"),
        ("20240101", "not a plausible Unix timestamp"),
        ("1000", "not a plausible Unix timestamp"),
    ],
)
def test_parse_when_invalid(value: str, message: str) -> None:
    with pytest.raises(Exception, match=message):
        _parse_when(value)


def test_cli_requires_api_key(monkeypatch, capsys) -> None:
    # Arrange
    monkeypatch.delenv("PYLAST_API_KEY", raising=False)

    # Act
    with pytest.raises(SystemExit) as excinfo:
        main(["export", "alice"])

    # Assert
    assert excinfo.value.code == 2
    err = _plain(capsys.readouterr().err)
    assert "PYLAST_API_KEY" in err
    assert "usage: python -m pylast export" in err  # the subcommand's usage


def test_cli_export(tmp_path, monkeypatch, capsys) -> None:
    # Arrange
    monkeypatch.setenv("PYLAST_API_KEY", "k")
    path = tmp_path / "alice.jsonl"
    responses = [
        _ok(_loved([_loved_track(400)])),
        _ok(_recent([_track(300), _track(200)])),
    ]

    # Act
    with patch("httpx2.Client.post", side_effect=responses) as post:
        code = main(["export", "alice", "-o", str(path), "--to", "2024-01-01"])

    # Assert: loved tracks first, then scrobbles
    assert code == 0
    methods = [c.kwargs["data"]["method"] for c in post.call_args_list]
    assert methods == ["user.getLovedTracks", "user.getRecentTracks"]
    assert post.call_args.kwargs["data"]["to"] == "1704067200"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    loved = (tmp_path / "alice-loved.jsonl").read_text(encoding="utf-8")
    assert json.loads(loved)["timestamp"] == 400
    err = capsys.readouterr().err
    assert "Wrote 1 loved tracks" in err
    assert "Wrote 2 scrobbles" in err


def test_cli_export_to_stdout(capsys) -> None:
    # Arrange
    body = _recent([_track(300)])

    # Act
    with patch("httpx2.Client.post", return_value=_ok(body)) as post:
        code = main(
            ["export", "alice", "-o", "-", "--api-key", "k", "--to", "2024-01-01"]
        )

    # Assert: scrobbles only, no loved tracks fetched
    assert code == 0
    assert post.call_count == 1
    assert json.loads(capsys.readouterr().out)["timestamp"] == 300


@pytest.mark.parametrize(
    "response, output, existing, message",
    [
        pytest.param(
            _ok(LOGIN_REQUIRED_BODY), "a.jsonl", None, "private", id="private-profile"
        ),
        pytest.param(
            _ok(_loved([_loved_track(400)])),
            "a.jsonl",
            b"not json\n",
            "Error: ",
            id="resume-error",
        ),
        pytest.param(
            _ok(_recent([_track(300)])), "no/a.jsonl", None, "Error: ", id="missing-dir"
        ),
    ],
)
def test_cli_errors(tmp_path, capsys, response, output, existing, message) -> None:
    # Arrange
    path = tmp_path / output
    if existing:
        path.write_bytes(existing)

    # Act
    with patch("httpx2.Client.post", return_value=response):
        code = main(["export", "alice", "-o", str(path), "--api-key", "k"])

    # Assert
    assert code == 1
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra_args, advice",
    [
        pytest.param([], "run the same command again to resume", id="resumable"),
        pytest.param(["--no-resume"], "the output is incomplete", id="no-resume"),
    ],
)
def test_cli_interrupted(tmp_path, capsys, extra_args, advice) -> None:
    # Act
    with patch("httpx2.Client.post", side_effect=KeyboardInterrupt):
        code = main(
            ["export", "alice", "-o", str(tmp_path / "a.jsonl"), "--api-key", "k"]
            + extra_args
        )

    # Assert
    assert code == 130
    assert f"Interrupted after fetching 0 loved tracks; {advice}." in (
        capsys.readouterr().err
    )


# Against Last.fm (recorded)

BBC6_START = int(dt.datetime(2020, 2, 15, 15, 0, tzinfo=dt.UTC).timestamp())
BBC6_END = int(dt.datetime(2020, 2, 15, 15, 40, tzinfo=dt.UTC).timestamp())


class TestPyLastExport(TestPyLastWithLastFm):
    def test_get_scrobbles(self) -> None:
        # Arrange
        user = self.network.get_user("bbc6music")

        # Act
        scrobbles = list(user.get_scrobbles(BBC6_START, BBC6_END, page_size=5))

        # Assert
        assert len(scrobbles) == 11
        assert scrobbles[0].artist == "Seun Kuti & Egypt 80"
        assert scrobbles[0].title == "Struggles Sounds"
        timestamps = [s.timestamp for s in scrobbles]
        assert timestamps == sorted(timestamps, reverse=True)
        assert all(BBC6_START <= t <= BBC6_END for t in timestamps)
        assert any(s.artist_mbid for s in scrobbles)
        assert any(s.track_mbid for s in scrobbles)
        assert all(s.url for s in scrobbles)

    def test_get_loves(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        loves = list(itertools.islice(user.get_loves(page_size=20), 25))

        # Assert
        assert len(loves) == 25
        assert all(love.artist and love.title and love.timestamp for love in loves)
        assert any(love.track_mbid for love in loves)

    def test_export_scrobbles_and_resume(self, tmp_path) -> None:
        # Arrange
        user = self.network.get_user("bbc6music")
        path = tmp_path / "bbc6music.jsonl"

        # Act
        written = export_scrobbles(user, path, time_from=BBC6_START, time_to=BBC6_END)
        again = export_scrobbles(user, path, time_from=BBC6_START, time_to=BBC6_END)

        # Assert
        assert written == 11
        assert again == 0
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 11
        assert json.loads(lines[0])["artist"] == "Seun Kuti & Egypt 80"

    def test_cli_export(self, tmp_path, capsys) -> None:
        # Arrange
        path = tmp_path / "bbc6music.jsonl"
        api_key = self.secrets["api_key"] or "k"

        # Act
        code = main(
            [
                "export",
                "bbc6music",
                "-o",
                str(path),
                "--from",
                str(BBC6_START),
                "--to",
                "2020-02-15T15:40:00Z",
                "--api-key",
                api_key,
            ]
        )

        # Assert
        assert code == 0
        assert len(path.read_text(encoding="utf-8").splitlines()) == 11
        assert (tmp_path / "bbc6music-loved.jsonl").exists()
        assert "Wrote 11 scrobbles" in capsys.readouterr().err
