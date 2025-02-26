from msgspec import json

from ._base import TranscoderBase

__all__ = ["JSONTranscoder"]


from krait import signal


class JSONTranscoder(TranscoderBase):
    mimetype = "application/json"
    decode_kwargs = signal.signal(
        {},
    )
    encode_kwargs = signal.signal({})

    def __init__(self, *args, **kwargs):
        super().__init__()
        # self.decoder =
        # self.encoder = json.Encoder

    @signal.signal
    def _decoder(self) -> json.Decoder:
        return json.Decoder(self.decode_kwargs)

    @signal.signal
    def _encoder(self) -> json.Encoder:
        return json.Encoder(self.encode_kwargs)

    def decode(self, data, **kwargs):
        self.decode_kwargs = kwargs
        return self._decoder.decode(data)

    def encode(self, obj, **kwargs):
        return self._encoder.encode(obj)

    def encode_into(self, obj, buffer, **kwargs):
        return self._encoder.encode_into(obj, buffer)
