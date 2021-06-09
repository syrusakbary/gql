import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLString,
)

from gql.compiler.query_parser import QueryParser
from gql.compiler.renderer_dataclasses import DataclassesRenderer
from gql.compiler.runtime.enum_utils import MissingEnumException
from gql.compiler.utils_codegen import camel_case_to_lower_case

from .conftest import load_module

FRAGMENT_DIRNAME = "fragment"


def test_simple_query(swapi_parser, swapi_dataclass_renderer):
    query = """
        query GetFilm {
            returnOfTheJedi: film(id: "1") {
            title
            director
            }
        }
    """

    parsed = swapi_parser.parse(query)
    rendered = swapi_dataclass_renderer.render(parsed, {}, {}, {}, None)

    m = load_module(rendered)
    response = m.GetFilm.GetFilmData.from_json(
        """
    {
        "returnOfTheJedi": {
            "title": "Return of the Jedi",
            "director": "George Lucas"
        }
    }
    """
    )

    assert response

    assert response.returnOfTheJedi.title == "Return of the Jedi"
    assert response.returnOfTheJedi.director == "George Lucas"


def _get_client(return_value: str) -> MagicMock:
    mock_client = MagicMock()
    mock_client.execute = MagicMock(return_value=json.loads(return_value))
    return mock_client


def test_simple_query_with_variables(swapi_parser, swapi_dataclass_renderer):
    query = """
        query GetFilm($id: ID!) {
            returnOfTheJedi: film(id: $id) {
            title
            director
            }
        }
    """

    parsed = swapi_parser.parse(query)
    rendered = swapi_dataclass_renderer.render(parsed, {}, {}, {}, None)

    m = load_module(rendered)

    mock_client = _get_client(
        """
        {
            "returnOfTheJedi": {
                "title": "Return of the Jedi",
                "director": "George Lucas"
            }
        }
    """
    )

    result = m.GetFilm.execute(mock_client, "luke")
    assert result
    assert isinstance(result, m.GetFilm.GetFilmData.Film)

    assert result.title == "Return of the Jedi"
    assert result.director == "George Lucas"


def test_simple_query_with_fragment(swapi_parser, swapi_dataclass_renderer):
    fragment_query = """
        fragment FilmFields on Film {
            title
            director
        }
    """

    query = """
        query GetFilm {
            returnOfTheJedi: film(id: "1") {
            ...FilmFields
            openingCrawl
            }
        }
    """

    parsed_fragment = swapi_parser.parse(fragment_query)
    rendered_fragment = swapi_dataclass_renderer.render(
        parsed_fragment, {}, {}, {}, None
    )

    load_module(rendered_fragment, module_name=camel_case_to_lower_case("FilmFields"))

    parsed = swapi_parser.parse(query, fragment_query)
    rendered = swapi_dataclass_renderer.render(
        parsed,
        {"FilmFields": "." + camel_case_to_lower_case("FilmFields")},
        {},
        {},
        None,
    )
    m = load_module(rendered)
    response = m.GetFilm.GetFilmData.from_json(
        """
    {
        "returnOfTheJedi": {
            "title": "Return of the Jedi",
            "director": "George Lucas",
            "openingCrawl": "la la la"
        }
    }
    """
    )

    assert response

    assert response.returnOfTheJedi.title == "Return of the Jedi"
    assert response.returnOfTheJedi.director == "George Lucas"
    assert response.returnOfTheJedi.openingCrawl == "la la la"


def test_simple_query_with_complex_fragment(swapi_parser, swapi_dataclass_renderer):
    fragment_query = """
        fragment CharacterFields on Person {
            name

            home: homeworld {
                name
            }
        }
    """
    query = """
        query GetPerson {
            luke: character(id: "luke") {
            ...CharacterFields
            }
        }
    """

    parsed_fragment = swapi_parser.parse(fragment_query)
    rendered_fragment = swapi_dataclass_renderer.render(
        parsed_fragment, {}, {}, {}, None
    )

    load_module(
        rendered_fragment, module_name=camel_case_to_lower_case("CharacterFields")
    )

    parsed = swapi_parser.parse(query, fragment_query)
    rendered = swapi_dataclass_renderer.render(
        parsed,
        {"CharacterFields": "." + camel_case_to_lower_case("CharacterFields")},
        {},
        {},
        None,
    )
    m = load_module(rendered)
    response = m.GetPerson.GetPersonData.from_json(
        """
    {
        "luke": {
            "name": "Luke Skywalker",
            "home": {
                "name": "Arakis"
            }
        }
    }
    """
    )

    assert response

    assert response.luke.name == "Luke Skywalker"
    assert response.luke.home.name == "Arakis"


