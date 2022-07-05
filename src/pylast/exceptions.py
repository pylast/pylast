from __future__ import annotations

from .utils import _string_output


class PyLastError(Exception):
    """Generic exception raised by PyLast"""

    pass


class WSError(PyLastError):
    """Exception related to the Network web service"""

    def __init__(self, network, status, details) -> None:
        self.status = status
        self.details = details
        self.network = network

    @_string_output
    def __str__(self) -> str:
        return self.details

    def get_id(self):
        """Returns the exception ID, from one of the following:
        STATUS_INVALID_SERVICE = 2
        STATUS_INVALID_METHOD = 3
        STATUS_AUTH_FAILED = 4
        STATUS_INVALID_FORMAT = 5
        STATUS_INVALID_PARAMS = 6
        STATUS_INVALID_RESOURCE = 7
        STATUS_OPERATION_FAILED = 8
        STATUS_INVALID_SK = 9
        STATUS_INVALID_API_KEY = 10
        STATUS_OFFLINE = 11
        STATUS_SUBSCRIBERS_ONLY = 12
        STATUS_TOKEN_UNAUTHORIZED = 14
        STATUS_TOKEN_EXPIRED = 15
        STATUS_TEMPORARILY_UNAVAILABLE = 16
        STATUS_LOGIN_REQUIRED = 17
        STATUS_TRIAL_EXPIRED = 18
        STATUS_NOT_ENOUGH_CONTENT = 20
        STATUS_NOT_ENOUGH_MEMBERS  = 21
        STATUS_NOT_ENOUGH_FANS = 22
        STATUS_NOT_ENOUGH_NEIGHBOURS = 23
        STATUS_NO_PEAK_RADIO = 24
        STATUS_RADIO_NOT_FOUND = 25
        STATUS_API_KEY_SUSPENDED = 26
        STATUS_DEPRECATED = 27
        STATUS_RATE_LIMIT_EXCEEDED = 29
        """

        return self.status


class MalformedResponseError(PyLastError):
    """Exception conveying a malformed response from the music network."""

    def __init__(self, network, underlying_error) -> None:
        self.network = network
        self.underlying_error = underlying_error

    def __str__(self) -> str:
        return (
            f"Malformed response from {self.network.name}. "
            f"Underlying error: {self.underlying_error}"
        )


class NetworkError(PyLastError):
    """Exception conveying a problem in sending a request to Last.fm"""

    def __init__(self, network, underlying_error) -> None:
        self.network = network
        self.underlying_error = underlying_error

    def __str__(self) -> str:
        return f"NetworkError: {self.underlying_error}"
