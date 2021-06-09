# GQL

This is a GraphQL client for Python 3.6+.
Plays nicely with `graphene`, `graphql-core`, `graphql-js` and any other GraphQL implementation compatible with the spec.

GQL architecture is inspired by `React-Relay` and `Apollo-Client`.

> **WARNING**: Please note that the following documentation describes the current version which is currently only available as a pre-release
> The documentation for the 2.x version compatible with python<3.6 is available in the [2.x branch](https://github.com/graphql-python/gql/tree/v2.x)

[![GitHub-Actions][gh-image]][gh-url]
[![pyversion][pyversion-image]][pyversion-url]
[![pypi][pypi-image]][pypi-url]
[![Anaconda-Server Badge][conda-image]][conda-url]
[![codecov][codecov-image]][codecov-url]

[gh-image]: https://github.com/graphql-python/gql/workflows/Tests/badge.svg
[gh-url]: https://github.com/graphql-python/gql/actions?query=workflow%3ATests
[pyversion-image]: https://img.shields.io/pypi/pyversions/gql
[pyversion-url]: https://pypi.org/project/gql/
[pypi-image]: https://img.shields.io/pypi/v/gql.svg?style=flat
[pypi-url]: https://pypi.org/project/gql/
[conda-image]: https://img.shields.io/conda/vn/conda-forge/gql.svg
[conda-url]: https://anaconda.org/conda-forge/gql
[codecov-image]: https://codecov.io/gh/graphql-python/gql/branch/master/graph/badge.svg
[codecov-url]: https://codecov.io/gh/graphql-python/gql

## Documentation

The complete documentation for GQL can be found at
[gql.readthedocs.io](https://gql.readthedocs.io).

## Features

The main features of GQL are:

* Execute GraphQL queries using [different protocols](https://gql.readthedocs.io/en/latest/transports/index.html) (http, websockets, ...)
* Possibility to [validate the queries locally](https://gql.readthedocs.io/en/latest/usage/validation.html) using a GraphQL schema provided locally or fetched from the backend using an instrospection query
* Supports GraphQL queries, mutations and [subscriptions](https://gql.readthedocs.io/en/latest/usage/subscriptions.html)
* Supports [sync or async usage](https://gql.readthedocs.io/en/latest/async/index.html), [allowing concurrent requests](https://gql.readthedocs.io/en/latest/advanced/async_advanced_usage.html#async-advanced-usage)
* Supports [File uploads](https://gql.readthedocs.io/en/latest/usage/file_upload.html)
* [gql-cli script](https://gql.readthedocs.io/en/latest/gql-cli/intro.html) to execute GraphQL queries from the command line
* [DSL module](https://gql.readthedocs.io/en/latest/advanced/dsl_module.html) to compose GraphQL queries dynamically
* [Compiler](https://gql.readthedocs.io/en/latest/advanced/compiler.html) to compile query files to strongly typed classes

## Installation

> **WARNING**: Please note that the following documentation describes the current version which is currently only available as a pre-release and needs to be installed with

    $ pip install --pre gql[all]

> **NOTE**: See also [the documentation](https://gql.readthedocs.io/en/latest/intro.html#less-dependencies) to install GQL with less extra dependencies

## Usage

### Basic usage

```python
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

# Select your transport with a defined url endpoint
transport = AIOHTTPTransport(url="https://countries.trevorblades.com/")

# Create a GraphQL client using the defined transport
client = Client(transport=transport, fetch_schema_from_transport=True)

# Provide a GraphQL query
query = gql(
    """
    query getContinents {
      continents {
        code
        name
      }
    }
"""
)

# Execute the query on the transport
result = client.execute(query)
print(result)
```

> **WARNING**: Please note that this basic example won't work if you have an asyncio event loop running. In some
> python environments (as with Jupyter which uses IPython) an asyncio event loop is created for you. In that case you
> should use instead the [async usage example](https://gql.readthedocs.io/en/latest/async/async_usage.html#async-usage).

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

[MIT License](https://github.com/graphql-python/gql/blob/master/LICENSE)
