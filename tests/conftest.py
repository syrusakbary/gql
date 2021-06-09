import asyncio
import json
import logging
import os
import pathlib
import ssl
import sys
import tempfile
import types
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType
from typing import Union

import pytest
from graphql import build_client_schema

import tests.testmodule as testmodule
from gql import Client
from gql.compiler.query_parser import QueryParser
from gql.compiler.renderer_dataclasses import DataclassesRenderer

all_transport_dependencies = ["aiohttp", "requests", "websockets"]


def pytest_addoption(parser):
    parser.addoption(
        "--run-online",
        action="store_true",
        default=False,
        help="run tests necessitating online resources",
    )
    for transport in all_transport_dependencies:
        parser.addoption(
            f"--{transport}-only",
            action="store_true",
            default=False,
            help=f"run tests necessitating only the {transport} dependency",
        )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "online: mark test as necessitating external online resources"
    )
    for transport in all_transport_dependencies:
        config.addinivalue_line(
            "markers",
            f"{transport}: mark test as necessitating the {transport} dependency",
        )


def pytest_collection_modifyitems(config, items):

    # --run-online given in cli: do not skip online tests
    if not config.getoption("--run-online"):
        skip_online = pytest.mark.skip(reason="need --run-online option to run")
        for item in items:
            if "online" in item.keywords:
                item.add_marker(skip_online)

    # --aiohttp-only
    # --requests-only
    # --websockets-only
    for transport in all_transport_dependencies:

        other_transport_dependencies = [
            t for t in all_transport_dependencies if t != transport
        ]

        if config.getoption(f"--{transport}-only"):
            skip_transport = pytest.mark.skip(
                reason=f"need another dependency than {transport}"
            )
            for item in items:
                # Check if we have a dependency transport
                # other than the requested transport
                if any(t in item.keywords for t in other_transport_dependencies):
                    item.add_marker(skip_transport)


@pytest.fixture
async def aiohttp_server():
    """Factory to create a TestServer instance, given an app.

    aiohttp_server(app, **kwargs)
    """
    from aiohttp.test_utils import TestServer as AIOHTTPTestServer

    servers = []

    async def go(app, *, port=None, **kwargs):  # type: ignore
        server = AIOHTTPTestServer(app, port=port)
        await server.start_server(**kwargs)
        servers.append(server)
        return server

    yield go

    while servers:
        await servers.pop().close()


# Adding debug logs to websocket tests
for name in ["websockets.legacy.server", "gql.transport.websockets", "gql.dsl"]:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if len(logger.handlers) < 1:
        logger.addHandler(logging.StreamHandler())

# Unit for timeouts. May be increased on slow machines by setting the
# GQL_TESTS_TIMEOUT_FACTOR environment variable.
# Copied from websockets source
MS = 0.001 * int(os.environ.get("GQL_TESTS_TIMEOUT_FACTOR", 1))


class WebSocketServer:
    """Websocket server on localhost on a free port.

    This server allows us to test our client by simulating different correct and
    incorrect server responses.
    """

    def __init__(self, with_ssl: bool = False):
        self.with_ssl = with_ssl

    async def start(self, handler):

        import websockets.server

        print("Starting server")

        extra_serve_args = {}

        if self.with_ssl:
            # This is a copy of certificate from websockets tests folder
            #
            # Generate TLS certificate with:
            # $ openssl req -x509 -config test_localhost.cnf \
            #       -days 15340 -newkey rsa:2048 \
            #       -out test_localhost.crt -keyout test_localhost.key
            # $ cat test_localhost.key test_localhost.crt > test_localhost.pem
            # $ rm test_localhost.key test_localhost.crt
            self.testcert = bytes(
                pathlib.Path(__file__).with_name("test_localhost.pem")
            )
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self.testcert)

            extra_serve_args["ssl"] = ssl_context

        # Start a server with a random open port
        self.start_server = websockets.server.serve(
            handler, "127.0.0.1", 0, **extra_serve_args
        )

        # Wait that the server is started
        self.server = await self.start_server

        # Get hostname and port
        hostname, port = self.server.sockets[0].getsockname()[:2]
        assert hostname == "127.0.0.1"

        self.hostname = hostname
        self.port = port

        print(f"Server started on port {port}")

    async def stop(self):
        print("Stopping server")

        self.server.close()
        try:
            await asyncio.wait_for(self.server.wait_closed(), timeout=1)
        except asyncio.TimeoutError:  # pragma: no cover
            assert False, "Server failed to stop"

        print("Server stopped\n\n\n")


class WebSocketServerHelper:
    @staticmethod
    async def send_complete(ws, query_id):
        await ws.send(f'{{"type":"complete","id":"{query_id}","payload":null}}')

    @staticmethod
    async def send_keepalive(ws):
        await ws.send('{"type":"ka"}')

    @staticmethod
    async def send_connection_ack(ws):

        # Line return for easy debugging
        print("")

        # Wait for init
        result = await ws.recv()
        json_result = json.loads(result)
        assert json_result["type"] == "connection_init"

        # Send ack
        await ws.send('{"type":"connection_ack"}')

    @staticmethod
    async def wait_connection_terminate(ws):
        result = await ws.recv()
        json_result = json.loads(result)
        assert json_result["type"] == "connection_terminate"


