"""
A PynamoDB example using a custom attribute
"""
import asyncio
import pickle
from typing import Any

from aiopynamodb.attributes import Attribute
from aiopynamodb.attributes import UnicodeAttribute
from aiopynamodb.constants import BINARY
from aiopynamodb.models import Model


class Color(object):
    """
    This class is used to demonstrate the PickleAttribute below
    """

    def __init__(self, name: str) -> None:
        self.name = name


class PickleAttribute(Attribute[object]):
    """
    This class will serializer/deserialize any picklable Python object.
    The value will be stored as a binary attribute in DynamoDB.
    """
    attr_type = BINARY

    def serialize(self, value: Any) -> bytes:
        return pickle.dumps(value)

    def deserialize(self, value: Any) -> Any:
        return pickle.loads(value)


class CustomAttributeModel(Model):
    """
    A model with a custom attribute
    """

    class Meta:
        host = 'http://localhost:8000'
        table_name = 'custom_attr'
        read_capacity_units = 1
        write_capacity_units = 1

    id = UnicodeAttribute(hash_key=True)
    obj = PickleAttribute()


async def main():
    # Create the example table
    if not await CustomAttributeModel.exists():
        await CustomAttributeModel.create_table(wait=True)

    instance = CustomAttributeModel()
    instance.obj = Color('red')
    instance.id = 'red'
    await instance.save()
    print('instance', instance)

    instance = await CustomAttributeModel.get('red')
    print('instance', instance)
    print('instance.obj', instance.obj)


if __name__ == '__main__':
    asyncio.run(main())
