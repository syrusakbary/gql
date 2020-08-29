"""Tests for the GraphQL Response Parser.

At the moment we use the Star Wars schema which is fetched each time from the
server endpoint. In future it would be better to store this schema in a file
locally.
"""
import copy
import os

import pytest
import requests
import vcr
from graphql import GraphQLSchema

from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from gql.type_adapter import TypeAdapter

# We serve https://github.com/graphql-python/swapi-graphene locally:
URL = "http://127.0.0.1:8000/graphql"


query_vcr = vcr.VCR(
    cassette_library_dir=os.path.join(
        os.path.dirname(__file__), "fixtures", "vcr_cassettes"
    ),
    record_mode="new_episodes",
    match_on=["uri", "method", "body"],
)


def use_cassette(name):
    return query_vcr.use_cassette(name + ".yaml")


@pytest.fixture
def client():
    with use_cassette("client"):
        response = requests.get(
            URL, headers={"Host": "swapi.graphene-python.org", "Accept": "text/html"}
        )
        response.raise_for_status()
        csrf = response.cookies["csrftoken"]

        return Client(
            transport=RequestsHTTPTransport(
                url=URL, cookies={"csrftoken": csrf}, headers={"x-csrftoken": csrf}
            ),
            fetch_schema_from_transport=True,
        )


class Capitalize:
    @classmethod
    def parse_value(cls, value: str):
        return value.upper()


@pytest.fixture()
def schema(client):
    return client.schema


def test_scalar_type_name_for_scalar_field_returns_name(schema: GraphQLSchema):
    type_adapter = TypeAdapter(schema)
    schema_obj = schema.query_type.fields["film"] if schema.query_type else None

    assert (
        type_adapter._get_scalar_type_name(schema_obj.type.fields["releaseDate"])
        == "Date"
    )


def test_scalar_type_name_for_non_scalar_field_returns_none(schema: GraphQLSchema):
    type_adapter = TypeAdapter(schema)
    schema_obj = schema.query_type.fields["film"] if schema.query_type else None

    assert type_adapter._get_scalar_type_name(schema_obj.type.fields["species"]) is None


def test_lookup_scalar_type(schema):
    type_adapter = TypeAdapter(schema)

    assert type_adapter._lookup_scalar_type(["film"]) is None
    assert type_adapter._lookup_scalar_type(["film", "releaseDate"]) == "Date"
    assert type_adapter._lookup_scalar_type(["film", "species"]) is None


def test_lookup_scalar_type_in_mutation(schema: GraphQLSchema):
    type_adapter = TypeAdapter(schema)

    assert type_adapter._lookup_scalar_type(["createHero"]) is None
    assert type_adapter._lookup_scalar_type(["createHero", "hero"]) is None
    assert type_adapter._lookup_scalar_type(["createHero", "ok"]) == "Boolean"


def test_parse_response(schema: GraphQLSchema):
    custom_types = {"Date": Capitalize}
    type_adapter = TypeAdapter(schema, custom_types)

    response = {"film": {"id": "some_id", "releaseDate": "some_datetime"}}

    expected = {"film": {"id": "some_id", "releaseDate": "SOME_DATETIME"}}

    assert type_adapter.convert_scalars(response) == expected
    # ensure original response is not changed
    assert response["film"]["releaseDate"] == "some_datetime"


def test_parse_response_containing_list(schema: GraphQLSchema):
    custom_types = {"Date": Capitalize}
    type_adapter = TypeAdapter(schema, custom_types)

    response = {
        "allFilms": {
            "edges": [
                {"node": {"id": "some_id", "releaseDate": "some_datetime"}},
                {"node": {"id": "some_id", "releaseDate": "some_other_datetime"}},
            ]
        }
    }

    expected = copy.deepcopy(response)
    expected["allFilms"]["edges"][0]["node"]["releaseDate"] = "SOME_DATETIME"
    expected["allFilms"]["edges"][1]["node"]["releaseDate"] = "SOME_OTHER_DATETIME"

    result = type_adapter.convert_scalars(response)
    assert result == expected

    # ensure original response is not changed
    assert response["allFilms"]["edges"][0]["node"]["releaseDate"] == "some_datetime"
    # ensure original response is not changed
    assert (
        response["allFilms"]["edges"][1]["node"]["releaseDate"] == "some_other_datetime"
    )
