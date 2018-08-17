import json
import sys

import pytest
import snug

import quiz

_ = quiz.selector

py3 = pytest.mark.skipif(sys.version_info < (3, ), reason='python 3+ only')


class MockClient:

    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


snug.send.register(MockClient, MockClient.send)


def token_auth(token):
    return snug.header_adder({'Authorization': 'token {}'.format(token)})


class TestExecute:

    def test_success(self):
        client = MockClient(snug.Response(200, b'{"data": {"foo": 4}}'))
        result = quiz.execute('my query', url='https://my.url/api',
                              client=client, auth=token_auth('foo'))
        assert result == {'foo': 4}

        request = client.request
        assert request.url == 'https://my.url/api'
        assert request.method == 'POST'
        assert json.loads(request.content) == {'query': 'my query'}
        assert request.headers == {'Authorization': 'token foo',
                                   'Content-Type': 'application/json'}

    def test_selection_set(self):
        client = MockClient(snug.Response(200, b'{"data": {"foo": 4}}'))
        result = quiz.execute(_.foo, url='https://my.url/api', client=client)
        assert result == {'foo': 4}

        request = client.request
        assert request.url == 'https://my.url/api'
        assert request.method == 'POST'
        assert json.loads(request.content) == {'query': quiz.gql(_.foo)}
        assert request.headers == {'Content-Type': 'application/json'}

    def test_errors(self):
        client = MockClient(snug.Response(200, json.dumps({
            'data': {'foo': 4},
            'errors': [{'message': 'foo'}]
        })))
        with pytest.raises(quiz.ErrorResponse) as exc:
            quiz.execute('my query', url='https://my.url/api',
                         client=client, auth=token_auth('foo'))
        assert exc.value == quiz.ErrorResponse({'foo': 4},
                                               [{'message': 'foo'}])


def test_executor():
    executor = quiz.executor(url='https://my.url/graphql')
    assert executor.keywords['url'] == 'https://my.url/graphql'