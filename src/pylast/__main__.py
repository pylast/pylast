"""
Command-line interface for pylast.

    python -m pylast export USERNAME

exports a user's scrobbles and loved tracks to JSON Lines files.
See python -m pylast export --help.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import os
import sys
import time

import pylast
from pylast.export import export_loved, export_scrobbles

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import IO

_API_KEY_ENV_VAR = "PYLAST_API_KEY"


def _parse_when(value: str) -> int:
    """
    Parses a Unix timestamp, a bare year, or an ISO 8601 date/datetime
    (naive = UTC).
    """
    if value.isdigit():
        if len(value) == 4 and 1970 <= int(value) <= 2100:
            value = f"{value}-01-01"  # a bare year
        elif int(value) < 1_000_000_000:  # 2001, before Last.fm existed
            msg = (
                f"{value!r} is not a plausible Unix timestamp; "
                "use a date like 2024-01-01"
            )
            raise argparse.ArgumentTypeError(msg)
        else:
            return int(value)
    try:
        when = dt.datetime.fromisoformat(value)
    except ValueError:
        msg = f"not a Unix timestamp or ISO 8601 date: {value!r}"
        raise argparse.ArgumentTypeError(msg) from None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.UTC)
    return int(when.timestamp())


class _Progress:
    """Prints a one-line progress report to stderr after each page."""

    def __init__(self, what: str, stream: IO[str] | None = None) -> None:
        self.what = what
        self.stream = stream if stream is not None else sys.stderr
        self.interactive = self.stream.isatty()
        self.start = time.monotonic()
        self.count = 0

    def __call__(self, page: int, total_pages: int, count: int, total: int) -> None:
        self.count = count
        if not self.interactive and page % 50 != 0 and page != total_pages:
            return
        elapsed = dt.timedelta(seconds=int(time.monotonic() - self.start))
        line = (
            f"page {page:,}/{total_pages:,}  "
            f"{count:,}/{total:,} {self.what}  elapsed {elapsed}"
        )
        if self.interactive:
            self.stream.write("\r" + line.ljust(79))
        else:
            self.stream.write(line + "\n")
        self.stream.flush()

    def finish(self) -> None:
        if self.interactive:
            self.stream.write("\n")
            self.stream.flush()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pylast",
        description="pylast command-line tools.",
    )
    parser.add_argument(
        "--version", action="version", version=f"pylast {pylast.__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser(
        "export",
        help="export a user's scrobbles and loved tracks to files",
        description=(
            "Export a user's scrobbles to a JSON Lines file, newest first, "
            "with MusicBrainz IDs, and their loved tracks to a second file. "
            "An interrupted export is resumed when run again with the same "
            "output file."
        ),
        epilog=(
            "Dates are Unix timestamps or ISO 8601. For example, `2024-01-01` "
            "or `2024-01-01T12:00:00+02:00`; dates without a timezone are UTC, "
            "so `--to 2025-01-01` (or just `--to 2025`) means midnight UTC at "
            "the start of that day. "
            "The API key is read from `--api-key` or the `PYLAST_API_KEY` "
            "environment variable; get one at "
            "https://www.last.fm/api/account/create"
        ),
    )
    export.add_argument("username", help="Last.fm username")
    export.add_argument(
        "-o",
        "--output",
        help=(
            "scrobbles output file (default: `USERNAME.jsonl`); loved tracks go to "
            "the same name with `-loved` before the suffix. Use `-` to write "
            "scrobbles to standard output and skip loved tracks"
        ),
    )
    export.add_argument(
        "--from",
        dest="time_from",
        type=_parse_when,
        metavar="WHEN",
        help="only scrobbles after this time",
    )
    export.add_argument(
        "--to",
        dest="time_to",
        type=_parse_when,
        metavar="WHEN",
        help="only scrobbles before this time",
    )
    export.add_argument(
        "--no-resume",
        action="store_true",
        help="overwrite an existing scrobbles file instead of resuming it",
    )
    export.add_argument("--api-key", help="Last.fm API key")
    export.set_defaults(func=_export, parser=export)
    return parser


def _loved_path(output: str) -> str:
    root, ext = os.path.splitext(output)
    return f"{root}-loved{ext}"


def _export(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    api_key = args.api_key or os.environ.get(_API_KEY_ENV_VAR)
    if not api_key:
        parser.error(
            f"no API key: pass --api-key or set {_API_KEY_ENV_VAR} "
            "(create one at https://www.last.fm/api/account/create)"
        )

    output = args.output or f"{args.username}.jsonl"
    network = pylast.LastFMNetwork(api_key=api_key)
    network.enable_rate_limit()
    user = network.get_user(args.username)

    progress = _Progress("loved tracks")
    stdout = None
    try:
        if output == "-":
            stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", newline="\n", write_through=True
            )
            target: str | IO[str] = stdout
            destination = "standard output"
        else:
            # Loved tracks first: they take seconds, so an interruption during
            # the long scrobbles export still leaves both files useful.
            loved_path = _loved_path(output)
            written = export_loved(user, loved_path, progress=progress)
            progress.finish()
            print(f"Wrote {written:,} loved tracks to {loved_path}", file=sys.stderr)
            target = destination = output

        progress = _Progress("scrobbles")
        written = export_scrobbles(
            user,
            target,
            time_from=args.time_from,
            time_to=args.time_to,
            resume=not args.no_resume,
            progress=progress,
        )
        progress.finish()
        print(f"Wrote {written:,} scrobbles to {destination}", file=sys.stderr)
    except KeyboardInterrupt:
        progress.finish()
        if args.no_resume or output == "-":
            advice = "the output is incomplete"
        else:
            advice = "run the same command again to resume"
        print(
            f"Interrupted after fetching {progress.count:,} {progress.what}; {advice}.",
            file=sys.stderr,
        )
        return 130
    except pylast.WSError as e:
        progress.finish()
        if e.get_id() == str(pylast.STATUS_LOGIN_REQUIRED):
            print(
                f"Error: {args.username}'s listening history is private; "
                "the Last.fm API only exports it for authenticated sessions.",
                file=sys.stderr,
            )
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except (pylast.PyLastError, OSError) as e:
        progress.finish()
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if stdout is not None:
            stdout.flush()
            stdout.detach()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args, args.parser))


if __name__ == "__main__":
    sys.exit(main())