def test_simple_query_with_complex_fragments(swapi_parser, swapi_dataclass_renderer):
    fragment_query1 = """
        fragment PlanetFields on Planet {
            name
            population
            terrains
        }
    """
    fragment_query2 = """
        fragment CharacterFields on Person {
            name
            home: homeworld {
            ...PlanetFields
            }
        }
    """
    query = """
        query GetPerson {
            luke: character(id: "luke") {
            ...CharacterFields
            }
        }
    """

    parsed_fragment1 = swapi_parser.parse(fragment_query1)
    rendered_fragment1 = swapi_dataclass_renderer.render(
        parsed_fragment1, {}, {}, {}, None
    )
    load_module(
        rendered_fragment1, module_name=camel_case_to_lower_case("PlanetFields")
    )

    parsed_fragment2 = swapi_parser.parse(fragment_query2, fragment_query1)
    rendered_fragment2 = swapi_dataclass_renderer.render(
        parsed_fragment2,
        {"PlanetFields": "." + camel_case_to_lower_case("PlanetFields")},
        {},
        {},
        None,
    )
    load_module(
        rendered_fragment2, module_name=camel_case_to_lower_case("CharacterFields")
    )

    parsed = swapi_parser.parse(query, fragment_query1 + fragment_query2)
    rendered = swapi_dataclass_renderer.render(
        parsed,
        {"CharacterFields": "." + camel_case_to_lower_case("CharacterFields")},
        {},
        {},
        None,
    )
    m = load_module(rendered)
    response = m.GetPerson.GetPersonData.from_json(
        """
    {
        "luke": {
            "name": "Luke Skywalker",
            "home": {
                "name": "Arakis",
                "population": "1,000,000",
                "terrains": ["Desert"]
            }
        }
    }
    """
    )

    assert response

    assert response.luke.name == "Luke Skywalker"
    assert response.luke.home.name == "Arakis"


def test_simple_query_with_complex_inline_fragment(
    swapi_parser, swapi_dataclass_renderer
):
    query = """
        query GetPerson {
            luke: character(id: "luke") {
            ... on Person {
                name
                home: homeworld {
                name
                }
            }
            }
        }
    """

    parsed = swapi_parser.parse(query)
    rendered = swapi_dataclass_renderer.render(parsed, {}, {}, {}, None)

    m = load_module(rendered)
    response = m.GetPerson.GetPersonData.from_json(
        """
        {
            "luke": {
                "name": "Luke Skywalker",
                "home": {
                    "name": "Arakis"
                }
            }
        }
        """
    )

    assert response

    assert response.luke.name == "Luke Skywalker"
    assert response.luke.home.name == "Arakis"


def test_simple_query_with_enums(github_parser, github_dataclass_renderer):
    query = """
        query MyIssues {
            viewer {
            issues(first: 5) {
                edges {
                node {
                    author { login }
                    authorAssociation
                }
                }
            }
            }
        }
    """
    parsed = github_parser.parse(query)

    rendered_enums = github_dataclass_renderer.render_enums(parsed)
    for enum_name, enum_code in rendered_enums.items():
        load_module(enum_code, module_name=camel_case_to_lower_case(enum_name))

    rendered = github_dataclass_renderer.render(
        parsed,
        {},
        {
            "CommentAuthorAssociation": "."
            + camel_case_to_lower_case("CommentAuthorAssociation")
        },
        {},
        None,
    )
    m = load_module(rendered)

    response = m.MyIssues.MyIssuesData.from_json(
        """
        {
            "viewer": {
                "issues": {
                    "edges": [
                        {
                            "node": {
                                "author": { "login": "whatever" },
                                "authorAssociation": "FIRST_TIMER"
                            }
                        }
                    ]
                }
            }
        }
        """
    )

    assert response

    node = response.viewer.issues.edges[0].node
    assert node
    assert node.author.login == "whatever"
    assert node.authorAssociation == m.CommentAuthorAssociation.FIRST_TIMER


