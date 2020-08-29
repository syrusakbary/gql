from concurrent.futures import ThreadPoolExecutor

import pytest
from aiohttp import web

from gql import Client, gql
from gql.transport.exceptions import (
    TransportAlreadyConnected,
    TransportClosed,
    TransportProtocolError,
    TransportQueryError,
    TransportServerError,
)
from gql.transport.requests import RequestsHTTPTransport

from .test_type_adapter import Capitalize

query1_str = """
    query getContinents {
      continents {
        code
        name
      }
    }
"""

query1_server_answer = (
    '{"data":{"continents":['
    '{"code":"AF","name":"Africa"},{"code":"AN","name":"Antarctica"},'
    '{"code":"AS","name":"Asia"},{"code":"EU","name":"Europe"},'
    '{"code":"NA","name":"North America"},{"code":"OC","name":"Oceania"},'
    '{"code":"SA","name":"South America"}]}}'
)


async def run_sync_test(event_loop, server, test_function):
    """This function will run the test in a different Thread.

    This allows us to run sync code while aiohttp server can still run.
    """
    executor = ThreadPoolExecutor(max_workers=2)
    test_task = event_loop.run_in_executor(executor, test_function)

    await test_task
    await server.close()


@pytest.mark.asyncio
async def test_requests_query(event_loop, aiohttp_server):
    async def handler(request):
        return web.Response(text=query1_server_answer, content_type="application/json")

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        with Client(transport=sample_transport,) as session:

            query = gql(query1_str)

            # Execute query synchronously
            result = session.execute(query)

            continents = result["continents"]

            africa = continents[0]

            assert africa["code"] == "AF"

    await run_sync_test(event_loop, server, test_code)


@pytest.mark.asyncio
async def test_requests_error_code_500(event_loop, aiohttp_server):
    async def handler(request):
        # Will generate http error code 500
        raise Exception("Server error")

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        with Client(transport=sample_transport,) as session:

            query = gql(query1_str)

            with pytest.raises(TransportServerError):
                session.execute(query)

    await run_sync_test(event_loop, server, test_code)


query1_server_error_answer = '{"errors": ["Error 1", "Error 2"]}'


@pytest.mark.asyncio
async def test_requests_error_code(event_loop, aiohttp_server):
    async def handler(request):
        return web.Response(
            text=query1_server_error_answer, content_type="application/json"
        )

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        with Client(transport=sample_transport,) as session:

            query = gql(query1_str)

            with pytest.raises(TransportQueryError):
                session.execute(query)

    await run_sync_test(event_loop, server, test_code)


invalid_protocol_responses = [
    "{}",
    "qlsjfqsdlkj",
    '{"not_data_or_errors": 35}',
]


@pytest.mark.asyncio
@pytest.mark.parametrize("response", invalid_protocol_responses)
async def test_requests_invalid_protocol(event_loop, aiohttp_server, response):
    async def handler(request):
        return web.Response(text=response, content_type="application/json")

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        with Client(transport=sample_transport,) as session:

            query = gql(query1_str)

            with pytest.raises(TransportProtocolError):
                session.execute(query)

    await run_sync_test(event_loop, server, test_code)


@pytest.mark.asyncio
async def test_requests_cannot_connect_twice(event_loop, aiohttp_server):
    async def handler(request):
        return web.Response(text=query1_server_answer, content_type="application/json")

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        with Client(transport=sample_transport,) as session:

            with pytest.raises(TransportAlreadyConnected):
                session.transport.connect()

    await run_sync_test(event_loop, server, test_code)


@pytest.mark.asyncio
async def test_requests_cannot_execute_if_not_connected(event_loop, aiohttp_server):
    async def handler(request):
        return web.Response(text=query1_server_answer, content_type="application/json")

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        query = gql(query1_str)

        with pytest.raises(TransportClosed):
            sample_transport.execute(query)

    await run_sync_test(event_loop, server, test_code)


partial_schema = """

type Continent {
  code: ID!
  name: String!
}

type Query {
  continents: [Continent!]!
}

"""


@pytest.mark.asyncio
async def test_requests_query_with_custom_types(event_loop, aiohttp_server):
    async def handler(request):
        return web.Response(text=query1_server_answer, content_type="application/json")

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    server = await aiohttp_server(app)

    url = server.make_url("/")

    def test_code():
        sample_transport = RequestsHTTPTransport(url=url)

        custom_types = {"String": Capitalize}

        # Instanciate a client which will capitalize all the String scalars
        with Client(
            transport=sample_transport,
            type_def=partial_schema,
            custom_types=custom_types,
        ) as session:

            query = gql(query1_str)

            # Execute query synchronously
            result = session.execute(query)

            continents = result["continents"]

            africa = continents[0]

            assert africa["code"] == "AF"

            # Check that the string is capitalized
            assert africa["name"] == "AFRICA"

    await run_sync_test(event_loop, server, test_code)
