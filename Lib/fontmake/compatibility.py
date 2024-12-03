from __future__ import annotations

import logging

from ufoLib2 import Font
from ufoLib2.objects import Layer
from fontTools.designspaceLib import DesignSpaceDocument

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
    def __init__(self, designspace: DesignSpaceDocument):
        self.errors = []
        self.context = []
        self.okay = True

        self.fonts: list[Font] = [source.font for source in designspace.sources]
        self.layers: list[tuple[Font, Layer]] = [
            (
                source.font,
                source.font.layers.defaultLayer
                if source.layerName is None
                else source.font.layers[source.layerName],
            )
            for source in designspace.sources
        ]

    def check(self) -> bool:
        first = self.fonts[0]
        skip_export_glyphs = set(first.lib.get("public.skipExportGlyphs", ()))
        for glyph in first.keys():
            if glyph in skip_export_glyphs:
                continue
            self.current_layers = [
                (font, layer) for (font, layer) in self.layers if glyph in layer
            ]
            glyphs = [layer[glyph] for (_, layer) in self.current_layers]
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
        # Context for contextual anchors
        libs = [g.lib for g in glyphs]
        for each_anchors in zip(*anchors):
            if each_anchors[0].name[0] == "*":
                objectlibs = [
                    libs[font_ix]
                    .get("public.objectLibs", {})
                    .get(anchor.identifier, {})
                    for font_ix, anchor in enumerate(each_anchors)
                ]
                with Context(self, f"anchor {each_anchors[0].name}"):
                    self.ensure_all_same(
                        lambda lib: lib.get("GPOS_Context", "None").strip(),
                        objectlibs,
                        "GPOS context",
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

    def ensure_all_same(self, func, objs, what) -> bool:
        values = {}
        context = ", ".join(self.context)
        for obj, (font, layer) in zip(objs, self.current_layers):
            values.setdefault(func(obj), []).append(self._name_for(font, layer))
        if len(values) < 2:
            logger.debug(f"All sources had same {what} in {context}")
            return True
        report = f"\nSources had differing {what} in {context}:\n"
        debug_enabled = logger.isEnabledFor(logging.DEBUG)
        for value, source_names in values.items():
            if debug_enabled or len(source_names) <= 6:
                key = ", ".join(source_names)
            else:
                key = f"{len(source_names)} sources"
            if len(str(value)) > 20:
                value = "\n    " + str(value)
            report += f" * {key} had: {value}\n"
        logger.error(report)
        self.okay = False
        return False

    def _name_for(self, font: Font, layer: Layer) -> str:
        names: list[str] = [
            name
            for name in (font.info.familyName, font.info.styleName, layer.name)
            if name is not None and name != "public.default"
        ]
        return " ".join(names)
