from __future__ import annotations

import os

import pytest

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any

PYLAST_USERNAME = os.environ.get("PYLAST_USERNAME", "")


def scrub_response(response: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive data from response bodies."""
    if PYLAST_USERNAME:
        body = response["body"]["string"]
        if isinstance(body, bytes):
            body = body.replace(PYLAST_USERNAME.encode(), b"REDACTED_USER")
        else:
            body = body.replace(PYLAST_USERNAME, "REDACTED_USER")
        response["body"]["string"] = body
    return response


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    return {
        "filter_query_parameters": ["api_key", "api_sig", "sk", "username"],
        "filter_post_data_parameters": ["api_key", "api_sig", "password", "sk", "user"],
        "before_record_response": scrub_response,
    }
