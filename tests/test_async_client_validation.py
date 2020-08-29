import asyncio
import json

import graphql
import pytest
import websockets

from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport

from .conftest import MS, WebSocketServer
from .starwars.schema import StarWarsIntrospection, StarWarsSchema, StarWarsTypeDef

starwars_expected_one = {
    "stars": 3,
    "commentary": "Was expecting more stuff",
    "episode": "JEDI",
}

starwars_expected_two = {
    "stars": 5,
    "commentary": "This is a great movie!",
    "episode": "JEDI",
}


async def server_starwars(ws, path):
    await WebSocketServer.send_connection_ack(ws)

    try:
        await ws.recv()

        reviews = [starwars_expected_one, starwars_expected_two]

        for review in reviews:

            data = (
                '{"type":"data","id":"1","payload":{"data":{"reviewAdded": '
                + json.dumps(review)
                + "}}}"
            )
            await ws.send(data)
            await asyncio.sleep(2 * MS)

        await WebSocketServer.send_complete(ws, 1)
        await WebSocketServer.wait_connection_terminate(ws)

    except websockets.exceptions.ConnectionClosedOK:
        pass

    print("Server is now closed")


starwars_subscription_str = """
    subscription ListenEpisodeReviews($ep: Episode!) {
      reviewAdded(episode: $ep) {
        stars,
        commentary,
        episode
      }
    }
"""

starwars_invalid_subscription_str = """
    subscription ListenEpisodeReviews($ep: Episode!) {
      reviewAdded(episode: $ep) {
        not_valid_field,
        stars,
        commentary,
        episode
      }
    }
"""


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [server_starwars], indirect=True)
@pytest.mark.parametrize("subscription_str", [starwars_subscription_str])
@pytest.mark.parametrize(
    "client_params",
    [
        {"schema": StarWarsSchema},
        {"introspection": StarWarsIntrospection},
        {"type_def": StarWarsTypeDef},
        {"schema": StarWarsTypeDef},
    ],
)
async def test_async_client_validation(
    event_loop, server, subscription_str, client_params
):

    url = f"ws://{server.hostname}:{server.port}/graphql"

    sample_transport = WebsocketsTransport(url=url)

    async with Client(transport=sample_transport, **client_params) as session:

        variable_values = {"ep": "JEDI"}

        subscription = gql(subscription_str)

        expected = []

        async for result in session.subscribe(
            subscription, variable_values=variable_values
        ):

            review = result["reviewAdded"]
            expected.append(review)

            assert "stars" in review
            assert "commentary" in review
            assert "episode" in review

        assert expected[0] == starwars_expected_one
        assert expected[1] == starwars_expected_two


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [server_starwars], indirect=True)
@pytest.mark.parametrize("subscription_str", [starwars_invalid_subscription_str])
@pytest.mark.parametrize(
    "client_params",
    [
        {"schema": StarWarsSchema},
        {"introspection": StarWarsIntrospection},
        {"type_def": StarWarsTypeDef},
        {"schema": StarWarsTypeDef},
    ],
)
async def test_async_client_validation_invalid_query(
    event_loop, server, subscription_str, client_params
):

    url = f"ws://{server.hostname}:{server.port}/graphql"

    sample_transport = WebsocketsTransport(url=url)

    async with Client(transport=sample_transport, **client_params) as session:

        variable_values = {"ep": "JEDI"}

        subscription = gql(subscription_str)

        with pytest.raises(graphql.error.GraphQLError):
            async for _result in session.subscribe(
                subscription, variable_values=variable_values
            ):
                pass


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [server_starwars], indirect=True)
@pytest.mark.parametrize("subscription_str", [starwars_invalid_subscription_str])
@pytest.mark.parametrize(
    "client_params",
    [
        {"schema": StarWarsSchema, "introspection": StarWarsIntrospection},
        {"schema": StarWarsSchema, "type_def": StarWarsTypeDef},
        {"introspection": StarWarsIntrospection, "type_def": StarWarsTypeDef},
    ],
)
async def test_async_client_validation_different_schemas_parameters_forbidden(
    event_loop, server, subscription_str, client_params
):

    url = f"ws://{server.hostname}:{server.port}/graphql"

    sample_transport = WebsocketsTransport(url=url)

    with pytest.raises(AssertionError):
        async with Client(transport=sample_transport, **client_params):
            pass


hero_server_answers = (
    '{"type":"data","id":"1","payload":{"data":'
    + json.dumps(StarWarsIntrospection)
    + "}}",
    '{"type":"data","id":"2","payload":{"data":{"hero":{"name": "R2-D2"}}}}',
)


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [hero_server_answers], indirect=True)
async def test_async_client_validation_fetch_schema_from_server_valid_query(
    event_loop, client_and_server
):
    session, server = client_and_server
    client = session.client

    # No schema in the client at the beginning
    assert client.introspection is None
    assert client.schema is None

    # Fetch schema from server
    await session.fetch_schema()

    # Check that the async client correctly recreated the schema
    assert client.introspection == StarWarsIntrospection
    assert client.schema is not None

    query = gql(
        """
        query HeroNameQuery {
          hero {
            name
          }
        }
    """
    )

    result = await session.execute(query)

    print("Client received:", result)
    expected = {"hero": {"name": "R2-D2"}}

    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [hero_server_answers], indirect=True)
async def test_async_client_validation_fetch_schema_from_server_invalid_query(
    event_loop, client_and_server
):
    session, server = client_and_server

    # Fetch schema from server
    await session.fetch_schema()

    query = gql(
        """
        query HeroNameQuery {
          hero {
            name
            sldkfjqlmsdkjfqlskjfmlqkjsfmkjqsdf
          }
        }
    """
    )

    with pytest.raises(graphql.error.GraphQLError):
        await session.execute(query)


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [hero_server_answers], indirect=True)
async def test_async_client_validation_fetch_schema_from_server_with_client_argument(
    event_loop, server
):
    url = f"ws://{server.hostname}:{server.port}/graphql"

    sample_transport = WebsocketsTransport(url=url)

    async with Client(
        transport=sample_transport, fetch_schema_from_transport=True,
    ) as session:

        query = gql(
            """
            query HeroNameQuery {
              hero {
                name
                sldkfjqlmsdkjfqlskjfmlqkjsfmkjqsdf
              }
            }
        """
        )

        with pytest.raises(graphql.error.GraphQLError):
            await session.execute(query)


class ToLowercase:
    @staticmethod
    def parse_value(value: str):
        return value.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("server", [hero_server_answers], indirect=True)
async def test_async_client_validation_fetch_schema_from_server_with_custom_types(
    event_loop, server
):

    url = f"ws://{server.hostname}:{server.port}/graphql"

    sample_transport = WebsocketsTransport(url=url)

    custom_types = {"String": ToLowercase}

    async with Client(
        transport=sample_transport,
        fetch_schema_from_transport=True,
        custom_types=custom_types,
    ) as session:

        query = gql(
            """
            query HeroNameQuery {
              hero {
                name
              }
            }
        """
        )

        result = await session.execute(query)

        print("Client received:", result)

        # The expected hero name is now in lowercase
        expected = {"hero": {"name": "r2-d2"}}

        assert result == expected
