from gql import gql, AsyncClient
from gql.transport.websockets import WebsocketsTransport
import asyncio
import argparse

parser = argparse.ArgumentParser(description='Send GraphQL queries from command line to a websocket endpoint')
parser.add_argument('server', help='the server websocket url starting with ws:// or wss://')
args = parser.parse_args()

async def main():
    
    transport = WebsocketsTransport(url=args.server, ssl=args.server.startswith('wss'))

    async with AsyncClient(transport=transport) as client:

        while True:
            try:
                query_str = input()
            except EOFError:
                break

            query = gql(query_str)

            async for result in client.subscribe(query):

                print (result.data)

asyncio.run(main())