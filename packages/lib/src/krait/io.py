import contextlib
import io
import re


class ObservableBuffer(io.StringIO):
    """
    The Stream buffer intercept writes and provides hooks for callbacks, redirection to other buffers, and data collection.

    The `ObservableBuffer` acts as a proxy for stream-like objects, allowing users
    to attach custom behavior when data is written to the buffer. It supports
    redirection of data to other buffers, invoking user-defined callbacks, and
    optional collection of written data for later inspection.

    Parameters
    ----------
    skip_ansi : bool, optional
        Whether to skip ANSI escape sequences for colored text. Defaults to False.
    buffers : list, optional
        A list of buffer objects to which the data will also be written. Defaults to None.

    Examples
    --------
    >>> import sys
    >>> from krait.io import StreamCollector
    >>> sys.stdout = buffer = StreamCollector(skip_ansi=True)
    >>> print("Hello, World!")
    >>> with open("output.txt", "w") as file:
    >>>     file.write(buffer.getvalue())
    """

    ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

    def __init__(
        self,
        *args,
        buffers=None,
        skip_ansi=False,
        callbacks=None,
        collect: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.buffers = buffers or []
        self.skip_ansi = skip_ansi
        self.callbacks = callbacks or []
        self.collect = collect

    def write(self, data):
        """
        Write the data to the output stream.

        Args:
            data (str): The data to be written.
        """
        for buffer in self.buffers:
            buffer.write(data)
        for callback in self.callbacks:
            with contextlib.suppress(Exception):
                callback(data)
        if self.skip_ansi:
            # remove ANSI escape sequences for colored text
            data = self.ansi_escape.sub("", data)
        # \r\n is replaced with \n to avoid double line breaks
        data = data.replace("\r\n", "\n")
        if self.collect:
            super().write(data)

    def flush(self):
        """Flushes the output stream."""
        for buffer in self.buffers:
            buffer.flush()
        super().flush()
