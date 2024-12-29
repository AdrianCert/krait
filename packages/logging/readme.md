# krait-logging

Logging Utilities for Python

---

This package provides advanced logging utilities for Python, including asynchronous file logging, custom filters, and enhanced logging levels. It is designed to support complex logging requirements in modular and distributed applications.

## Features

1. **Asynchronous File Logging**: Efficiently writes log records to a file in a separate thread.
2. **Custom Logging Filters**: 
   - Add fully qualified module paths to log records.
   - Skip specific log records based on flags.
3. **Enhanced Logging Levels**: Supports additional levels like `TRACE` and `NOTICE`.
4. **Dynamic Logger Configuration**: Easily configure loggers for different tasks with custom handlers and formatters.
5. **Reflexive Logger**: Automatically creates loggers based on the caller's context.

## Installation

Install the required dependencies:

```sh
pip install krait-logging
```

## Usage

### 1. Asynchronous File Logging

Use the `AsyncFileHandler` for non-blocking logging to files:

```py
from krait import logging

logger = logging.getLogger()
handler = logging.AsyncFileHandler("logs/example.log")
logger.addHandler(handler)
logger.info("This is an asynchronous log message.")
```

### 2. Custom Filters

#### Add Fully Qualified Module Path

The `QualModulePathFilter` appends the fully qualified module name to log records:

```py
from krait import logging

logger = logging.getLogger()
logger.addFilter(logging.QualModulePathFilter())
logger.info("Log message with module path.")
```

#### Skip Log Records

The `SkipFlagFilter` skips log messages based on a flag:

```py
from krait import logging

logger = logging.getLogger()
logger.addFilter(logging.SkipFlagFilter(flag_name="skip_display"))
logger.info("This log will not be print on screen but on file", extra={"skip_display": True})
```

### 3. Configure Logging

Simplify logger setup with `configure_logging`:

```py
from pathlib import Path
from krait.logging import configure_logging

configure_logging(
    log_location=Path("logs/my_app.log"),
    log_level="DEBUG",
    task_name="MyTask"
)

```

### 4. Reflexive Logger

Automatically get a logger based on the caller's context:

```py
from your_module.logging import getLogger

logger = getLogger()
logger.info("Message from reflexive logger.")
```

### 5. Enhanced Logging Levels

Use custom levels like `TRACE` and `NOTICE` for more granularity:

```from krait import logging

logging.notice("This is a notice log message.")
logging.trace("This is a trace log message.")
```

## Contributing

Feel free to open issues or contribute enhancements to this project. Fork the repository and create a pull request with your changes.

## License

This project is licensed under the MIT License.