def test_simple_query_with_missing_enums(github_parser, github_dataclass_renderer):
    query = """
        query MyIssues {
            viewer {
            issues(first: 5) {
                edges {
                node {
                    author { login }
                    authorAssociation
                }
                }
            }
            }
        }
    """
    parsed = github_parser.parse(query)

    rendered_enums = github_dataclass_renderer.render_enums(parsed)
    for enum_name, enum_code in rendered_enums.items():
        load_module(enum_code, module_name=camel_case_to_lower_case(enum_name))

    rendered = github_dataclass_renderer.render(
        parsed,
        {},
        {
            "CommentAuthorAssociation": "."
            + camel_case_to_lower_case("CommentAuthorAssociation")
        },
        {},
        None,
    )
    m = load_module(rendered)

    response = m.MyIssues.MyIssuesData.from_json(
        """
        {
            "viewer": {
                "issues": {
                    "edges": [
                        {
                            "node": {
                                "author": { "login": "whatever" },
                                "authorAssociation": "VALUE_THAT_DOES_NOT_EXIST"
                            }
                        }
                    ]
                }
            }
        }
        """
    )

    assert response

    node = response.viewer.issues.edges[0].node
    assert node
    assert node.author.login == "whatever"
    assert node.authorAssociation == m.CommentAuthorAssociation.MISSING_ENUM


def test_simple_query_with_input_objects(github_parser, github_dataclass_renderer):
    query = """
        query MyIssues($orderBy: IssueOrder) {
            viewer {
            issues(first: 5, orderBy: $orderBy) {
                edges {
                node {
                    author { login }
                }
                }
            }
            }
        }
    """
    parsed = github_parser.parse(query)

    rendered_enums = github_dataclass_renderer.render_enums(parsed)
    for enum_name, enum_code in rendered_enums.items():
        load_module(
            enum_code, module_name="enum." + camel_case_to_lower_case(enum_name)
        )

    rendered_input_objects = github_dataclass_renderer.render_input_objects(
        parsed, None
    )
    for input_object_name, input_object_code in rendered_input_objects.items():
        load_module(
            input_object_code,
            module_name="input." + camel_case_to_lower_case(input_object_name),
        )

    rendered = github_dataclass_renderer.render(
        parsed,
        {},
        {},
        {"IssueOrder": "." + "input." + camel_case_to_lower_case("IssueOrder")},
        None,
    )
    m = load_module(rendered)

    response = m.MyIssues.MyIssuesData.from_json(
        """
        {
            "viewer": {
                "issues": {
                    "edges": [
                        {
                            "node": {
                                "author": { "login": "whatever" }
                            }
                        }
                    ]
                }
            }
        }
        """
    )

    assert response

    node = response.viewer.issues.edges[0].node
    assert node
    assert node.author.login == "whatever"


def test_mutation_with_nested_input_objects(github_schema, github_parser, config_path):
    query = """
        mutation AddPullRequestReview($input: AddPullRequestReviewInput!) {
            addPullRequestReview(input: $input) {
            clientMutationId
            }
        }
    """

    parsed = github_parser.parse(query)

    github_dataclass_renderer = DataclassesRenderer(github_schema, config_path)

    rendered_enums = github_dataclass_renderer.render_enums(parsed)

    load_module(
        rendered_enums["PullRequestReviewEvent"],
        module_name="enum." + camel_case_to_lower_case("PullRequestReviewEvent"),
    )

    rendered_input_objects = github_dataclass_renderer.render_input_objects(
        parsed, "..config"
    )

    load_module(
        rendered_input_objects["DraftPullRequestReviewComment"],
        module_name="input."
        + camel_case_to_lower_case("DraftPullRequestReviewComment"),
    )
    add_pull_request_review_input = load_module(
        rendered_input_objects["AddPullRequestReviewInput"],
        module_name="input." + camel_case_to_lower_case("AddPullRequestReviewInput"),
    )

    rendered = github_dataclass_renderer.render(
        parsed,
        {},
        {
            "PullRequestReviewEvent": "."
            + "enum."
            + camel_case_to_lower_case("PullRequestReviewEvent")
        },
        {
            "DraftPullRequestReviewComment": "."
            + "input."
            + camel_case_to_lower_case("DraftPullRequestReviewComment"),
            "AddPullRequestReviewInput": "."
            + "input."
            + camel_case_to_lower_case("AddPullRequestReviewInput"),
        },
        None,
    )
    m = load_module(rendered)

    mock_client = _get_client(
        """
        {
            "addPullRequestReview": {
                "clientMutationId": "ABC"
            }
        }
        """
    )

    response = m.AddPullRequestReview.execute(
        mock_client,
        add_pull_request_review_input.AddPullRequestReviewInput(
            pullRequestId="A", commitOID="B"
        ),
    )

    assert response

    assert response.clientMutationId == "ABC"


