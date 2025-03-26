import typing


class CallableParams(typing.NamedTuple):
    args: typing.Tuple
    kwargs: typing.Dict[str, typing.Any]
