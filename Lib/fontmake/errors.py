class FontmakeError(Exception):
    """Base class for all fontmake exceptions."""

    pass


class TTFAError(FontmakeError):
    def __init__(self, exitcode):
        self.exitcode = exitcode

    def __str__(self):
        return "ttfautohint command failed: error " + str(self.exitcode)