def test_simple_query_with_enums_default_value():
    """
    enum LengthUnit {
        METER
        KM
    }

    type Starship {
        id: ID!
        name: String!
        length(unit: LengthUnit = METER): Float
        newLength(input: UnitInput!): Float
    }

    type Query {
        ship(id: String!): Starship
    }
    """

    length_unit_enum = GraphQLEnumType(
        "LengthUnit",
        {"METER": GraphQLEnumValue("METER"), "KM": GraphQLEnumValue("KM")},
        description="One of the films in the Star Wars Trilogy",
    )

    input_object_type = GraphQLInputObjectType(
        "UnitInput", {"unit": GraphQLInputField(GraphQLNonNull(length_unit_enum))}
    )

    starship_type = GraphQLObjectType(
        "Starship",
        lambda: {
            "id": GraphQLField(
                GraphQLNonNull(GraphQLString), description="The id of the ship."
            ),
            "name": GraphQLField(GraphQLString, description="The name of the ship."),
            "length": GraphQLField(
                GraphQLInt,
                args={
                    "unit": GraphQLArgument(
                        GraphQLNonNull(length_unit_enum), default_value="METER"
                    )
                },
            ),
            "newLength": GraphQLField(
                GraphQLInt,
                args={"input": GraphQLArgument(GraphQLNonNull(input_object_type))},
            ),
        },
    )

    query_type = GraphQLObjectType(
        "Query",
        lambda: {
            "ship": GraphQLField(
                starship_type,
                args={
                    "id": GraphQLArgument(
                        GraphQLNonNull(GraphQLString), description="id of the ship"
                    )
                },
            )
        },
    )

    schema = GraphQLSchema(query_type, types=[length_unit_enum, starship_type])

    query = """
        query GetStarship($unit: LengthUnit!, $input: UnitInput!) {
            ship(id: "Enterprise") {
                id
                name
                length(unit: $unit)
                newLength(input: $input)
            }
        }
    """
    query_parser = QueryParser(schema)
    query_renderer = DataclassesRenderer(schema)
    parsed = query_parser.parse(query)

    rendered_enums = query_renderer.render_enums(parsed)
    assert len(rendered_enums) == 1
    enum_module = load_module(
        list(rendered_enums.values())[0],
        module_name="enum." + camel_case_to_lower_case(list(rendered_enums.keys())[0]),
    )

    rendered_inputs = query_renderer.render_input_objects(parsed, None)
    assert len(rendered_inputs) == 1
    input_module = load_module(
        list(rendered_inputs.values())[0],
        module_name="input."
        + camel_case_to_lower_case(list(rendered_inputs.keys())[0]),
    )

    rendered = query_renderer.render(
        parsed,
        {},
        {"LengthUnit": "." + "enum." + camel_case_to_lower_case("LengthUnit")},
        {"UnitInput": "." + "input." + camel_case_to_lower_case("UnitInput")},
        None,
    )

    m = load_module(rendered)

    mock_client = _get_client(
        """
        {
            "ship": {
                "id": "Enterprise",
                "name": "Enterprise",
                "length": 100,
                "newLength": 200
            }
        }
        """
    )

    response = m.GetStarship.execute(
        mock_client,
        enum_module.LengthUnit("METER"),
        input_module.UnitInput(unit=enum_module.LengthUnit("METER")),
    )

    assert response

    assert response.id == "Enterprise"
    assert response.name == "Enterprise"
    assert response.length == 100

    with pytest.raises(MissingEnumException) as excinfo:
        m.GetStarship.execute(
            mock_client,
            enum_module.LengthUnit("MILE"),
            input_module.UnitInput(unit=enum_module.LengthUnit("METER")),
        )
    assert str(excinfo.value) == "Try to encode missing value of enum LengthUnit"


