import os


def _try_relative_path(path):
    # Try to return 'path' relative to the current working directory, or
    # return input 'path' if we can't make a relative path.
    # E.g. on Windows, os.path.relpath fails when path and "." are on
    # different mount points, C: or D: etc.
    try:
        return os.path.relpath(path)
    except ValueError:
        return path


class FontmakeError(Exception):
    """Base class for all fontmake exceptions.

    This exception is intended to be chained to the original exception. The
    main purpose is to provide a source file trail that points to where the
    explosion came from.
    """

    def __init__(self, msg, source_file):
        self.msg = msg
        self.source_trail = [source_file]

    def __str__(self):
        trail = " -> ".join(
            f"'{str(_try_relative_path(s))}'"
            for s in reversed(self.source_trail)
            if s is not None
        )
        cause = str(self.__cause__) if self.__cause__ is not None else None

        message = ""
        if trail:
            message = f"In {trail}: "
        message += f"{self.msg}"
        if cause:
            message += f": {cause}"

        return message


class TTFAError(FontmakeError):
    def __init__(self, exitcode, source_file):
        self.exitcode = exitcode
        self.source_trail = source_file

    def __str__(self):
        return (
            f"ttfautohint failed for '{str(_try_relative_path(self.source_trail))}': "
            f"error code {str(self.exitcode)}."
        )
