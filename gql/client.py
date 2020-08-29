import asyncio
import warnings
from typing import Any, AsyncGenerator, Dict, Generator, Optional, Union

from graphql import (
    DocumentNode,
    ExecutionResult,
    GraphQLSchema,
    build_ast_schema,
    build_client_schema,
    get_introspection_query,
    parse,
    validate,
)

from .transport.async_transport import AsyncTransport
from .transport.exceptions import TransportQueryError
from .transport.local_schema import LocalSchemaTransport
from .transport.transport import Transport
from .type_adapter import TypeAdapter


class Client:
    def __init__(
        self,
        schema: Optional[Union[str, GraphQLSchema]] = None,
        introspection=None,
        type_def: Optional[str] = None,
        transport: Optional[Union[Transport, AsyncTransport]] = None,
        fetch_schema_from_transport: bool = False,
        execute_timeout: Optional[int] = 10,
        custom_types: Optional[Dict[str, Any]] = None,
    ):
        assert not (
            type_def and introspection
        ), "Cannot provide introspection and type definition at the same time."

        if type_def:
            assert (
                not schema
            ), "Cannot provide type definition and schema at the same time."
            warnings.warn(
                "type_def is deprecated; use schema instead",
                category=DeprecationWarning,
            )
            schema = type_def

        if introspection:
            assert (
                not schema
            ), "Cannot provide introspection and schema at the same time."
            schema = build_client_schema(introspection)

        if isinstance(schema, str):
            type_def_ast = parse(schema)
            schema = build_ast_schema(type_def_ast)

        if transport and fetch_schema_from_transport:
            assert (
                not schema
            ), "Cannot fetch the schema from transport if is already provided."

        if schema and not transport:
            transport = LocalSchemaTransport(schema)

        # GraphQL schema
        self.schema: Optional[GraphQLSchema] = schema

        # Answer of the introspection query
        self.introspection = introspection

        # GraphQL transport chosen
        self.transport: Optional[Union[Transport, AsyncTransport]] = transport

        # Flag to indicate that we need to fetch the schema from the transport
        # On async transports, we fetch the schema before executing the first query
        self.fetch_schema_from_transport: bool = fetch_schema_from_transport

        # Enforced timeout of the execute function
        self.execute_timeout = execute_timeout

        # Fetch schema from transport directly if we are using a sync transport
        if isinstance(transport, Transport) and fetch_schema_from_transport:
            with self as session:
                session.fetch_schema()

        # Dictionary where the name of the custom scalar type is the key and the
        # value is a class which has a `parse_value()` function
        self.custom_types = custom_types

        # Create a type_adapter instance directly here if we received the schema
        # locally or from a sync transport
        self.type_adapter = (
            TypeAdapter(schema, custom_types) if custom_types and schema else None
        )

    def validate(self, document):
        assert (
            self.schema
        ), "Cannot validate the document locally, you need to pass a schema."

        validation_errors = validate(self.schema, document)
        if validation_errors:
            raise validation_errors[0]

    def execute_sync(self, document: DocumentNode, *args, **kwargs) -> Dict:
        with self as session:
            return session.execute(document, *args, **kwargs)

    async def execute_async(self, document: DocumentNode, *args, **kwargs) -> Dict:
        async with self as session:
            return await session.execute(document, *args, **kwargs)

    def execute(self, document: DocumentNode, *args, **kwargs) -> Dict:
        """Execute the provided document AST against the configured remote server.

        This function WILL BLOCK until the result is received from the server.

        Either the transport is sync and we execute the query synchronously directly
        OR the transport is async and we execute the query in the asyncio loop
        (blocking here until answer).
        """

        if isinstance(self.transport, AsyncTransport):

            loop = asyncio.get_event_loop()

            assert not loop.is_running(), (
                "Cannot run client.execute(query) if an asyncio loop is running."
                " Use 'await client.execute_async(query)' instead."
            )

            data: Dict[Any, Any] = loop.run_until_complete(
                self.execute_async(document, *args, **kwargs)
            )

            return data

        else:  # Sync transports
            return self.execute_sync(document, *args, **kwargs)

    async def subscribe_async(
        self, document: DocumentNode, *args, **kwargs
    ) -> AsyncGenerator[Dict, None]:
        async with self as session:

            generator: AsyncGenerator[Dict, None] = session.subscribe(
                document, *args, **kwargs
            )

            async for result in generator:
                yield result

    def subscribe(
        self, document: DocumentNode, *args, **kwargs
    ) -> Generator[Dict, None, None]:
        """Execute a GraphQL subscription with a python generator.

        We need an async transport for this functionality.
        """

        async_generator = self.subscribe_async(document, *args, **kwargs)

        loop = asyncio.get_event_loop()

        assert not loop.is_running(), (
            "Cannot run client.subscribe(query) if an asyncio loop is running."
            " Use 'await client.subscribe_async(query)' instead."
        )

        try:
            while True:
                # Note: we need to create a task here in order to be able to close
                # the async generator properly on python 3.8
                # See https://bugs.python.org/issue38559
                generator_task = asyncio.ensure_future(async_generator.__anext__())
                result = loop.run_until_complete(generator_task)
                yield result

        except StopAsyncIteration:
            pass

        except (KeyboardInterrupt, Exception):

            # Graceful shutdown by cancelling the task and waiting clean shutdown
            generator_task.cancel()

            try:
                loop.run_until_complete(generator_task)
            except (StopAsyncIteration, asyncio.CancelledError):
                pass

            # Then reraise the exception
            raise

    async def __aenter__(self):

        assert isinstance(
            self.transport, AsyncTransport
        ), "Only a transport of type AsyncTransport can be used asynchronously"

        await self.transport.connect()

        if not hasattr(self, "session"):
            self.session = AsyncClientSession(client=self)

        return self.session

    async def __aexit__(self, exc_type, exc, tb):

        await self.transport.close()

    def __enter__(self):

        assert not isinstance(self.transport, AsyncTransport), (
            "Only a sync transport can be used."
            " Use 'async with Client(...) as session:' instead"
        )

        self.transport.connect()

        if not hasattr(self, "session"):
            self.session = SyncClientSession(client=self)

        return self.session

    def __exit__(self, *args):
        self.transport.close()


