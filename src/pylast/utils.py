from __future__ import annotations

import hashlib
import html
import re
import time
import warnings
import xml
from urllib.parse import quote_plus
from xml.dom import Node, minidom

import pylast


def cleanup_nodes(doc: minidom.Document) -> minidom.Document:
    """
    cleanup_nodes is deprecated and will be removed in pylast 6.0
    """
    warnings.warn(
        "cleanup_nodes is deprecated and will be removed in pylast 6.0",
        DeprecationWarning,
        stacklevel=2,
    )
    return _cleanup_nodes(doc)


def md5(text: str) -> str:
    """Returns the md5 hash of a string."""

    h = hashlib.md5()
    h.update(_unicode(text).encode("utf-8"))

    return h.hexdigest()


def _collect_nodes(
    limit, sender, method_name, cacheable, params=None, stream: bool = False
):
    """
    Returns a sequence of dom.Node objects about as close to limit as possible
    """
    if not params:
        params = sender._get_params()

    def _stream_collect_nodes():
        node_count = 0
        page = 1
        end_of_pages = False

        while not end_of_pages and (not limit or (limit and node_count < limit)):
            params["page"] = str(page)

            tries = 1
            while True:
                try:
                    doc = sender._request(method_name, cacheable, params)
                    break  # success
                except Exception as e:
                    if tries >= 3:
                        raise pylast.PyLastError() from e
                    # Wait and try again
                    time.sleep(1)
                    tries += 1

            doc = _cleanup_nodes(doc)

            # break if there are no child nodes
            if not doc.documentElement.childNodes:
                break
            main = doc.documentElement.childNodes[0]

            if main.hasAttribute("totalPages") or main.hasAttribute("totalpages"):
                total_pages = _number(
                    main.getAttribute("totalPages") or main.getAttribute("totalpages")
                )
            else:
                raise pylast.PyLastError("No total pages attribute")

            for node in main.childNodes:
                if not node.nodeType == xml.dom.Node.TEXT_NODE and (
                    not limit or (node_count < limit)
                ):
                    node_count += 1
                    yield node

            end_of_pages = page >= total_pages

            page += 1

    return _stream_collect_nodes() if stream else list(_stream_collect_nodes())


def _cleanup_nodes(doc: minidom.Document) -> minidom.Document:
    """
    Remove text nodes containing only whitespace
    """
    for node in doc.documentElement.childNodes:
        if node.nodeType == Node.TEXT_NODE and node.nodeValue.isspace():
            doc.documentElement.removeChild(node)
    return doc


def _number(string: str | None) -> float:
    """
    Extracts an int from a string.
    Returns a 0 if None or an empty string was passed.
    """

    if not string:
        return 0
    else:
        try:
            return int(string)
        except ValueError:
            return float(string)


def _parse_response(response: str) -> xml.dom.minidom.Document:
    response = str(response).replace("opensearch:", "")
    try:
        doc = minidom.parseString(response)
    except xml.parsers.expat.ExpatError:
        # Try again. For performance, we only remove when needed in rare cases.
        doc = minidom.parseString(_remove_invalid_xml_chars(response))
    return doc


def _remove_invalid_xml_chars(string: str) -> str:
    return re.sub(
        r"[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFF]+", "", string
    )


def _string_output(func):
    def r(*args):
        return str(func(*args))

    return r


def _unescape_htmlentity(string: str) -> str:
    mapping = html.entities.name2codepoint
    for key in mapping:
        string = string.replace(f"&{key};", chr(mapping[key]))

    return string


def _unicode(text: bytes | str) -> str:
    if isinstance(text, bytes):
        return str(text, "utf-8")
    else:
        return str(text)


def _url_safe(text: str) -> str:
    """Does all kinds of tricks on a text to make it safe to use in a URL."""

    return quote_plus(quote_plus(str(text))).lower()
