import pytest

from gql import Client
from gql.dsl import DSLSchema

from .schema import StarWarsSchema


@pytest.fixture
def ds():
    return DSLSchema(StarWarsSchema)


@pytest.fixture
def client():
    return Client(schema=StarWarsSchema)


def test_invalid_field_on_type_query(ds):
    with pytest.raises(KeyError) as exc_info:
        ds.Query.extras.select(ds.Character.name)
    assert "Field extras does not exist in type Query." in str(exc_info.value)


def test_incompatible_field(ds):
    with pytest.raises(Exception) as exc_info:
        ds.gql("hero")
    assert "Received incompatible field" in str(exc_info.value)


def test_hero_name_query(ds):
    query = """
hero {
  name
}
    """.strip()
    query_dsl = ds.Query.hero.select(ds.Character.name)
    assert query == str(query_dsl)


def test_hero_name_and_friends_query(ds):
    query = """
hero {
  id
  name
  friends {
    name
  }
}
    """.strip()
    query_dsl = ds.Query.hero.select(
        ds.Character.id,
        ds.Character.name,
        ds.Character.friends.select(ds.Character.name,),
    )
    assert query == str(query_dsl)


def test_hero_id_and_name(ds):
    query = """
hero {
  id
  name
}
    """.strip()
    query_dsl = ds.Query.hero.select(ds.Character.id)
    query_dsl = query_dsl.select(ds.Character.name)
    assert query == str(query_dsl)


def test_nested_query(ds):
    query = """
hero {
  name
  friends {
    name
    appearsIn
    friends {
      name
    }
  }
}
    """.strip()
    query_dsl = ds.Query.hero.select(
        ds.Character.name,
        ds.Character.friends.select(
            ds.Character.name,
            ds.Character.appears_in,
            ds.Character.friends.select(ds.Character.name),
        ),
    )
    assert query == str(query_dsl)


def test_fetch_luke_query(ds):
    query = """
human(id: "1000") {
  name
}
    """.strip()
    query_dsl = ds.Query.human(id="1000").select(ds.Human.name,)

    assert query == str(query_dsl)


def test_fetch_luke_aliased(ds):
    query = """
luke: human(id: "1000") {
  name
}
    """.strip()
    query_dsl = ds.Query.human.args(id=1000).alias("luke").select(ds.Character.name,)
    assert query == str(query_dsl)


def test_hero_name_query_result(ds, client):
    query = ds.gql(ds.Query.hero.select(ds.Character.name))
    result = client.execute(query)
    expected = {"hero": {"name": "R2-D2"}}
    assert result == expected


def test_arg_serializer_list(ds, client):
    query = ds.gql(
        ds.Query.characters.args(ids=[1000, 1001, 1003]).select(ds.Character.name,)
    )
    result = client.execute(query)
    expected = {
        "characters": [
            {"name": "Luke Skywalker"},
            {"name": "Darth Vader"},
            {"name": "Leia Organa"},
        ]
    }
    assert result == expected


def test_arg_serializer_enum(ds, client):
    query = ds.gql(ds.Query.hero.args(episode=5).select(ds.Character.name))
    result = client.execute(query)
    expected = {"hero": {"name": "Luke Skywalker"}}
    assert result == expected


def test_create_review_mutation_result(ds, client):

    query = ds.gql(
        ds.Mutation.createReview.args(
            episode=6, review={"stars": 5, "commentary": "This is a great movie!"}
        ).select(ds.Review.stars, ds.Review.commentary),
        operation="mutation",
    )
    result = client.execute(query)
    expected = {"createReview": {"stars": 5, "commentary": "This is a great movie!"}}
    assert result == expected


def test_invalid_arg(ds):
    with pytest.raises(
        KeyError, match="Argument invalid_arg does not exist in Field: Character."
    ):
        ds.Query.hero.args(invalid_arg=5).select(ds.Character.name)