class SyncClientSession:
    """An instance of this class is created when using 'with' on the client.

    It contains the sync method execute to send queries
    with the sync transports.
    """

    def __init__(self, client: Client):
        self.client = client

    def _execute(self, document: DocumentNode, *args, **kwargs) -> ExecutionResult:

        # Validate document
        if self.client.schema:
            self.client.validate(document)

        return self.transport.execute(document, *args, **kwargs)

    def execute(self, document: DocumentNode, *args, **kwargs) -> Dict[str, Any]:

        # Validate and execute on the transport
        result = self._execute(document, *args, **kwargs)

        # Raise an error if an error is returned in the ExecutionResult object
        if result.errors:
            raise TransportQueryError(
                str(result.errors[0]), errors=result.errors, data=result.data
            )

        assert (
            result.data is not None
        ), "Transport returned an ExecutionResult without data or errors"

        if self.client.type_adapter:
            return self.client.type_adapter.convert_scalars(result.data)
        else:
            return result.data

    def fetch_schema(self) -> None:
        execution_result = self.transport.execute(parse(get_introspection_query()))
        self.client.introspection = execution_result.data
        self.client.schema = build_client_schema(self.client.introspection)

    @property
    def transport(self):
        return self.client.transport


class AsyncClientSession:
    """An instance of this class is created when using 'async with' on the client.

    It contains the async methods (execute, subscribe) to send queries
    with the async transports.
    """

    def __init__(self, client: Client):
        self.client = client

    async def fetch_and_validate(self, document: DocumentNode):
        """Fetch schema from transport if needed and validate document.

        If no schema is present, the validation will be skipped.
        """

        # Get schema from transport if needed
        if self.client.fetch_schema_from_transport and not self.client.schema:
            await self.fetch_schema()

            # Once we have received the schema from the async transport,
            # we can create a TypeAdapter instance if the user provided custom types
            if self.client.custom_types and self.client.schema:
                self.client.type_adapter = TypeAdapter(
                    self.client.schema, self.client.custom_types
                )

        # Validate document
        if self.client.schema:
            self.client.validate(document)

    async def _subscribe(
        self, document: DocumentNode, *args, **kwargs
    ) -> AsyncGenerator[ExecutionResult, None]:

        # Fetch schema from transport if needed and validate document if possible
        await self.fetch_and_validate(document)

        # Subscribe to the transport
        inner_generator: AsyncGenerator[
            ExecutionResult, None
        ] = self.transport.subscribe(document, *args, **kwargs)

        # Keep a reference to the inner generator to allow the user to call aclose()
        # before a break if python version is too old (pypy3 py 3.6.1)
        self._generator = inner_generator

        async for result in inner_generator:
            if result.errors:
                # Note: we need to run generator.aclose() here or the finally block in
                # transport.subscribe will not be reached in pypy3 (py 3.6.1)
                await inner_generator.aclose()

            yield result

    async def subscribe(
        self, document: DocumentNode, *args, **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:

        # Validate and subscribe on the transport
        async for result in self._subscribe(document, *args, **kwargs):

            # Raise an error if an error is returned in the ExecutionResult object
            if result.errors:
                raise TransportQueryError(
                    str(result.errors[0]), errors=result.errors, data=result.data
                )

            elif result.data is not None:
                if self.client.type_adapter:
                    yield self.client.type_adapter.convert_scalars(result.data)
                else:
                    yield result.data

    async def _execute(
        self, document: DocumentNode, *args, **kwargs
    ) -> ExecutionResult:

        # Fetch schema from transport if needed and validate document if possible
        await self.fetch_and_validate(document)

        # Execute the query with the transport with a timeout
        return await asyncio.wait_for(
            self.transport.execute(document, *args, **kwargs),
            self.client.execute_timeout,
        )

    async def execute(self, document: DocumentNode, *args, **kwargs) -> Dict[str, Any]:

        # Validate and execute on the transport
        result = await self._execute(document, *args, **kwargs)

        # Raise an error if an error is returned in the ExecutionResult object
        if result.errors:
            raise TransportQueryError(
                str(result.errors[0]), errors=result.errors, data=result.data
            )

        assert (
            result.data is not None
        ), "Transport returned an ExecutionResult without data or errors"

        if self.client.type_adapter:
            return self.client.type_adapter.convert_scalars(result.data)
        else:
            return result.data

    async def fetch_schema(self) -> None:
        execution_result = await self.transport.execute(
            parse(get_introspection_query())
        )
        self.client.introspection = execution_result.data
        self.client.schema = build_client_schema(self.client.introspection)

    @property
    def transport(self):
        return self.client.transport
