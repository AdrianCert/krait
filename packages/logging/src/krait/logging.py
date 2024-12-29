import logging
import queue
import threading
import typing
from pathlib import Path

from krait import package


class AsyncFileHandler(logging.Handler):
    """
    A logging handler that writes log records to a file asynchronously.

    Parameters
    ----------
    filename : str
        The path to the log file.
    """

    def __init__(self, filename):
        super().__init__()
        self.filename = Path(filename)
        self.queue = queue.Queue()
        self.worker_thread = None

    def emit(self, record):
        self.queue.put(record)
        self.start_worker()

    def format(self, record):
        if getattr(record, "raw", False):
            return record.getMessage()
        return super().format(record)

    def start_worker(self):
        if not self.worker_thread:
            self.worker_thread = threading.Thread(target=self._process_queue)
            self.worker_thread.start()

    def _process_queue(self):
        while True:
            try:
                record = self.queue.get(timeout=1)
            except Exception:
                if not self.queue.unfinished_tasks:
                    break
                continue
            try:
                with self.filename.open("a") as f:
                    f.write(self.format(record) + "\n")
            except Exception:
                self.handleError(record)
            finally:
                self.queue.task_done()
        self.worker_thread = None

    def close(self):
        self.start_worker()
        self.queue.join()  # Wait for all pending records to be processed
        self.worker_thread.join()
        super().close()


class QualModulePathFilter(logging.Filter):
    """
    A logging filter that adds a fully qualified module path to log records.

    Examples
    --------
    >>> import logging
    >>> from krait.logging import QualModulePathFilter
    >>> logger = logging.getLogger(__name__)
    >>> logger.addFilter(QualModulePathFilter())
    >>> logger.info("This is a test log message.")
    """

    def filter(self, record):
        qualname = package.path2qualname(record.pathname)
        record.qual_module = qualname or record.module
        return True


class SkipFlagFilter(logging.Filter):
    """
    A logging filter that skips log records based on a flag attribute.
    """

    def __init__(self, *args, flag_name: str = "skip_display", **kwargs):
        super().__init__(*args, **kwargs)
        self.flag_name = flag_name

    def filter(self, record):
        return not getattr(record, self.flag_name, False)


def configure_logging(
    log_location: typing.Optional[Path] = None,
    log_level=logging.DEBUG,
    task_name: str = None,
):
    """
    Configure the logging system with custom handlers and formatters.

    Parameters
    ----------
    log_location : typing.Optional[Path], optional
        The location where the log file will be saved. If not provided, the current working directory will be used.
    log_level : int, optional
        The logging level to be set for the logger. Default is `logging.DEBUG`.
    task_name : str, optional
        The name of the task to be included in the log messages. If not provided, no task name will be included.

    Returns
    -------
    None
    """
    logger = getLogger()
    from krait import path

    log_location = path.PathHelper.resolve_outfile(
        log_location or Path.cwd(),
        f"{logger.name}.logs",
    )

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = AsyncFileHandler(log_location)

    # Create formatters and add it to handlers
    format_prefix = f"[{task_name}]" if task_name else ""
    format_base = "[%(levelname)s][%(qual_module)s:%(funcName)s:%(lineno)d] %(message)s"

    f_format = logging.Formatter(
        "{prefix}[%(name)s][%(asctime)s]{base}".format(
            prefix=format_prefix,
            base=format_base,
        )
    )
    c_format = logging.Formatter(
        "{prefix}{base}".format(
            prefix=format_prefix,
            base=format_base,
        )
    )

    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add the custom filter to the handlers
    full_module_filter = QualModulePathFilter()
    skip_display_filter = SkipFlagFilter()
    c_handler.addFilter(skip_display_filter)
    c_handler.addFilter(full_module_filter)
    f_handler.addFilter(full_module_filter)

    # Set the log level
    logger.setLevel(log_level)

    # Add handlers to the logger
    logger.handlers.clear()
    logger.addHandler(c_handler)
    if not task_name:
        logger.addHandler(f_handler)


class ReflexiveLogger:
    @staticmethod
    def get_logger(relative_frame=1):
        """
        Create an instance of the class based on the caller's file location.

        Parameters
        ----------
        relative_frame : int, optional
            The stack frame index to inspect. Default is 1, which refers to the caller's frame.

        Returns
        -------
        cls or None
            An instance of the class if the caller's file is mapped to a package, otherwise None.
        """
        try:
            pkg: package.PackageInfo = package.this(relative_frame=relative_frame + 1)
            logger_name = pkg.dist_name
        except Exception:
            logger_name = ""

        return logging.getLogger(logger_name)


TRACE = 5
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
NOTICE = 60
VERBOSITY_LEVELS = {
    0: WARNING,
    1: INFO,
    2: DEBUG,
    3: TRACE,
}


def set_verbose_level(logger: logging.Logger, level: int):
    logger.setLevel(VERBOSITY_LEVELS[min(max(level, 0), 3)])


def impl_notice(self, message, *args, stacklevel=1, **kwargs):
    if self.isEnabledFor(NOTICE):
        self._log(NOTICE, message, args, stacklevel=stacklevel + 1, **kwargs)


def impl_trace(self, message, *args, stacklevel=1, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, stacklevel=stacklevel + 1, **kwargs)


logging.Logger.notice = impl_notice
logging.Logger.trace = impl_trace
logging.addLevelName(NOTICE, "NOTICE")
logging.addLevelName(TRACE, "TRACE")


def getLogger(name: str = None, /, relative_frame=1):  # noqa: N802
    if name is not None:
        return logging.getLogger(name)
    return ReflexiveLogger.get_logger(relative_frame=relative_frame + 1)


def _log(level, message, *args, **kwargs):
    getLogger().log(level, message, *args, **kwargs)


def trace(message, *args, **kwargs):
    getLogger().trace(message, *args, **kwargs)


def info(message, *args, **kwargs):
    getLogger().info(message, *args, **kwargs)


def debug(message, *args, **kwargs):
    getLogger().debug(message, *args, **kwargs)


def warning(message, *args, **kwargs):
    getLogger().warning(message, *args, **kwargs)


def error(message, *args, **kwargs):
    getLogger().error(message, *args, **kwargs)


def exception(message, *args, **kwargs):
    getLogger().exception(message, *args, **kwargs)


def critical(message, *args, **kwargs):
    getLogger().critical(message, *args, **kwargs)


def notice(message, *args, **kwargs):
    getLogger().notice(message, *args, **kwargs)


if typing.TYPE_CHECKING:
    trace = logging.trace  # noqa: F811
    info = logging.info  # noqa: F811
    debug = logging.debug  # noqa: F811
    warning = logging.warning  # noqa: F811
    error = logging.error  # noqa: F811
    exception = logging.exception  # noqa: F811
    critical = logging.critical  # noqa: F811
    notice = logging.notice  # noqa: F811
