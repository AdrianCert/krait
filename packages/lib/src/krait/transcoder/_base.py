import abc
import typing


class TranscoderBase:
    @abc.abstractmethod
    def encode(self, text: str) -> str:
        """Encode a string."""
        raise NotImplementedError

    @abc.abstractmethod
    def decode(self, text: str) -> str:
        """Decode a string."""
        raise NotImplementedError

    @abc.abstractmethod
    def encode_into(self, data: typing.Any, buffer: bytearray) -> None:
        """Encode a string into a buffer."""
        raise NotImplementedError
