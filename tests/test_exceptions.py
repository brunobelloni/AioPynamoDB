from botocore.exceptions import ClientError

from aiopynamodb.exceptions import PynamoDBException, PutError


def test_get_cause_response_code():
    error = PutError(
        cause=ClientError(
            error_response={
                'Error': {
                    'Code': 'hello'
                }
            },
            operation_name='test'
        )
    )
    assert error.cause_response_code == 'hello'


def test_get_cause_response_code__no_code():
    error = PutError()
    assert error.cause_response_code is None


def test_get_cause_response_message():
    error = PutError(
        cause=ClientError(
            error_response={
                'Error': {
                    'Message': 'hiya'
                }
            },
            operation_name='test'
        )
    )
    assert error.cause_response_message == 'hiya'


def test_get_cause_response_message__no_message():
    error = PutError()
    assert error.cause_response_message is None


class PynamoDBTestError(PynamoDBException):
    msg = "Test message"


def test_subclass_message_is_not_overwritten_with_none():
    assert PynamoDBTestError().msg == "Test message"
