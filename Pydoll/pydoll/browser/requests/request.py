"""
This module provides a Request class that mimics the behavior of requests.
It allows making HTTP requests using the browser's fetch API.
"""

import json as jsonlib
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, cast
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydoll.browser.requests.response import HTTPError, Response
from pydoll.commands.runtime_commands import RuntimeCommands
from pydoll.constants import Scripts
from pydoll.protocol.fetch.types import HeaderEntry
from pydoll.protocol.network.events import NetworkEvent
from pydoll.protocol.network.types import CookieParam

if TYPE_CHECKING:
    from pydoll.browser.tab import Tab
    from pydoll.protocol.network.events import (
        RequestWillBeSentEvent,
        RequestWillBeSentEventParams,
        RequestWillBeSentExtraInfoEvent,
        RequestWillBeSentExtraInfoEventParams,
        ResponseReceivedEvent,
        ResponseReceivedEventParams,
        ResponseReceivedExtraInfoEvent,
        ResponseReceivedExtraInfoEventParams,
    )
    from pydoll.protocol.runtime.methods import EvaluateResponse

    RequestReceivedEvent = Union[
        ResponseReceivedEvent,
        ResponseReceivedExtraInfoEvent,
    ]
    RequestReceivedEventParams = Union[
        ResponseReceivedEventParams,
        ResponseReceivedExtraInfoEventParams,
    ]
    RequestSentEvent = Union[
        RequestWillBeSentEvent,
        RequestWillBeSentExtraInfoEvent,
    ]
    RequestSentEventParams = Union[
        RequestWillBeSentEventParams,
        RequestWillBeSentExtraInfoEventParams,
    ]


