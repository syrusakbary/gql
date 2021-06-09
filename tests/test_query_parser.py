from dataclasses import asdict

import pytest
from deepdiff import DeepDiff

from gql.compiler.query_parser import (
    InvalidQueryError,
    ParsedEnum,
    ParsedField,
    ParsedObject,
    ParsedOperation,
    ParsedQuery,
    ParsedVariableDefinition,
    QueryParser,
)


def test_parser_fails_invalid_query(swapi_schema):
    query = """
        query ShouldFail {
            allFilms {
            totalCount
            edges {
                node {
                title
                nonExistingField
                }
            }
            }
        }
    """

    parser = QueryParser(swapi_schema)

    with pytest.raises(InvalidQueryError):
        parser.parse(query)


def test_parser_query(swapi_schema):
    query = """
        query GetFilm {
            returnOfTheJedi: film(id: "1") {
            title
            director
            }
        }
    """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetFilm",
                    type="query",
                    children=[
                        ParsedObject(
                            name="GetFilmData",
                            fields=[
                                ParsedField(
                                    name="returnOfTheJedi",
                                    type="Film",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="Film",
                                    fields=[
                                        ParsedField(
                                            name="title",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                        ParsedField(
                                            name="director",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_query_inline_fragment(swapi_schema):
    query = """
        query GetFilm {
            returnOfTheJedi: film(id: "1") {
            ... on Film {
                title
                director
            }
            }
        }
    """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetFilm",
                    type="query",
                    children=[
                        ParsedObject(
                            name="GetFilmData",
                            fields=[
                                ParsedField(
                                    name="returnOfTheJedi",
                                    type="Film",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="Film",
                                    fields=[
                                        ParsedField(
                                            name="title",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                        ParsedField(
                                            name="director",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_query_fragment(swapi_schema):
    query = """
        query GetFilm {
            returnOfTheJedi: film(id: "1") {
            id
            ...FilmFields
            }
        }

        fragment FilmFields on Film {
            title
            director
        }
    """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetFilm",
                    type="query",
                    children=[
                        ParsedObject(
                            name="GetFilmData",
                            fields=[
                                ParsedField(
                                    name="returnOfTheJedi",
                                    type="Film",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="Film",
                                    parents=["FilmFields"],
                                    fields=[
                                        ParsedField(
                                            name="id",
                                            type="ID",
                                            nullable=False,
                                            is_list=False,
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
            fragment_objects=[
                ParsedObject(
                    name="FilmFields",
                    fields=[
                        ParsedField(
                            name="title", type="String", nullable=False, is_list=False
                        ),
                        ParsedField(
                            name="director",
                            type="String",
                            nullable=False,
                            is_list=False,
                        ),
                    ],
                )
            ],
            used_fragments=["FilmFields"],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_query_complex_fragment(swapi_schema):
    query = """
            query GetPerson {
                luke: character(id: "luke") {
                ...CharacterFields
                }
            }

            fragment CharacterFields on Person {
                name

                home: homeworld {
                    name
                }
            }
        """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetPerson",
                    type="query",
                    children=[
                        ParsedObject(
                            name="GetPersonData",
                            fields=[
                                ParsedField(
                                    name="luke",
                                    type="Person",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="Person",
                                    parents=["CharacterFields"],
                                    fields=[],
                                )
                            ],
                        )
                    ],
                )
            ],
            fragment_objects=[
                ParsedObject(
                    name="CharacterFields",
                    fields=[
                        ParsedField(
                            name="name", type="String", nullable=False, is_list=False
                        ),
                        ParsedField(
                            name="home", type="Planet", nullable=False, is_list=False
                        ),
                    ],
                    children=[
                        ParsedObject(
                            name="Planet",
                            fields=[
                                ParsedField(
                                    name="name",
                                    type="String",
                                    nullable=False,
                                    is_list=False,
                                )
                            ],
                        )
                    ],
                )
            ],
            used_fragments=["CharacterFields"],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_query_with_variables(swapi_schema):
    query = """
        query GetFilm($theFilmID: ID!) {
            returnOfTheJedi: film(id: $theFilmID) {
            title
            director
            }
        }
    """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetFilm",
                    type="query",
                    variables=[
                        ParsedVariableDefinition(
                            name="theFilmID", type="ID", nullable=False, is_list=False
                        )
                    ],
                    children=[
                        ParsedObject(
                            name="GetFilmData",
                            fields=[
                                ParsedField(
                                    name="returnOfTheJedi",
                                    type="Film",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="Film",
                                    fields=[
                                        ParsedField(
                                            name="title",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                        ParsedField(
                                            name="director",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


'''
def test_parser_query_with_enum_variables(github_schema):
    query = """
        query GetRepositories($privacy: RepositoryPrivacy) {
            repositories(privacy: $privacy) {
            nodes {
                databaseId
            }
            }
        }
    """

    parser = QueryParser(github_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetRepositories",
                    type="query",
                    variables=[
                        ParsedVariableDefinition(
                            name="theFilmID",
                            type="ID",
                            nullable=False,
                            is_list=False,
                        )
                    ],
                    children=[
                        ParsedObject(
                            name="GetFilmData",
                            fields=[
                                ParsedField(
                                    name="returnOfTheJedi",
                                    type="Film",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="Film",
                                    fields=[
                                        ParsedField(
                                            name="title",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                        ParsedField(
                                            name="director",
                                            type="String",
                                            nullable=False,
                                            is_list=False,
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
            enums=[
                ParsedEnum
            ]
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))
'''


def test_parser_connection_query(swapi_schema):
    query = """
        query GetAllFilms {
            allFilms {
            count: totalCount
            edges {
                node {
                id
                title
                director
                }
            }
            }
            allHeroes {
            edges {
                node {
                ...HeroFields
                }
            }
            }
        }

        fragment HeroFields on Hero {
            id
            name
        }

    """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="GetAllFilms",
                    type="query",
                    children=[
                        ParsedObject(
                            name="GetAllFilmsData",
                            fields=[
                                ParsedField(
                                    name="allFilms",
                                    type="FilmConnection",
                                    nullable=True,
                                    is_list=False,
                                ),
                                ParsedField(
                                    name="allHeroes",
                                    type="HeroConnection",
                                    nullable=True,
                                    is_list=False,
                                ),
                            ],
                            children=[
                                ParsedObject(
                                    name="FilmConnection",
                                    fields=[
                                        ParsedField(
                                            name="count",
                                            type="Int",
                                            nullable=True,
                                            is_list=False,
                                        ),
                                        ParsedField(
                                            name="edges",
                                            type="FilmEdge",
                                            nullable=True,
                                            is_list=True,
                                        ),
                                    ],
                                    children=[
                                        ParsedObject(
                                            name="FilmEdge",
                                            fields=[
                                                ParsedField(
                                                    name="node",
                                                    type="Film",
                                                    nullable=True,
                                                    is_list=False,
                                                )
                                            ],
                                            children=[
                                                ParsedObject(
                                                    name="Film",
                                                    fields=[
                                                        ParsedField(
                                                            name="id",
                                                            type="ID",
                                                            nullable=False,
                                                            is_list=False,
                                                        ),
                                                        ParsedField(
                                                            name="title",
                                                            type="String",
                                                            nullable=False,
                                                            is_list=False,
                                                        ),
                                                        ParsedField(
                                                            name="director",
                                                            type="String",
                                                            nullable=False,
                                                            is_list=False,
                                                        ),
                                                    ],
                                                )
                                            ],
                                        )
                                    ],
                                ),
                                ParsedObject(
                                    name="HeroConnection",
                                    fields=[
                                        ParsedField(
                                            name="edges",
                                            type="HeroEdge",
                                            nullable=True,
                                            is_list=True,
                                        )
                                    ],
                                    children=[
                                        ParsedObject(
                                            name="HeroEdge",
                                            fields=[
                                                ParsedField(
                                                    name="node",
                                                    type="Hero",
                                                    nullable=True,
                                                    is_list=False,
                                                )
                                            ],
                                            children=[
                                                ParsedObject(
                                                    name="Hero",
                                                    parents=["HeroFields"],
                                                    fields=[],
                                                )
                                            ],
                                        )
                                    ],
                                ),
                            ],
                        )
                    ],
                )
            ],
            fragment_objects=[
                ParsedObject(
                    name="HeroFields",
                    fields=[
                        ParsedField(
                            name="id", type="ID", nullable=False, is_list=False
                        ),
                        ParsedField(
                            name="name", type="String", nullable=False, is_list=False
                        ),
                    ],
                )
            ],
            used_fragments=["HeroFields"],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_query_with_enums(github_parser):
    query = """
        query MyIssues($states: [IssueState!], $orderBy: IssueOrder) {
            viewer {
            issues(first: 5, states: $states, orderBy: $orderBy) {
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

    issue_child = ParsedObject(
        name="Issue",
        fields=[
            ParsedField(name="author", type="Actor", nullable=True, is_list=False),
            ParsedField(
                name="authorAssociation",
                type="CommentAuthorAssociation",
                nullable=False,
                is_list=False,
            ),
        ],
        children=[
            ParsedObject(
                name="Actor",
                fields=[
                    ParsedField(
                        name="login", type="String", nullable=False, is_list=False
                    )
                ],
            )
        ],
    )
    child = ParsedObject(
        name="MyIssuesData",
        fields=[ParsedField(name="viewer", type="User", nullable=False, is_list=False)],
        children=[
            ParsedObject(
                name="User",
                fields=[
                    ParsedField(
                        name="issues",
                        type="IssueConnection",
                        nullable=False,
                        is_list=False,
                    )
                ],
                children=[
                    ParsedObject(
                        name="IssueConnection",
                        fields=[
                            ParsedField(
                                name="edges",
                                type="IssueEdge",
                                nullable=True,
                                is_list=True,
                            )
                        ],
                        children=[
                            ParsedObject(
                                name="IssueEdge",
                                fields=[
                                    ParsedField(
                                        name="node",
                                        type="Issue",
                                        nullable=True,
                                        is_list=False,
                                    )
                                ],
                                children=[issue_child],
                            )
                        ],
                    )
                ],
            )
        ],
    )
    enums = [
        ParsedEnum(
            name="IssueOrderField",
            values={
                "COMMENTS": "COMMENTS",
                "CREATED_AT": "CREATED_AT",
                "UPDATED_AT": "UPDATED_AT",
            },
        ),
        ParsedEnum(name="OrderDirection", values={"ASC": "ASC", "DESC": "DESC"}),
    ]
    input_object = ParsedObject(
        name="IssueOrder",
        fields=[
            ParsedField(
                name="field", type="IssueOrderField", nullable=False, is_list=False
            ),
            ParsedField(
                name="direction", type="OrderDirection", nullable=False, is_list=False
            ),
        ],
        input_enums=enums,
    )
    expected = asdict(
        ParsedQuery(
            query=query,
            enums=[
                ParsedEnum(
                    name="IssueState", values={"CLOSED": "CLOSED", "OPEN": "OPEN"}
                ),
                ParsedEnum(
                    name="CommentAuthorAssociation",
                    values={
                        "MEMBER": "MEMBER",
                        "OWNER": "OWNER",
                        "COLLABORATOR": "COLLABORATOR",
                        "CONTRIBUTOR": "CONTRIBUTOR",
                        "FIRST_TIME_CONTRIBUTOR": "FIRST_TIME_CONTRIBUTOR",
                        "FIRST_TIMER": "FIRST_TIMER",
                        "NONE": "NONE",
                    },
                ),
            ],
            input_objects=[input_object],
            internal_enums=enums,
            objects=[
                ParsedOperation(
                    name="MyIssues",
                    type="query",
                    children=[child],
                    variables=[
                        ParsedVariableDefinition(
                            name="states",
                            type="IssueState",
                            is_list=True,
                            nullable=False,
                        ),
                        ParsedVariableDefinition(
                            name="orderBy",
                            type="IssueOrder",
                            is_list=False,
                            nullable=True,
                        ),
                    ],
                )
            ],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_mutation(swapi_schema):
    query = """
        mutation CreateHero {
            createHero {
            hero {
                name
            }
            ok
            }
        }
    """

    parser = QueryParser(swapi_schema)
    parsed = parser.parse(query)

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="CreateHero",
                    type="mutation",
                    children=[
                        ParsedObject(
                            name="CreateHeroData",
                            fields=[
                                ParsedField(
                                    name="createHero",
                                    type="CreateHeroPayload",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                            children=[
                                ParsedObject(
                                    name="CreateHeroPayload",
                                    fields=[
                                        ParsedField(
                                            name="hero",
                                            type="Hero",
                                            nullable=True,
                                            is_list=False,
                                        ),
                                        ParsedField(
                                            name="ok",
                                            type="Boolean",
                                            nullable=True,
                                            is_list=False,
                                        ),
                                    ],
                                    children=[
                                        ParsedObject(
                                            name="Hero",
                                            fields=[
                                                ParsedField(
                                                    name="name",
                                                    type="String",
                                                    nullable=False,
                                                    is_list=False,
                                                )
                                            ],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))


def test_parser_mutation_with_nested_inputs(github_schema):
    query = """
        mutation AddPullRequestReview($input: AddPullRequestReviewInput!) {
            addPullRequestReview(input: $input) {
            clientMutationId
            }
        }
    """

    parser = QueryParser(github_schema)
    parsed = parser.parse(query)

    enums = [
        ParsedEnum(
            name="PullRequestReviewEvent",
            values={
                "APPROVE": "APPROVE",
                "COMMENT": "COMMENT",
                "DISMISS": "DISMISS",
                "REQUEST_CHANGES": "REQUEST_CHANGES",
            },
        )
    ]

    inputs = [
        ParsedObject(
            name="DraftPullRequestReviewComment",
            fields=[
                ParsedField(name="path", type="String", nullable=False, is_list=False),
                ParsedField(name="position", type="Int", nullable=False, is_list=False),
                ParsedField(name="body", type="String", nullable=False, is_list=False),
            ],
        )
    ]

    expected = asdict(
        ParsedQuery(
            query=query,
            objects=[
                ParsedOperation(
                    name="AddPullRequestReview",
                    type="mutation",
                    variables=[
                        ParsedVariableDefinition(
                            name="input",
                            type="AddPullRequestReviewInput",
                            nullable=False,
                            is_list=False,
                        )
                    ],
                    children=[
                        ParsedObject(
                            name="AddPullRequestReviewData",
                            children=[
                                ParsedObject(
                                    name="AddPullRequestReviewPayload",
                                    fields=[
                                        ParsedField(
                                            name="clientMutationId",
                                            type="String",
                                            nullable=True,
                                            is_list=False,
                                        )
                                    ],
                                )
                            ],
                            fields=[
                                ParsedField(
                                    name="addPullRequestReview",
                                    type="AddPullRequestReviewPayload",
                                    nullable=True,
                                    is_list=False,
                                )
                            ],
                        )
                    ],
                )
            ],
            input_objects=[
                ParsedObject(
                    name="AddPullRequestReviewInput",
                    fields=[
                        ParsedField(
                            name="pullRequestId",
                            type="ID",
                            nullable=False,
                            is_list=False,
                        ),
                        ParsedField(
                            name="commitOID",
                            type="GitObjectID",
                            nullable=True,
                            is_list=False,
                        ),
                        ParsedField(
                            name="body", type="String", nullable=True, is_list=False
                        ),
                        ParsedField(
                            name="event",
                            type="PullRequestReviewEvent",
                            nullable=True,
                            is_list=False,
                        ),
                        ParsedField(
                            name="comments",
                            type="DraftPullRequestReviewComment",
                            nullable=True,
                            is_list=True,
                        ),
                        ParsedField(
                            name="clientMutationId",
                            type="String",
                            nullable=True,
                            is_list=False,
                        ),
                    ],
                    input_enums=enums,
                    inputs=inputs,
                )
            ],
            internal_enums=enums,
            internal_inputs=inputs,
        )
    )

    parsed_dict = asdict(parsed)

    assert bool(parsed)
    assert parsed_dict == expected, str(DeepDiff(parsed_dict, expected))
