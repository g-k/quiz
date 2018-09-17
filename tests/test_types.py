from textwrap import dedent

import pytest

import quiz
from quiz import SELECTOR as _
from quiz.build import SelectionSet, gql
from quiz.utils import FrozenDict as fdict

from .example import Command, Dog, Hobby, Human, Query


class TestUnion:

    def test_instancecheck(self):

        class MyUnion(quiz.Union):
            __args__ = (str, int)

        assert isinstance('foo', MyUnion)
        assert isinstance(5, MyUnion)
        assert not isinstance(1.3, MyUnion)


class TestOptional:

    def test_instancecheck(self):

        class MyOptional(quiz.Nullable):
            __arg__ = int

        assert isinstance(5, MyOptional)
        assert isinstance(None, MyOptional)
        assert not isinstance(5.4, MyOptional)


class TestList:

    def test_isinstancecheck(self):

        class MyList(quiz.List):
            __arg__ = int

        assert isinstance([1, 2], MyList)
        assert isinstance([], MyList)
        assert not isinstance(['foo'], MyList)
        assert not isinstance([3, 'bla'], MyList)
        assert not isinstance((1, 2), MyList)


class TestGenericScalar:

    def test_isinstancecheck(self):

        class MyScalar(quiz.GenericScalar):
            """foo"""

        assert isinstance(4, MyScalar)
        assert isinstance(u'foo', MyScalar)
        assert isinstance(0.1, MyScalar)
        assert isinstance(True, MyScalar)

        assert not isinstance([], MyScalar)
        assert not isinstance(None, MyScalar)


class TestObject:

    class TestGetItem:

        def test_valid(self):
            selection_set = (
                _
                .name
                .knows_command(command=Command.SIT)
                .is_housetrained
            )
            fragment = Dog[selection_set]
            assert fragment == quiz.InlineFragment(Dog, selection_set)

        def test_validates(self):
            with pytest.raises(quiz.SelectionError):
                Dog[_.name.foo.knows_command(command=Command.SIT)]


class TestInlineFragment:

    def test_gql(self):
        fragment = Dog[
            _
            .name
            .bark_volume
            .knows_command(command=Command.SIT)
            .is_housetrained
            .owner[
                _
                .name
            ]
        ]
        assert gql(fragment) == dedent('''\
        ... on Dog {
          name
          bark_volume
          knows_command(command: SIT)
          is_housetrained
          owner {
            name
          }
        }
        ''').strip()


class TestOperation:

    def test_graphql(self):
        operation = quiz.Operation(
            quiz.OperationType.QUERY,
            SelectionSet(
                quiz.Field('foo'),
                quiz.Field('qux', fdict({'buz': 99}), SelectionSet(
                    quiz.Field('nested'),
                ))
            )
        )
        assert gql(operation) == dedent('''
        query {
          foo
          qux(buz: 99) {
            nested
          }
        }
        ''').strip()


class TestValidate:

    def test_empty(self):
        selection = SelectionSet()
        assert quiz.validate(Dog, selection) == SelectionSet()

    def test_simple_valid(self):
        assert quiz.validate(Dog, _.name) == _.name

    def test_complex_valid(self):
        selection_set = (
            _
            .name
            .knows_command(command=Command.SIT)
            .is_housetrained
            .owner[
                _
                .name
                .hobbies[
                    _
                    .name
                    .cool_factor
                ]
            ]
            .best_friend[
                _
                .name
            ]
            .age(on_date='2018-09-17T08:52:13.956621')
        )
        assert quiz.validate(Dog, selection_set) == selection_set

    def test_no_such_field(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.name.foo.knows_command(command=Command.SIT))
        assert exc.value == quiz.SelectionError(
            Dog, 'foo', quiz.NoSuchField())

    def test_invalid_argument(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.knows_command(
                foo=1, command=Command.SIT))
        assert exc.value == quiz.SelectionError(
            Dog,
            'knows_command',
            quiz.NoSuchArgument('foo'))

    def test_missing_arguments(self):
        selection_set = _.knows_command
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, selection_set)

        assert exc.value == quiz.SelectionError(
            Dog,
            'knows_command',
            quiz.MissingArgument('command')
        )

    def test_invalid_argument_type(self):
        selection_set = _.knows_command(command='foobar')
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, selection_set)

        assert exc.value == quiz.SelectionError(
            Dog,
            'knows_command',
            quiz.InvalidArgumentType('command', 'foobar')
        )

    def test_invalid_argument_type_optional(self):
        selection_set = _.is_housetrained(at_other_homes='foo')
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, selection_set)
        assert exc.value == quiz.SelectionError(
            Dog,
            'is_housetrained',
            quiz.InvalidArgumentType('at_other_homes', 'foo')
        )

    def test_nested_selection_error(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.owner[_.hobbies[_.foo]])
        assert exc.value == quiz.SelectionError(
            Dog,
            'owner',
            quiz.SelectionError(
                Human,
                'hobbies',
                quiz.SelectionError(
                    Hobby,
                    'foo',
                    quiz.NoSuchField()
                )
            )
        )

    def test_selection_set_on_non_object(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.name[_.foo])
        assert exc.value == quiz.SelectionError(
            Dog,
            'name',
            quiz.SelectionsNotSupported()
        )

    # TODO: check object types always have selection sets

    # TODO: list input type


class TestQuery:

    def test_valid(self):
        selection_set = (
            _
            .dog[
                _
                .name
                .is_housetrained
            ]
        )
        query = quiz.query(selection_set, cls=Query)
        assert isinstance(query, quiz.Operation)
        assert query.type is quiz.OperationType.QUERY  # noqa
        assert len(query.selection_set) == 1

    def test_validates(self):
        with pytest.raises(quiz.SelectionError):
            quiz.query(
                _
                .dog[
                    _
                    .name
                    .is_housetrained
                    .foobar
                ],
                cls=Query,
            )


class TestFieldDefinition:

    def test_doc(self):
        schema = quiz.FieldDefinition(
            'foo', 'my description', type=quiz.List[str],
            args=fdict.EMPTY,
            is_deprecated=False, deprecation_reason=None)
        assert '[str]' in schema.__doc__


class TestRaw:

    def test_gql(self):
        raw = quiz.Raw('my raw graphql')
        assert gql(raw) == 'my raw graphql'
