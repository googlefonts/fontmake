import logging

logger = logging.getLogger(__name__)


class Context:
    def __init__(self, checker, newcontext):
        self.checker = checker
        self.newcontext = newcontext

    def __enter__(self):
        self.checker.context.append(self.newcontext)

    def __exit__(self, type, value, traceback):
        self.checker.context.pop()


class CompatibilityChecker:
    def __init__(self, fonts):
        self.errors = []
        self.context = []
        self.okay = True
        self.fonts = fonts

    def check(self):
        first = self.fonts[0]
        skip_export_glyphs = set(first.lib.get("public.skipExportGlyphs", ()))
        for glyph in first.keys():
            if glyph in skip_export_glyphs:
                continue
            self.current_fonts = [font for font in self.fonts if glyph in font]
            glyphs = [font[glyph] for font in self.current_fonts]
            with Context(self, f"glyph {glyph}"):
                self.check_glyph(glyphs)
        return self.okay

    def check_glyph(self, glyphs):
        if self.ensure_all_same(len, glyphs, "number of contours"):
            for ix, contours in enumerate(zip(*glyphs)):
                with Context(self, f"contour {ix}"):
                    self.check_contours(contours)

        anchors = [g.anchors for g in glyphs]
        self.ensure_all_same(
            lambda anchors: '"' + (", ".join(sorted(a.name for a in anchors))) + '"',
            anchors,
            "anchors",
        )

        components = [g.components for g in glyphs]
        if self.ensure_all_same(len, components, "number of components"):
            for ix, component in enumerate(zip(*components)):
                with Context(self, f"component {ix}"):
                    self.ensure_all_same(lambda c: c.baseGlyph, component, "base glyph")

    def check_contours(self, contours):
        if not self.ensure_all_same(len, contours, "number of points"):
            return
        for ix, point in enumerate(zip(*contours)):
            with Context(self, f"point {ix}"):
                self.ensure_all_same(lambda x: x.type, point, "point type")

    def ensure_all_same(self, func, objs, what):
        values = {}
        context = ", ".join(self.context)
        for obj, font in zip(objs, self.current_fonts):
            values.setdefault(func(obj), []).append(self._name_for(font))
        if len(values) < 2:
            logger.debug(f"All fonts had same {what} in {context}")
            return True
        logger.error(f"Fonts had differing {what} in {context}:")
        debug_enabled = logger.isEnabledFor(logging.DEBUG)
        for value, fonts in values.items():
            if debug_enabled or len(fonts) <= 6:
                key = ", ".join(fonts)
            else:
                key = f"{len(fonts)} fonts"
            logger.error(f" * {key} had {value}")
        self.okay = False
        return False

    def _name_for(self, font):
        names = list(filter(None, [font.info.familyName, font.info.styleName]))
        return " ".join(names)