class Request:
    """High-level interface for making HTTP requests using the browser's fetch API.

    This class provides a requests-like interface that executes HTTP requests in the
    browser's JavaScript context. All requests inherit the browser's current session
    state including cookies, authentication headers, and other automatic browser
    behaviors. This allows for seamless interaction with websites that require
    authentication or have complex cookie management.

    Key Features:
    - Executes requests in the browser's JavaScript context using fetch API
    - Automatically includes browser cookies and session state
    - Preserves browser's security context and CORS policies
    - Captures both request and response headers for analysis
    - Supports all standard HTTP methods (GET, POST, PUT, DELETE, etc.)

    Note:
    - Headers passed to methods are additional headers, not replacements
    - Browser's automatic headers (User-Agent, Accept, etc.) are preserved
    - Cookies are managed automatically by the browser
    """

    def __init__(self, tab: 'Tab'):
        """Initialize a new Request instance bound to a browser tab.

        Args:
            tab: The browser tab instance where requests will be executed.
                This tab provides the JavaScript execution context and maintains
                the browser's session state (cookies, authentication, etc.).
        """
        self.tab = tab
        self._network_events_enabled = False
        self._requests_sent: list['RequestSentEvent'] = []
        self._requests_received: list['RequestReceivedEvent'] = []

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, str]] = None,
        data: Optional[Union[dict, list, tuple, str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[list[HeaderEntry]] = None,
        **kwargs,
    ) -> Response:
        """Execute an HTTP request in the browser's JavaScript context.

        This method uses the browser's fetch API to make requests, inheriting all
        browser session state including cookies, authentication, and security context.
        The request is executed as if made by the browser itself.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.). Case insensitive.
            url: Target URL for the request. Can be relative or absolute.
            params: Query parameters to append to the URL. These are URL-encoded
                and merged with any existing query string in the URL.
            data: Request body data. Behavior depends on type:
                - dict/list/tuple: URL-encoded as form data (application/x-www-form-urlencoded)
                - str/bytes: Sent as-is with no Content-Type modification
                Mutually exclusive with 'json' parameter.
            json: Data to be JSON-serialized as request body. Automatically sets
                Content-Type to application/json. Mutually exclusive with 'data'.
            headers: Additional headers to include. These are ADDED to browser's
                automatic headers, not replacements.
                Format: [{'name': 'X-Custom', 'value': 'value'}]
            **kwargs: Additional fetch API options (e.g., credentials, mode, cache).

        Returns:
            Response object containing status, headers, content, and cookies from
            both the request and response phases.

        Raises:
            HTTPError: If the request execution fails or network error occurs.

        Note:
            - Browser cookies are automatically included
            - CORS policies are enforced by the browser
            - Authentication headers are preserved from browser session
        """
        final_url = self._build_url_with_params(url, params)
        options = self._build_request_options(method, headers, json, data, **kwargs)
        try:
            result = await self._execute_fetch_request(final_url, options)
            received_headers = self._extract_received_headers()
            sent_headers = self._extract_sent_headers()
            cookies = self._extract_set_cookies()
            return self._build_response(result, received_headers, sent_headers, cookies)

        except Exception as exc:
            raise HTTPError(f'Request failed: {str(exc)}') from exc

        finally:
            await self._clear_callbacks()

    async def get(
        self,
        url: str,
        params: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> Response:
        """Execute a GET request for retrieving data.

        Args:
            url: Target URL to retrieve data from.
            params: Query parameters to append to URL.
            **kwargs: Additional fetch options.

        Returns:
            Response object with retrieved data.
        """
        return await self.request('GET', url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        data: Optional[Union[dict, list, tuple, str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> Response:
        """Execute a POST request for creating or submitting data.

        Args:
            url: Target URL for data submission.
            data: Form data to submit (URL-encoded).
            json: JSON data to submit.
            **kwargs: Additional fetch options.

        Returns:
            Response object with server's response to the submission.
        """
        return await self.request('POST', url, data=data, json=json, **kwargs)

    async def put(
        self,
        url: str,
        data: Optional[Union[dict, list, tuple, str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> Response:
        """Execute a PUT request for updating/replacing resources.

        Args:
            url: Target URL of resource to update.
            data: Form data for the update.
            json: JSON data for the update.
            **kwargs: Additional fetch options.

        Returns:
            Response object confirming the update operation.
        """
        return await self.request('PUT', url, data=data, json=json, **kwargs)

    async def patch(
        self,
        url: str,
        data: Optional[Union[dict, list, tuple, str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> Response:
        """Execute a PATCH request for partial resource updates.

        Args:
            url: Target URL of resource to partially update.
            data: Form data with changes to apply.
            json: JSON data with changes to apply.
            **kwargs: Additional fetch options.

        Returns:
            Response object confirming the partial update.
        """
        return await self.request('PATCH', url, data=data, json=json, **kwargs)

    async def delete(self, url: str, **kwargs) -> Response:
        """Execute a DELETE request for removing resources.

        Args:
            url: Target URL of resource to delete.
            **kwargs: Additional fetch options.

        Returns:
            Response object confirming the deletion.
        """
        return await self.request('DELETE', url, **kwargs)

    async def head(self, url: str, **kwargs) -> Response:
        """Execute a HEAD request to retrieve only response headers.

        Useful for checking resource existence, size, or modification date
        without downloading the full content.

        Args:
            url: Target URL to check headers for.
            **kwargs: Additional fetch options.

        Returns:
            Response object with headers but no body content.
        """
        return await self.request('HEAD', url, **kwargs)

    async def options(self, url: str, **kwargs) -> Response:
        """Execute an OPTIONS request to check allowed methods and capabilities.

        Used for CORS preflight checks and discovering server capabilities.

        Args:
            url: Target URL to check options for.
            **kwargs: Additional fetch options.

        Returns:
            Response object with allowed methods and CORS headers.
        """
        return await self.request('OPTIONS', url, **kwargs)

    @staticmethod
    def _build_url_with_params(url: str, params: Optional[dict[str, str]]) -> str:
        """Build final URL with query parameters."""
        if not params:
            return url

        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        for key, value in params.items():
            query[key] = [value]

        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def _build_request_options(
        self,
        method: str,
        headers: Optional[list[HeaderEntry]],
        json: Optional[dict[str, Any]],
        data: Optional[Union[dict, list, tuple, str, bytes]],
        **kwargs,
    ) -> dict[str, Any]:
        """Build request options dictionary."""
        headers_dict = self._convert_header_entries_to_dict(headers) if headers else {}
        options = {
            'method': method.upper(),
            'headers': headers_dict,
            **kwargs,
        }

        self._add_request_body(options, json, data)
        return options

    def _add_request_body(
        self,
        options: dict[str, Any],
        json: Optional[dict[str, Any]],
        data: Optional[Union[dict, list, tuple, str, bytes]],
    ) -> None:
        """Add request body and appropriate Content-Type header."""

        if json is not None:
            self._handle_json_options(options, json)
        elif data is not None:
            self._handle_data_options(options, data)

    @staticmethod
    def _handle_json_options(options: dict[str, Any], json: Optional[dict[str, Any]]) -> None:
        """Handle JSON options."""
        options['body'] = jsonlib.dumps(json)
        options['headers'].setdefault('Content-Type', 'application/json')

    @staticmethod
    def _handle_data_options(
        options: dict[str, Any], data: Optional[Union[dict, list, tuple, str, bytes]]
    ) -> None:
        """Handle data options."""
        if isinstance(data, (dict, list, tuple)):
            options['body'] = urlencode(data, doseq=True)
            options['headers'].setdefault('Content-Type', 'application/x-www-form-urlencoded')
        else:
            options['body'] = data

    async def _execute_fetch_request(self, url: str, options: dict[str, Any]) -> 'EvaluateResponse':
        """Execute the fetch request using browser's runtime."""
        script = Scripts.MAKE_REQUEST.format(url=jsonlib.dumps(url), options=jsonlib.dumps(options))
        await self._register_callbacks()

        return await self.tab._execute_command(
            RuntimeCommands.evaluate(
                expression=script,
                return_by_value=True,
                await_promise=True,
            )
        )

    @staticmethod
    def _build_response(
        result: 'EvaluateResponse',
        response_headers: list[HeaderEntry],
        request_headers: list[HeaderEntry],
        cookies: list[CookieParam],
    ) -> Response:
        """Build Response object from fetch result."""
        result_value = result['result']['result']['value']
        return Response(
            status_code=result_value['status'],
            content=bytes(result_value.get('content', b'')),
            text=result_value['text'],
            json=result_value['json'],
            response_headers=response_headers,
            request_headers=request_headers,
            cookies=cookies,
            url=result_value['url'],
        )

    async def _register_callbacks(self) -> None:
        """Register network event listeners to capture request/response metadata.

        Sets up CDP event listeners to capture all network activity during the
        request execution. This includes both outgoing request data and incoming
        response data, which are used for header and cookie extraction.

        Note:
            Network events are only enabled if not already active on the tab.
        """
        if not self.tab.network_events_enabled:
            await self.tab.enable_network_events()
            self._network_events_enabled = True

        def append_received_request(event: dict) -> None:
            self._requests_received.append(cast('RequestReceivedEvent', event))

        def append_sent_request(event: dict) -> None:
            self._requests_sent.append(cast('RequestSentEvent', event))

        await self.tab.on(
            NetworkEvent.REQUEST_WILL_BE_SENT,
            callback=append_sent_request,
        )
        await self.tab.on(
            NetworkEvent.REQUEST_WILL_BE_SENT_EXTRA_INFO,
            callback=append_sent_request,
        )
        await self.tab.on(
            NetworkEvent.RESPONSE_RECEIVED,
            callback=append_received_request,
        )
        await self.tab.on(
            NetworkEvent.RESPONSE_RECEIVED_EXTRA_INFO,
            callback=append_received_request,
        )

    async def _clear_callbacks(self) -> None:
        """Clean up network event listeners and disable network monitoring.

        Removes all registered event callbacks and disables network events
        if they were enabled by this request instance.
        """
        if self._network_events_enabled:
            await self.tab.disable_network_events()
            self._network_events_enabled = False
        await self.tab.clear_callbacks()

    def _extract_received_headers(self) -> list[HeaderEntry]:
        """Extract headers from response network events.

        Returns:
            List of headers received from the server during response.
        """
        event_extractors: dict[str, Callable[[Any], list[HeaderEntry]]] = {
            'response': self._extract_response_received_headers,
            'blockedCookies': self._extract_response_received_extra_info_headers,
        }

        return self._extract_headers_from_events(self._requests_received, event_extractors)

    def _extract_sent_headers(self) -> list[HeaderEntry]:
        """Extract headers from request network events.

        Returns:
            List of headers that were actually sent in the request.
        """
        event_extractors: dict[str, Callable[[Any], list[HeaderEntry]]] = {
            'request': self._extract_request_sent_headers,
            'associatedCookies': self._extract_request_sent_extra_info_headers,
        }

        return self._extract_headers_from_events(self._requests_sent, event_extractors)

    @staticmethod
    def _extract_headers_from_events(
        events: Union[list['RequestSentEvent'], list['RequestReceivedEvent']],
        event_extractors: dict[str, Callable[[Any], list[HeaderEntry]]],
    ) -> list[HeaderEntry]:
        """Extract headers from network events using appropriate extractors.

        Args:
            events: List of network events to process.
            event_extractors: Mapping of event keys to header extraction functions.

        Returns:
            Deduplicated list of headers from all matching events.

        Note:
            Headers are deduplicated based on name-value pairs to avoid
            duplicate entries from multiple event types.
        """
        headers: list[HeaderEntry] = []
        seen = set()

        for event in events:
            params = event['params']
            for key, extractor in event_extractors.items():
                if key in params:
                    extracted_headers = extractor(params)
                    for header in extracted_headers:
                        identity = (header['name'], header['value'])
                        if identity not in seen:
                            headers.append(header)
                            seen.add(identity)
                    break

        return headers

    def _extract_request_sent_headers(
        self, params: 'RequestWillBeSentEventParams'
    ) -> list[HeaderEntry]:
        """Extract headers from main request event.

        Args:
            params: Event parameters containing request details.

        Returns:
            List of headers that were sent with the request.
        """
        request = params['request']
        return self._convert_dict_to_header_entries(request.get('headers', {}))

    def _extract_request_sent_extra_info_headers(
        self, params: 'RequestWillBeSentExtraInfoEventParams'
    ) -> list[HeaderEntry]:
        """Extract headers from extra request info event.

        This event contains additional header information that may not be
        present in the main request event, such as security-related headers.

        Args:
            params: Extra info event parameters containing additional headers.

        Returns:
            List of additional headers sent with the request.
        """
        return self._convert_dict_to_header_entries(params.get('headers', {}))

    def _extract_response_received_headers(
        self, params: 'ResponseReceivedEventParams'
    ) -> list[HeaderEntry]:
        """Extract headers from main response event.

        Args:
            params: Event parameters containing response details.

        Returns:
            List of headers received from the server.
        """
        response = params['response']
        return self._convert_dict_to_header_entries(response.get('headers', {}))

    def _extract_response_received_extra_info_headers(
        self, params: 'ResponseReceivedExtraInfoEventParams'
    ) -> list[HeaderEntry]:
        """Extract headers from extra response info event.

        This event contains additional response header information, including
        Set-Cookie headers and security-related headers that may be filtered
        from the main response event.

        Args:
            params: Extra info event parameters containing additional headers.

        Returns:
            List of additional headers received from the server.
        """
        return self._convert_dict_to_header_entries(params.get('headers', {}))

    @staticmethod
    def _convert_dict_to_header_entries(headers_dict: dict) -> list[HeaderEntry]:
        """Convert header dictionary to standardized HeaderEntry format.

        Args:
            headers_dict: Dictionary mapping header names to values.

        Returns:
            List of HeaderEntry objects with 'name' and 'value' keys.
        """
        return [HeaderEntry(name=name, value=value) for name, value in headers_dict.items()]

    def _extract_set_cookies(self) -> list[CookieParam]:
        """Extract and parse all Set-Cookie headers from response events.

        Processes response events to find Set-Cookie headers and converts them
        into structured cookie objects. Handles multiple Set-Cookie headers
        and multi-line cookie declarations.

        Returns:
            List of unique cookies extracted from Set-Cookie headers.
        """
        cookies: list[CookieParam] = []

        response_extra_info_events = self._filter_response_extra_info_events()

        for event in response_extra_info_events:
            params = cast('ResponseReceivedExtraInfoEventParams', event['params'])
            headers = self._convert_dict_to_header_entries(params['headers'])
            set_cookie_headers = [
                header['value'] for header in headers if header['name'] == 'Set-Cookie'
            ]

            if set_cookie_headers:
                for set_cookie_header in set_cookie_headers:
                    self._add_unique_cookies(
                        cookies, self._parse_set_cookie_header(set_cookie_header)
                    )

        return cookies

    def _filter_response_extra_info_events(self) -> list['RequestReceivedEvent']:
        """Filter network events to find those containing Set-Cookie information.

        Returns:
            List of events that contain extra response information including cookies.
        """
        return [
            event
            for event in self._requests_received
            if event['method'] == NetworkEvent.RESPONSE_RECEIVED_EXTRA_INFO
        ]

    def _parse_set_cookie_header(self, set_cookie_header: str) -> list[CookieParam]:
        """Parse a Set-Cookie header value into individual cookie objects.

        Handles both single and multi-line Set-Cookie headers, extracting
        cookie name-value pairs while ignoring attributes like Path, Domain, etc.

        Args:
            set_cookie_header: Raw Set-Cookie header value from HTTP response.

        Returns:
            List of parsed cookie objects with name and value.
        """
        cookies = []
        lines = set_cookie_header.split('\n')

        for line in lines:
            cookie = self._parse_cookie_line(line)
            if cookie:
                cookies.append(cookie)

        return cookies

    @staticmethod
    def _parse_cookie_line(line: str) -> Optional[CookieParam]:
        """Parse a single cookie line to extract name and value.

        Extracts only the cookie name and value, ignoring all cookie attributes
        like Path, Domain, Secure, HttpOnly, etc. Rejects cookies with empty names.

        Args:
            line: Single line from Set-Cookie header.

        Returns:
            CookieParam object with name and value, or None if parsing fails or name is empty.
        """
        if '=' not in line:
            return None

        name = line.split('=', 1)[0].strip()
        value = line.split('=', 1)[1].split(';', 1)[0].strip()

        # Reject cookies with empty names
        if not name:
            return None

        return CookieParam(name=name, value=value)

    @staticmethod
    def _add_unique_cookies(cookies: list[CookieParam], new_cookies: list[CookieParam]) -> None:
        """Add cookies to list while avoiding duplicates.

        Args:
            cookies: Existing list of cookies to add to.
            new_cookies: New cookies to add if not already present.
        """
        for cookie in new_cookies:
            if cookie not in cookies:
                cookies.append(cookie)

    @staticmethod
    def _convert_header_entries_to_dict(headers: list[HeaderEntry]) -> dict[str, str]:
        """Convert HeaderEntry objects to a plain dictionary format.

        Used for preparing headers for the JavaScript fetch API which expects
        a simple object mapping header names to values.

        Args:
            headers: List of HeaderEntry objects with 'name' and 'value' keys.

        Returns:
            Dictionary mapping header names to values.
        """
        return {header['name']: header['value'] for header in headers}