def test_simple_query_with_datetime(swapi_parser, swapi_dataclass_renderer):
    query = """
        query GetFilm($id: ID!) {
            returnOfTheJedi: film(id: $id) {
            title
            director
            releaseDate
            }
        }
    """

    parsed = swapi_parser.parse(query)
    rendered = swapi_dataclass_renderer.render(parsed, {}, {}, {}, ".config")

    m = load_module(rendered)

    now = datetime.now()

    mock_client = _get_client(
        """
        {
            "returnOfTheJedi": {
                "title": "Return of the Jedi",
                "director": "George Lucas",
                "releaseDate": "%s"
            }
        }
    """
        % now.isoformat()
    )

    result = m.GetFilm.execute(mock_client, "luke")
    assert isinstance(result, m.GetFilm.GetFilmData.Film)

    assert result.title == "Return of the Jedi"
    assert result.director == "George Lucas"
    assert result.releaseDate == now


def test_non_nullable_list():

    PersonType = GraphQLObjectType(
        "Person", lambda: {"name": GraphQLField(GraphQLString)}
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="RootQueryType",
            fields={
                "people": GraphQLField(
                    GraphQLList(GraphQLNonNull(PersonType)),
                    resolve=lambda obj, info: {"name": "eran"},
                )
            },
        )
    )

    query = """
            query GetPeople {
                people {
                name
                }
            }
        """

    parser = QueryParser(schema)
    dataclass_renderer = DataclassesRenderer(schema)

    parsed = parser.parse(query)
    rendered = dataclass_renderer.render(parsed, {}, {}, {}, None)

    m = load_module(rendered)

    mock_client = _get_client(
        """
        {
            "people": [
                {
                "name": "eran"
                },
                {
                "name": "eran1"
                }
            ]
        }
    """
    )

    result = m.GetPeople.execute(mock_client)
    assert result
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], m.GetPeople.GetPeopleData.Person)
    assert result[0].name == "eran"
    assert result[1].name == "eran1"


def test_render_subscription():
    def subscribe(_root, _info, breed):
        yield "dog"

    def resolve(s, _info, **_args):
        return s

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="RootQueryType",
            fields={
                "people": GraphQLField(
                    GraphQLString, resolve=lambda obj, info: "result"
                )
            },
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields=lambda: {
                "strAdded": GraphQLField(
                    GraphQLString, subscribe=subscribe, resolve=resolve
                )
            },
        ),
    )

    query = """
            subscription Subscription {
                strAdded
            }
        """

    parser = QueryParser(schema)

    dataclass_renderer = DataclassesRenderer(schema)

    parsed = parser.parse(query)
    rendered = dataclass_renderer.render(parsed, {}, {}, {}, None)

    m = load_module(rendered)

    mock_client = _get_client(
        """
        {
            "strAdded": "dogs"
        }
    """
    )

    result = m.Subscription.subscribe(mock_client)
    assert result


def test_render_query_with_custom_scalars(config_path):

    dateTimeType = GraphQLScalarType("DateTime")

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="RootQueryType",
            fields={
                "max": GraphQLField(
                    dateTimeType,
                    args={
                        "times": GraphQLArgument(
                            GraphQLList(GraphQLNonNull(dateTimeType)),
                            description="time",
                        )
                    },
                    resolve=lambda obj, info: "3",
                )
            },
        )
    )

    query = """
            query GetTime($times: [DateTime!]) {
                max(times: $times)
            }
        """

    parser = QueryParser(schema)

    dataclass_renderer = DataclassesRenderer(schema, config_path)

    parsed = parser.parse(query)
    rendered = dataclass_renderer.render(parsed, {}, {}, {}, ".config")

    m = load_module(rendered)

    mock_client = _get_client(
        """
        {
            "max": "2020-12-30T19:01:38.750931+00:00"
        }
    """
    )

    result = m.GetTime.execute(mock_client, [datetime.now()])
    assert result
