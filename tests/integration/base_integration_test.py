"""
Runs tests against dynamodb
"""
import time

from aiopynamodb.connection import Connection
from aiopynamodb.constants import PROVISIONED_THROUGHPUT, READ_CAPACITY_UNITS
from aiopynamodb.expressions.condition import BeginsWith, NotExists
from aiopynamodb.expressions.operand import Path, Value
from aiopynamodb.exceptions import TableDoesNotExist
from aiopynamodb.types import STRING, HASH, RANGE, NUMBER

import pytest


@pytest.mark.ddblocal
@pytest.mark.asyncio
async def test_connection_integration(ddb_url):
    table_name = 'pynamodb-ci-connection'

    # For use with a fake dynamodb connection
    # See: http://aws.amazon.com/dynamodb/developer-resources/
    conn = Connection(host=ddb_url)

    print(conn)
    print("conn.describe_table...")
    table = None
    try:
        table = await conn.describe_table(table_name)
    except TableDoesNotExist:
        params = {
            'read_capacity_units': 1,
            'write_capacity_units': 1,
            'attribute_definitions': [
                {
                    'attribute_type': STRING,
                    'attribute_name': 'Forum'
                },
                {
                    'attribute_type': STRING,
                    'attribute_name': 'Thread'
                },
                {
                    'attribute_type': STRING,
                    'attribute_name': 'AltKey'
                },
                {
                    'attribute_type': NUMBER,
                    'attribute_name': 'number'
                }
            ],
            'key_schema': [
                {
                    'key_type': HASH,
                    'attribute_name': 'Forum'
                },
                {
                    'key_type': RANGE,
                    'attribute_name': 'Thread'
                }
            ],
            'global_secondary_indexes': [
                {
                    'index_name': 'alt-index',
                    'key_schema': [
                        {
                            'KeyType': 'HASH',
                            'AttributeName': 'AltKey'
                        }
                    ],
                    'projection': {
                        'ProjectionType': 'KEYS_ONLY'
                    },
                    'provisioned_throughput': {
                        'ReadCapacityUnits': 1,
                        'WriteCapacityUnits': 1,
                    }
                }
            ],
            'local_secondary_indexes': [
                {
                    'index_name': 'view-index',
                    'key_schema': [
                        {
                            'KeyType': 'HASH',
                            'AttributeName': 'Forum'
                        },
                        {
                            'KeyType': 'RANGE',
                            'AttributeName': 'AltKey'
                        }
                    ],
                    'projection': {
                        'ProjectionType': 'KEYS_ONLY'
                    }
                }
            ]
        }
        print("conn.create_table...")
        await conn.create_table(table_name, **params)

    while table is None:
        time.sleep(1)
        table = await conn.describe_table(table_name)

    while table['TableStatus'] == 'CREATING':
        time.sleep(2)
        table = await conn.describe_table(table_name)
    print("conn.list_tables")
    await conn.list_tables()
    print("conn.update_table...")

    await conn.update_table(
        table_name,
        read_capacity_units=table.get(PROVISIONED_THROUGHPUT).get(READ_CAPACITY_UNITS) + 1,
        write_capacity_units=2
    )

    table = await conn.describe_table(table_name)

    while table['TableStatus'] != 'ACTIVE':
        time.sleep(2)
        table = await conn.describe_table(table_name)

    print("conn.put_item")
    await conn.put_item(
        table_name,
        'item1-hash',
        range_key='item1-range',
        attributes={'foo': {'S': 'bar'}},
        condition=NotExists(Path('Forum')),
    )
    await conn.get_item(
        table_name,
        'item1-hash',
        range_key='item1-range'
    )
    await conn.delete_item(
        table_name,
        'item1-hash',
        range_key='item1-range'
    )

    items = []
    for i in range(10):
        items.append(
            {"Forum": "FooForum", "Thread": "thread-{}".format(i)}
        )
    print("conn.batch_write_items...")
    await conn.batch_write_item(
        table_name,
        put_items=items
    )
    print("conn.batch_get_items...")
    data = await conn.batch_get_item(
        table_name,
        items
    )
    print("conn.query...")
    await conn.query(
        table_name,
        "FooForum",
        range_key_condition=(BeginsWith(Path('Thread'), Value('thread'))),
    )
    print("conn.scan...")
    await conn.scan(
        table_name,
    )
    print("conn.delete_table...")
    await conn.delete_table(table_name)