class PhoenixChannelServerHelper:
    @staticmethod
    async def send_close(ws):
        await ws.send('{"event":"phx_close"}')

    @staticmethod
    async def send_connection_ack(ws):

        # Line return for easy debugging
        print("")

        # Wait for init
        result = await ws.recv()
        json_result = json.loads(result)
        assert json_result["event"] == "phx_join"

        # Send ack
        await ws.send('{"event":"phx_reply", "payload": {"status": "ok"}, "ref": 1}')


class TemporaryFile:
    """Class used to generate temporary files for the tests"""

    def __init__(self, content: Union[str, bytearray]):

        mode = "w" if isinstance(content, str) else "wb"

        # We need to set the newline to '' so that the line returns
        # are not replaced by '\r\n' on windows
        newline = "" if isinstance(content, str) else None

        self.file = tempfile.NamedTemporaryFile(
            mode=mode, newline=newline, delete=False
        )

        with self.file as f:
            f.write(content)

    @property
    def filename(self):
        return self.file.name

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.unlink(self.filename)


def get_server_handler(request):
    """Get the server handler.

    Either get it from test or use the default server handler
    if the test provides only an array of answers.
    """

    from websockets.exceptions import ConnectionClosed

    if isinstance(request.param, types.FunctionType):
        server_handler = request.param

    else:
        answers = request.param

        async def default_server_handler(ws, path):

            try:
                await WebSocketServerHelper.send_connection_ack(ws)
                query_id = 1

                for answer in answers:
                    result = await ws.recv()
                    print(f"Server received: {result}", file=sys.stderr)

                    if isinstance(answer, str) and "{query_id}" in answer:
                        answer_format_params = {"query_id": query_id}
                        formatted_answer = answer.format(**answer_format_params)
                    else:
                        formatted_answer = answer

                    await ws.send(formatted_answer)
                    await WebSocketServerHelper.send_complete(ws, query_id)
                    query_id += 1

                await WebSocketServerHelper.wait_connection_terminate(ws)
                await ws.wait_closed()
            except ConnectionClosed:
                pass

        server_handler = default_server_handler

    return server_handler


@pytest.fixture
async def ws_ssl_server(request):
    """Websockets server fixture using SSL.

    It can take as argument either a handler function for the websocket server for
    complete control OR an array of answers to be sent by the default server handler.
    """

    server_handler = get_server_handler(request)

    try:
        test_server = WebSocketServer(with_ssl=True)

        # Starting the server with the fixture param as the handler function
        await test_server.start(server_handler)

        yield test_server
    except Exception as e:
        print("Exception received in ws server fixture:", e)
    finally:
        await test_server.stop()


@pytest.fixture
async def server(request):
    """Fixture used to start a dummy server to test the client behaviour.

    It can take as argument either a handler function for the websocket server for
    complete control OR an array of answers to be sent by the default server handler.
    """

    server_handler = get_server_handler(request)

    try:
        test_server = WebSocketServer()

        # Starting the server with the fixture param as the handler function
        await test_server.start(server_handler)

        yield test_server
    except Exception as e:
        print("Exception received in server fixture:", e)
    finally:
        await test_server.stop()


@pytest.fixture
async def client_and_server(server):
    """Helper fixture to start a server and a client connected to its port."""

    from gql.transport.websockets import WebsocketsTransport

    # Generate transport to connect to the server fixture
    path = "/graphql"
    url = f"ws://{server.hostname}:{server.port}{path}"
    sample_transport = WebsocketsTransport(url=url)

    async with Client(transport=sample_transport) as session:

        # Yield both client session and server
        yield session, server


@pytest.fixture
async def run_sync_test():
    async def run_sync_test_inner(event_loop, server, test_function):
        """This function will run the test in a different Thread.

        This allows us to run sync code while aiohttp server can still run.
        """
        executor = ThreadPoolExecutor(max_workers=2)
        test_task = event_loop.run_in_executor(executor, test_function)

        await test_task

        if hasattr(server, "close"):
            await server.close()

    return run_sync_test_inner


def load_introspection_from_file(filename):
    with open(filename, "r", encoding="utf8") as fin:
        return json.load(fin)


def load_schema_from_file(file_path):
    introspection = load_introspection_from_file(file_path)
    return build_client_schema(introspection)


@pytest.fixture
async def swapi_schema():
    filename = os.path.join(os.path.dirname(__file__), "fixtures/swapi-schema.graphql")
    return load_schema_from_file(filename)


@pytest.fixture
async def swapi_parser(swapi_schema):
    return QueryParser(swapi_schema)


@pytest.fixture
async def config_path(swapi_schema):
    return os.path.join(os.path.dirname(__file__), "testmodule/config.py")


@pytest.fixture
async def swapi_dataclass_renderer(swapi_schema, config_path):
    return DataclassesRenderer(swapi_schema, config_path)


@pytest.fixture
async def github_schema():
    filename = os.path.join(os.path.dirname(__file__), "fixtures/github-schema.graphql")
    return load_schema_from_file(filename)


@pytest.fixture
async def github_parser(github_schema):
    return QueryParser(github_schema)


@pytest.fixture
async def github_dataclass_renderer(github_schema):
    return DataclassesRenderer(github_schema)


def load_module(code, module_name=None):
    compiled = compile(code, "", "exec")
    module = testmodule
    if module_name is not None:
        module_name = ".".join([testmodule.__name__, module_name])
        module = ModuleType(module_name)
        sys.modules[module_name] = module
    exec(compiled, module.__dict__)
    return testmodule
