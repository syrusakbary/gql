from graphql.type import (GraphQLArgument, GraphQLEnumType, GraphQLEnumValue,
                          GraphQLField, GraphQLInterfaceType, GraphQLList,
                          GraphQLNonNull, GraphQLObjectType, GraphQLSchema,
                          GraphQLString, GraphQLInt, GraphQLInputObjectType,
                          GraphQLInputObjectField)

from .fixtures import createReview, getCharacters, getDroid, getFriends, getHero, getHuman, reviewAdded

episodeEnum = GraphQLEnumType(
    'Episode',
    description='One of the films in the Star Wars Trilogy',
    values={
        'NEWHOPE': GraphQLEnumValue(
            value='NEWHOPE',
            description='Released in 1977.',
        ),
        'EMPIRE': GraphQLEnumValue(
            value='EMPIRE',
            description='Released in 1980.',
        ),
        'JEDI': GraphQLEnumValue(
            value='JEDI',
            description='Released in 1983.',
        )
    }
)

characterInterface = GraphQLInterfaceType(
    'Character',
    description='A character in the Star Wars Trilogy',
    fields=lambda: {
        'id': GraphQLField(
            GraphQLNonNull(GraphQLString),
            description='The id of the character.'
        ),
        'name': GraphQLField(
            GraphQLString,
            description='The name of the character.'
        ),
        'friends': GraphQLField(
            GraphQLList(characterInterface),
            description='The friends of the character, or an empty list if they have none.'
        ),
        'appearsIn': GraphQLField(
            GraphQLList(episodeEnum),
            description='Which movies they appear in.'
        ),
    },
    resolve_type=lambda character, *_: humanType if getHuman(character.id) else droidType,
)

humanType = GraphQLObjectType(
    'Human',
    description='A humanoid creature in the Star Wars universe.',
    fields=lambda: {
        'id': GraphQLField(
            GraphQLNonNull(GraphQLString),
            description='The id of the human.',
        ),
        'name': GraphQLField(
            GraphQLString,
            description='The name of the human.',
        ),
        'friends': GraphQLField(
            GraphQLList(characterInterface),
            description='The friends of the human, or an empty list if they have none.',
            resolver=lambda human, info, **args: getFriends(human),
        ),
        'appearsIn': GraphQLField(
            GraphQLList(episodeEnum),
            description='Which movies they appear in.',
        ),
        'homePlanet': GraphQLField(
            GraphQLString,
            description='The home planet of the human, or null if unknown.',
        ),
    },
    interfaces=[characterInterface]
)

droidType = GraphQLObjectType(
    'Droid',
    description='A mechanical creature in the Star Wars universe.',
    fields=lambda: {
        'id': GraphQLField(
            GraphQLNonNull(GraphQLString),
            description='The id of the droid.',
        ),
        'name': GraphQLField(
            GraphQLString,
            description='The name of the droid.',
        ),
        'friends': GraphQLField(
            GraphQLList(characterInterface),
            description='The friends of the droid, or an empty list if they have none.',
            resolver=lambda droid, info, **args: getFriends(droid),
        ),
        'appearsIn': GraphQLField(
            GraphQLList(episodeEnum),
            description='Which movies they appear in.',
        ),
        'primaryFunction': GraphQLField(
            GraphQLString,
            description='The primary function of the droid.',
        )
    },
    interfaces=[characterInterface]
)

reviewType = GraphQLObjectType(
    'Review',
    description='Represents a review for a movie',
    fields=lambda: {
        'episode': GraphQLField(
            episodeEnum,
            description='The movie'
        ),
        'stars': GraphQLField(
            GraphQLNonNull(GraphQLInt),
            description='The number of stars this review gave, 1-5'
        ),
        'commentary': GraphQLField(
            GraphQLString,
            description='Comment about the movie'
        )
    }
)

reviewInputType = GraphQLInputObjectType(
    'ReviewInput',
    description='The input object sent when someone is creating a new review',
    fields={
        'stars': GraphQLInputObjectField(
            GraphQLInt,
            description='0-5 stars'
        ),
        'commentary': GraphQLInputObjectField(
            GraphQLString,
            description='Comment about the movie, optional'
        )
    }
)

queryType = GraphQLObjectType(
    'Query',
    fields=lambda: {
        'hero': GraphQLField(
            characterInterface,
            args={
                'episode': GraphQLArgument(
                    description='If omitted, returns the hero of the whole saga. If '
                                'provided, returns the hero of that particular episode.',
                    type=episodeEnum,
                )
            },
            resolver=lambda root, info, **args: getHero(args.get('episode')),
        ),
        'human': GraphQLField(
            humanType,
            args={
                'id': GraphQLArgument(
                    description='id of the human',
                    type=GraphQLNonNull(GraphQLString),
                )
            },
            resolver=lambda root, info, **args: getHuman(args['id']),
        ),
        'droid': GraphQLField(
            droidType,
            args={
                'id': GraphQLArgument(
                    description='id of the droid',
                    type=GraphQLNonNull(GraphQLString),
                )
            },
            resolver=lambda root, info, **args: getDroid(args['id']),
        ),
        'characters': GraphQLField(
            GraphQLList(characterInterface),
            args={
                'ids': GraphQLArgument(
                    description='list of character ids',
                    type=GraphQLList(GraphQLString),
                )
            },
            resolver=lambda root, info, **args: getCharacters(args['ids']),
        ),
    }
)

mutationType = GraphQLObjectType(
    'Mutation',
    description='The mutation type, represents all updates we can make to our data',
    fields=lambda: {
        'createReview': GraphQLField(
            reviewType,
            args={
                'episode': GraphQLArgument(
                    description='Episode to create review',
                    type=episodeEnum,
                ),
                'review': GraphQLArgument(
                    description='set alive status',
                    type=reviewInputType,
                ),
            },
            resolver=lambda root, info, **args: createReview(args.get('episode'), args.get('review')),
        ),
    }
)

subscriptionType = GraphQLObjectType(
    'Subscription',
    fields=lambda: {
        'reviewAdded': GraphQLField(
            reviewType,
            args={
                'episode': GraphQLArgument(
                    description='Episode to review',
                    type=episodeEnum,
                )
            },
            resolver=lambda root, info, **args: reviewAdded(args.get('episode')),
        )
    }
)

StarWarsSchema = GraphQLSchema(
    query=queryType,
    mutation=mutationType,
    subscription=subscriptionType,
    types=[humanType, droidType, reviewType, reviewInputType]
)
