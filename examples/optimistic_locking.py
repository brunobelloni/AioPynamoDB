import asyncio
from uuid import uuid4

from botocore.client import ClientError

from aiopynamodb.attributes import ListAttribute, MapAttribute, UnicodeAttribute, VersionAttribute
from aiopynamodb.connection import Connection
from aiopynamodb.exceptions import PutError, UpdateError, TransactWriteError, DeleteError, DoesNotExist
from aiopynamodb.models import Model
from aiopynamodb.transactions import TransactWrite


class OfficeEmployeeMap(MapAttribute):
    office_employee_id = UnicodeAttribute()
    person = UnicodeAttribute()

    def __eq__(self, other):
        return isinstance(other, OfficeEmployeeMap) and self.person == other.person


class Office(Model):
    class Meta:
        read_capacity_units = 1
        write_capacity_units = 1
        table_name = 'Office'
        host = "http://localhost:8000"

    office_id = UnicodeAttribute(hash_key=True)
    employees = ListAttribute(of=OfficeEmployeeMap)
    name = UnicodeAttribute()
    version = VersionAttribute()


from contextlib import asynccontextmanager


@asynccontextmanager
async def assert_condition_check_fails():
    try:
        yield
    except (PutError, UpdateError, DeleteError) as e:
        assert isinstance(e.cause, ClientError)
        assert e.cause_response_code == "ConditionalCheckFailedException"
    except TransactWriteError as e:
        assert isinstance(e.cause, ClientError)
        assert e.cause_response_code == "TransactionCanceledException"
        assert e.cause_response_message is not None
        assert "ConditionalCheckFailed" in e.cause_response_message
    else:
        raise AssertionError("The version attribute conditional check should have failed.")


async def main():
    if not await Office.exists():
        await Office.create_table(wait=True)

    justin = OfficeEmployeeMap(office_employee_id=str(uuid4()), person='justin')
    garrett = OfficeEmployeeMap(office_employee_id=str(uuid4()), person='garrett')
    office = Office(office_id=str(uuid4()), name="office 3", employees=[justin, garrett])
    await office.save()
    assert office.version == 1

    # Get a second local copy of Office
    office_out_of_date = await Office.get(office.office_id)
    # Add another employee and save the changes.
    office.employees.append(OfficeEmployeeMap(office_employee_id=str(uuid4()), person='lita'))
    await office.save()
    # After a successful save or update operation the version is set or incremented locally so there's no need to refresh
    # between operations using the same local copy.
    assert office.version == 2
    assert office_out_of_date.version == 1

    # Condition check fails for update.
    async with assert_condition_check_fails():
        await office_out_of_date.update(actions=[Office.name.set('new office name')])

    # Condition check fails for save.
    office_out_of_date.employees.remove(garrett)
    async with assert_condition_check_fails():
        await office_out_of_date.save()

    # After refreshing the local copy the operation will succeed.
    await office_out_of_date.refresh()
    office_out_of_date.employees.remove(garrett)
    await office_out_of_date.save()
    assert office_out_of_date.version == 3

    # Condition check fails for delete.
    async with assert_condition_check_fails():
        await office.delete()

    # Example failed transactions.
    connection = Connection(host='http://localhost:8000')

    async with assert_condition_check_fails(), TransactWrite(connection=connection) as transaction:
        transaction.save(Office(office.office_id, name='newer name', employees=[]))

    async with assert_condition_check_fails(), TransactWrite(connection=connection) as transaction:
        transaction.update(
            Office(office.office_id, name='newer name', employees=[]),
            actions=[
                Office.name.set('Newer Office Name'),
            ]
        )

    async with assert_condition_check_fails(), TransactWrite(connection=connection) as transaction:
        transaction.delete(Office(office.office_id, name='newer name', employees=[]))

    # Example successful transaction.
    office2 = Office(office_id=str(uuid4()), name="second office", employees=[justin])
    await office2.save()
    assert office2.version == 1
    office3 = Office(office_id=str(uuid4()), name="third office", employees=[garrett])
    await office3.save()
    assert office3.version == 1

    async with TransactWrite(connection=connection) as transaction:
        transaction.condition_check(Office, office.office_id, condition=(Office.name.exists()))
        transaction.delete(office2)
        transaction.save(Office(office_id=str(uuid4()), name="new office", employees=[justin, garrett]))
        transaction.update(
            office3,
            actions=[
                Office.name.set('birdistheword'),
            ]
        )

    try:
        await office2.refresh()
    except DoesNotExist:
        pass
    else:
        raise AssertionError(
            "This item should have been deleted, but no DoesNotExist "
            "exception was raised when attempting to refresh a local copy."
        )

    assert office.version == 2
    # The version attribute of items which are saved or updated in a transaction are updated automatically to match the
    # persisted value.
    assert office3.version == 2
    await office.refresh()
    assert office.version == 3


if __name__ == '__main__':
    asyncio.run(main())
