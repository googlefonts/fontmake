# This code is based on ufoProcessor code, which is licensed as follows:
# Copyright (c) 2017-2018 LettError and Erik van Blokland
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Module for generating static font instances.

It is an alternative to mutatorMath (used internally by fontmake) and ufoProcessor. The
aim is to be a minimal implementation that is focussed on using ufoLib2 for font data
abstraction, varLib for instance computation and fontMath as a font data shell for
instance computation directly and exclusively.

At the time of this writing, varLib lacks support for anisotropic (x, y) locations and
extrapolation.
"""

import copy
import logging
import typing
from typing import Any, Dict, List, Mapping, Set, Tuple, Union

import attr
import fontMath
import fontTools.designspaceLib as designspaceLib
import fontTools.misc.fixedTools
import fontTools.varLib as varLib
import ufoLib2

logger = logging.getLogger(__name__)

# Use the same rounding function used by varLib to round things for the variable font
# to reduce differences between the variable and static instances.
fontMath.mathFunctions.setRoundIntegerFunction(fontTools.misc.fixedTools.otRound)

# Stand-in type for any of the fontMath classes we use.
FontMathObject = Union[fontMath.MathGlyph, fontMath.MathInfo, fontMath.MathKerning]

# MutatorMath-style location mapping type, i.e.
# `{"wght": 1.0, "wdth": 0.0, "bleep": 0.5}`.
# LocationKey is a Location turned into a tuple so we can use it as a dict key.
Location = Mapping[str, float]
LocationKey = Tuple[Tuple[str, float], ...]

# Type of mapping of axes to their minimum, default and maximum values, i.e.
# `{"wght": (100.0, 400.0, 900.0), "wdth": (75.0, 100.0, 100.0)}`.
AxisBounds = Dict[str, Tuple[float, float, float]]

# For mapping `wdth` axis user values to the OS2 table's width class field.
WDTH_VALUE_TO_OS2_WIDTH_CLASS = {
    50: 1,
    62.5: 2,
    75: 3,
    87.5: 4,
    100: 5,
    112.5: 6,
    125: 7,
    150: 8,
    200: 9,
}

# Font info fields that are not interpolated and should be copied from the
# default font to the instance.
#
# fontMath at the time of this writing handles the following attributes:
# https://github.com/robotools/fontMath/blob/0.5.0/Lib/fontMath/mathInfo.py#L360-L422
#
# From the attributes that are left, we skip instance-specific ones on purpose:
# - guidelines
# - postscriptFontName
# - styleMapFamilyName
# - styleMapStyleName
# - styleName
# - openTypeNameCompatibleFullName
# - openTypeNamePreferredFamilyName
# - openTypeNamePreferredSubfamilyName
# - openTypeNameUniqueID
# - openTypeNameWWSFamilyName
# - openTypeNameWWSSubfamilyName
# - openTypeOS2Panose
# - postscriptFullName
# - postscriptUniqueID
# - woffMetadataUniqueID
#
# Some, we skip because they are deprecated:
# - macintoshFONDFamilyID
# - macintoshFONDName
# - year
#
# This means we implicitly require the `stylename` attribute in the Designspace
# `<instance>` element.
UFO_INFO_ATTRIBUTES_TO_COPY_TO_INSTANCES = {
    "copyright",
    "familyName",
    "note",
    "openTypeGaspRangeRecords",
    "openTypeHeadCreated",
    "openTypeHeadFlags",
    "openTypeNameDescription",
    "openTypeNameDesigner",
    "openTypeNameDesignerURL",
    "openTypeNameLicense",
    "openTypeNameLicenseURL",
    "openTypeNameManufacturer",
    "openTypeNameManufacturerURL",
    "openTypeNameRecords",
    "openTypeNameSampleText",
    "openTypeNameVersion",
    "openTypeOS2CodePageRanges",
    "openTypeOS2FamilyClass",
    "openTypeOS2Selection",
    "openTypeOS2Type",
    "openTypeOS2UnicodeRanges",
    "openTypeOS2VendorID",
    "postscriptDefaultCharacter",
    "postscriptForceBold",
    "postscriptIsFixedPitch",
    "postscriptWindowsCharacterSet",
    "trademark",
    "versionMajor",
    "versionMinor",
    "woffMajorVersion",
    "woffMetadataCopyright",
    "woffMetadataCredits",
    "woffMetadataDescription",
    "woffMetadataExtensions",
    "woffMetadataLicense",
    "woffMetadataLicensee",
    "woffMetadataTrademark",
    "woffMetadataVendor",
    "woffMinorVersion",
}


# Custom exception for this module
class InstantiatorError(Exception):
    pass


def process_rules_swaps(rules, location, glyphNames):
    """Apply these rules at this location to these glyphnames
    - rule order matters

    Return a list of (oldName, newName) in the same order as the rules.
    """
    swaps = []
    glyphNames = set(glyphNames)
    for rule in rules:
        if designspaceLib.evaluateRule(rule, location):
            for oldName, newName in rule.subs:
                # Here I don't check if the new name is also in glyphNames...
                # I guess it should be, so that we can swap, and if it isn't,
                # then it's better to error out later when we try to swap,
                # instead of silently ignoring the rule here.
                if oldName in glyphNames:
                    swaps.append((oldName, newName))
    return swaps


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Instantiator:
    """Data class that holds all necessary information to generate a static
    font instance object at an arbitary location within the design space."""

    axis_bounds: AxisBounds  # Design space!
    copy_feature_text: str
    copy_nonkerning_groups: Mapping[str, List[str]]
    copy_info: ufoLib2.objects.Info
    copy_lib: Mapping[str, Any]
    default_design_location: Location
    designspace_rules: List[designspaceLib.RuleDescriptor]
    glyph_mutators: Mapping[str, "Variator"]
    glyph_name_to_unicodes: Dict[str, List[int]]
    info_mutator: "Variator"
    kerning_mutator: "Variator"
    round_geometry: bool
    skip_export_glyphs: List[str]
    special_axes: Mapping[str, designspaceLib.AxisDescriptor]

    @classmethod
    def from_designspace(
        cls,
        designspace: designspaceLib.DesignSpaceDocument,
        round_geometry: bool = True,
    ):
        """Instantiates a new data class from a Designspace object."""
        if designspace.default is None:
            raise InstantiatorError(_error_msg_no_default(designspace))

        if any(hasattr(axis, "values") for axis in designspace.axes):
            raise InstantiatorError(
                "The given designspace has one or more discrete (= non-interpolating) "
                "axes. You should split this designspace into smaller interpolating "
                "spaces and use the Instantiator on each. See the method "
                "`fontTools.designspaceLib.split.splitInterpolable()`"
            )

        if any(anisotropic(instance.location) for instance in designspace.instances):
            raise InstantiatorError(
                "The Designspace contains anisotropic instance locations, which are "
                "not supported by varLib. Look for and remove all 'yvalue=\"...\"' or "
                "use MutatorMath instead."
            )

        designspace.loadSourceFonts(ufoLib2.Font.open)

        # The default font (default layer) determines which glyphs are interpolated,
        # because the math behind varLib and MutatorMath uses the default font as the
        # point of reference for all data.
        default_font = designspace.default.font
        glyph_names: Set[str] = set(default_font.keys())

        for source in designspace.sources:
            other_names = set(source.font.keys())
            diff_names = other_names - glyph_names
            if diff_names:
                logger.warning(
                    "The source %s (%s) contains glyphs that are missing from the "
                    "default source, which will be ignored: %s. If this is unintended, "
                    "check that these glyphs have the exact same name as the "
                    "corresponding glyphs in the default source.",
                    source.name,
                    source.filename,
                    ", ".join(sorted(diff_names)),
                )

        # Construct Variators
        axis_bounds: AxisBounds = {}  # Design space!
        axis_order: List[str] = []
        special_axes = {}
        for axis in designspace.axes:
            axis_order.append(axis.name)
            axis_bounds[axis.name] = (
                axis.map_forward(axis.minimum),
                axis.map_forward(axis.default),
                axis.map_forward(axis.maximum),
            )
            # Some axes relate to existing OpenType fields and get special attention.
            if axis.tag in {"wght", "wdth", "slnt"}:
                special_axes[axis.tag] = axis

        masters_info = collect_info_masters(designspace, axis_bounds)
        try:
            info_mutator = Variator.from_masters(masters_info, axis_order)
        except varLib.errors.VarLibError as e:
            raise InstantiatorError(
                f"Cannot set up fontinfo for interpolation: {e}'"
            ) from e

        masters_kerning = collect_kerning_masters(designspace, axis_bounds)
        try:
            kerning_mutator = Variator.from_masters(masters_kerning, axis_order)
        except varLib.errors.VarLibError as e:
            raise InstantiatorError(
                f"Cannot set up kerning for interpolation: {e}'"
            ) from e

        glyph_mutators: Dict[str, Variator] = {}
        glyph_name_to_unicodes: Dict[str, List[int]] = {}
        for glyph_name in glyph_names:
            items = collect_glyph_masters(designspace, glyph_name, axis_bounds)
            try:
                glyph_mutators[glyph_name] = Variator.from_masters(items, axis_order)
            except varLib.errors.VarLibError as e:
                raise InstantiatorError(
                    f"Cannot set up glyph '{glyph_name}' for interpolation: {e}'"
                ) from e
            glyph_name_to_unicodes[glyph_name] = default_font[glyph_name].unicodes

        # Construct defaults to copy over
        copy_feature_text: str = default_font.features.text
        copy_nonkerning_groups: Mapping[str, List[str]] = {
            key: glyph_names
            for key, glyph_names in default_font.groups.items()
            if not key.startswith(("public.kern1.", "public.kern2."))
        }  # Kerning groups are taken care of by the kerning Variator.
        copy_info: ufoLib2.objects.Info = default_font.info
        copy_lib: Mapping[str, Any] = default_font.lib

        # The list of glyphs-not-to-export-and-decompose-where-used-as-a-component is
        # supposed to be taken from the Designspace when a Designspace is used as the
        # starting point of the compilation process. It should be exported to all
        # instance libs, where the ufo2ft compilation functions will pick it up.
        skip_export_glyphs = designspace.lib.get("public.skipExportGlyphs", [])

        return cls(
            axis_bounds,
            copy_feature_text,
            copy_nonkerning_groups,
            copy_info,
            copy_lib,
            designspace.default.location,
            designspace.rules,
            glyph_mutators,
            glyph_name_to_unicodes,
            info_mutator,
            kerning_mutator,
            round_geometry,
            skip_export_glyphs,
            special_axes,
        )

    def generate_instance(
        self, instance: designspaceLib.InstanceDescriptor
    ) -> ufoLib2.Font:
        """Generate an interpolated instance font object for an
        InstanceDescriptor."""
        if anisotropic(instance.location):
            raise InstantiatorError(
                f"Instance {instance.familyName}-"
                f"{instance.styleName}: Anisotropic location "
                f"{instance.location} not supported by varLib."
            )

        font = ufoLib2.Font()

        # Instances may leave out locations that match the default source, so merge
        # default location with the instance's location.
        location = {**self.default_design_location, **instance.location}
        location_normalized = varLib.models.normalizeLocation(
            location, self.axis_bounds
        )

        # Kerning
        kerning_instance = self.kerning_mutator.instance_at(location_normalized)
        if self.round_geometry:
            kerning_instance.round()
        kerning_instance.extractKerning(font)

        # Info
        self._generate_instance_info(instance, location_normalized, location, font)

        # Non-kerning groups. Kerning groups have been taken care of by the kerning
        # instance.
        for key, glyph_names in self.copy_nonkerning_groups.items():
            font.groups[key] = [name for name in glyph_names]

        # Features
        font.features.text = self.copy_feature_text

        # Lib
        #  1. Copy the default lib to the instance.
        font.lib = typing.cast(dict, copy.deepcopy(self.copy_lib))
        #  2. Copy the Designspace's skipExportGlyphs list over to the UFO to
        #     make sure it wins over the default UFO one.
        font.lib["public.skipExportGlyphs"] = [name for name in self.skip_export_glyphs]
        #  3. Write _design_ location to instance's lib.
        font.lib["designspace.location"] = [loc for loc in location.items()]

        # Glyphs
        for glyph_name, glyph_mutator in self.glyph_mutators.items():
            glyph = font.newGlyph(glyph_name)

            try:
                glyph_instance = glyph_mutator.instance_at(location_normalized)

                if self.round_geometry:
                    glyph_instance = glyph_instance.round()

                # onlyGeometry=True does not set name and unicodes, in ufoLib2 we can't
                # modify a glyph's name. Copy unicodes from default font.
                glyph_instance.extractGlyph(glyph, onlyGeometry=True)
            except Exception as e:
                # TODO: Figure out what exceptions fontMath/varLib can throw.
                # By default, explode if we cannot generate a glyph instance for
                # whatever reason (usually outline incompatibility)...
                if glyph_name not in self.skip_export_glyphs:
                    raise InstantiatorError(
                        f"Failed to generate instance of glyph '{glyph_name}': "
                        f"{str(e)}. (Note: the most common cause for an error here is "
                        "that the glyph outlines are not point-for-point compatible or "
                        "have the same starting point or are in the same order in all "
                        "masters.)"
                    ) from e

                # ...except if the glyph is in public.skipExportGlyphs and would
                # therefore be removed from the compiled font anyway. There's not much
                # we can do except leave it empty in the instance and tell the user.
                logger.warning(
                    "Failed to generate instance of glyph '%s', which is marked as "
                    "non-exportable. Glyph will be left empty. Failure reason: %s",
                    glyph_name,
                    e,
                )

            glyph.unicodes = [uv for uv in self.glyph_name_to_unicodes[glyph_name]]

        # Process rules
        glyph_names_list = self.glyph_mutators.keys()
        # The order of the swaps below is independent of the order of glyph names.
        # It depends on the order of the <sub>s in the designspace rules.
        swaps = process_rules_swaps(self.designspace_rules, location, glyph_names_list)
        for name_old, name_new in swaps:
            if name_old != name_new:
                swap_glyph_names(font, name_old, name_new)

        return font

    def _generate_instance_info(
        self,
        instance: designspaceLib.InstanceDescriptor,
        location_normalized: Location,
        location: Location,
        font: ufoLib2.Font,
    ) -> None:
        """Generate fontinfo related attributes.

        Separate, as fontinfo treatment is more extensive than the rest.
        """
        info_instance = self.info_mutator.instance_at(location_normalized)
        if self.round_geometry:
            info_instance = info_instance.round()
        info_instance.extractInfo(font.info)

        # Copy non-interpolating metadata from the default font.
        for attribute in UFO_INFO_ATTRIBUTES_TO_COPY_TO_INSTANCES:
            if hasattr(self.copy_info, attribute):
                setattr(
                    font.info,
                    attribute,
                    copy.deepcopy(getattr(self.copy_info, attribute)),
                )

        # TODO: multilingual names to replace possibly existing name records.
        if instance.familyName:
            font.info.familyName = instance.familyName
        if instance.styleName is None:
            logger.warning(
                "The given instance or instance at location %s is missing the "
                "stylename attribute, which is required. Copying over the styleName "
                "from the default font, which is probably wrong.",
                location,
            )
            font.info.styleName = self.copy_info.styleName
        else:
            font.info.styleName = instance.styleName
        if instance.postScriptFontName:
            font.info.postscriptFontName = instance.postScriptFontName
        if instance.styleMapFamilyName:
            font.info.styleMapFamilyName = instance.styleMapFamilyName
        if instance.styleMapStyleName:
            font.info.styleMapStyleName = instance.styleMapStyleName

        # If the masters haven't set the OS/2 weight and width class, use the
        # user-space values ("input") of the axis mapping in the Designspace file for
        # weight and width axes, if they exist. The slnt axis' value maps 1:1 to
        # italicAngle. Clamp the values to the valid ranges.
        if info_instance.openTypeOS2WeightClass is None and "wght" in self.special_axes:
            weight_axis = self.special_axes["wght"]
            font.info.openTypeOS2WeightClass = weight_class_from_wght_value(
                weight_axis.map_backward(location[weight_axis.name])
            )
        if info_instance.openTypeOS2WidthClass is None and "wdth" in self.special_axes:
            width_axis = self.special_axes["wdth"]
            font.info.openTypeOS2WidthClass = width_class_from_wdth_value(
                width_axis.map_backward(location[width_axis.name])
            )
        if info_instance.italicAngle is None and "slnt" in self.special_axes:
            slant_axis = self.special_axes["slnt"]
            font.info.italicAngle = italic_angle_from_slnt_value(
                slant_axis.map_backward(location[slant_axis.name])
            )


def _error_msg_no_default(designspace: designspaceLib.DesignSpaceDocument) -> str:
    if any(axis.map for axis in designspace.axes):
        bonus_msg = (
            "For axes with a mapping, the 'default' values should have an "
            "'input=\"...\"' map value, where the corresponding 'output=\"...\"' "
            "value then points to the master source."
        )
    else:
        bonus_msg = ""

    default_location = ", ".join(
        f"{k}: {v}" for k, v in designspace.newDefaultLocation().items()
    )

    return (
        "Can't generate UFOs from this Designspace because there is no default "
        f"master source at location '{default_location}'. Check that all 'default' "
        "values of all axes together point to a single actual master source. "
        f"{bonus_msg}"
    )


def location_to_key(location: Location) -> LocationKey:
    """Converts a Location into a sorted tuple so it can be used as a dict
    key."""
    return tuple(sorted(location.items()))


def anisotropic(location: Location) -> bool:
    """Tests if any single location value is a MutatorMath-style anisotropic
    value, i.e. is a tuple of (x, y)."""
    return any(isinstance(v, tuple) for v in location.values())


def collect_info_masters(
    designspace: designspaceLib.DesignSpaceDocument, axis_bounds: AxisBounds
) -> List[Tuple[Location, FontMathObject]]:
    """Return master Info objects wrapped by MathInfo."""
    locations_and_masters = []
    for source in designspace.sources:
        if source.layerName is not None:
            continue  # No font info in source layers.

        normalized_location = varLib.models.normalizeLocation(
            source.location, axis_bounds
        )
        locations_and_masters.append(
            (normalized_location, fontMath.MathInfo(source.font.info))
        )

    return locations_and_masters


def collect_kerning_masters(
    designspace: designspaceLib.DesignSpaceDocument, axis_bounds: AxisBounds
) -> List[Tuple[Location, FontMathObject]]:
    """Return master kerning objects wrapped by MathKerning."""

    # Always take the groups from the default source. This also avoids fontMath
    # making a union of all groups it is given.
    groups = designspace.default.font.groups

    locations_and_masters = []
    for source in designspace.sources:
        if source.layerName is not None:
            continue  # No kerning in source layers.

        # If a source has groups, they should match the default's.
        if source.font.groups and source.font.groups != groups:
            logger.warning(
                "The source %s (%s) contains different groups than the default source. "
                "The default source's groups will be used for the instances.",
                source.name,
                source.filename,
            )

        # This assumes that groups of all sources are the same.
        normalized_location = varLib.models.normalizeLocation(
            source.location, axis_bounds
        )
        locations_and_masters.append(
            (normalized_location, fontMath.MathKerning(source.font.kerning, groups))
        )

    return locations_and_masters


def collect_glyph_masters(
    designspace: designspaceLib.DesignSpaceDocument,
    glyph_name: str,
    axis_bounds: AxisBounds,
) -> List[Tuple[Location, FontMathObject]]:
    """Return master glyph objects for glyph_name wrapped by MathGlyph.

    Note: skips empty source glyphs if the default glyph is not empty to almost match
    what ufoProcessor is doing. In e.g. Mutator Sans, the 'S.closed' glyph is left
    empty in one source layer. One could treat this as a source error, but ufoProcessor
    specifically has code to skip that empty glyph and carry on.
    """
    locations_and_masters = []
    default_glyph_empty = False
    other_glyph_empty = False

    for source in designspace.sources:
        if source.layerName is None:  # Source font.
            source_layer = source.font.layers.defaultLayer
        else:  # Source layer.
            source_layer = source.font.layers[source.layerName]

        # Sparse fonts do not and layers may not contain every glyph.
        if glyph_name not in source_layer:
            continue

        source_glyph = source_layer[glyph_name]

        if not (source_glyph.contours or source_glyph.components):
            if source is designspace.findDefault():
                default_glyph_empty = True
            else:
                other_glyph_empty = True

        normalized_location = varLib.models.normalizeLocation(
            source.location, axis_bounds
        )
        locations_and_masters.append(
            (normalized_location, fontMath.MathGlyph(source_glyph))
        )

    # Filter out empty glyphs if the default glyph is not empty.
    if not default_glyph_empty and other_glyph_empty:
        locations_and_masters = [
            (loc, master)
            for loc, master in locations_and_masters
            if master.contours or master.components
        ]

    return locations_and_masters


def width_class_from_wdth_value(wdth_user_value) -> int:
    """Return the OS/2 width class from the wdth axis user value.

    The OpenType 1.8.3 specification states:

        When mapping from 'wdth' values to usWidthClass, interpolate fractional
        values between the mapped values and then round, and clamp to the range
        1 to 9.

    "Mapped values" probably means the in-percent numbers layed out for the OS/2
    width class, so we are forcing these numerical semantics on the user values
    of the wdth axis.
    """
    width_user_value = min(max(wdth_user_value, 50), 200)
    width_user_value_mapped = varLib.models.piecewiseLinearMap(
        width_user_value, WDTH_VALUE_TO_OS2_WIDTH_CLASS
    )
    return fontTools.misc.fixedTools.otRound(width_user_value_mapped)


def weight_class_from_wght_value(wght_user_value) -> int:
    """Return the OS/2 weight class from the wght axis user value."""
    weight_user_value = min(max(wght_user_value, 1), 1000)
    return fontTools.misc.fixedTools.otRound(weight_user_value)


def italic_angle_from_slnt_value(slnt_user_value) -> Union[int, float]:
    """Return the italic angle from the slnt axis user value."""
    slant_user_value = min(max(slnt_user_value, -90), 90)
    return slant_user_value


def swap_glyph_names(font: ufoLib2.Font, name_old: str, name_new: str):
    """Swap two existing glyphs in the default layer of a font (outlines,
    width, component references, kerning references, group membership).

    The idea behind swapping instead of overwriting is explained in
    https://github.com/fonttools/fonttools/tree/main/Doc/source/designspaceLib#ufo-instances.
    We need to keep the old glyph around in case any other glyph references
    it; glyphs that are not explicitly substituted by rules should not be
    affected by the rule application.

    The .unicodes are not swapped. The rules mechanism is supposed to swap
    glyphs, not characters.
    """

    if name_old not in font or name_new not in font:
        raise InstantiatorError(
            f"Cannot swap glyphs '{name_old}' and '{name_new}', as either or both are "
            "missing."
        )

    # 1. Swap outlines and glyph width. Ignore lib content and other properties.
    glyph_swap = ufoLib2.objects.Glyph(name="temporary_swap_glyph")
    glyph_old = font[name_old]
    glyph_new = font[name_new]

    p = glyph_swap.getPointPen()
    glyph_old.drawPoints(p)
    glyph_swap.width = glyph_old.width

    glyph_old.clearContours()
    glyph_old.clearComponents()
    p = glyph_old.getPointPen()
    glyph_new.drawPoints(p)
    glyph_old.width = glyph_new.width

    glyph_new.clearContours()
    glyph_new.clearComponents()
    p = glyph_new.getPointPen()
    glyph_swap.drawPoints(p)
    glyph_new.width = glyph_swap.width

    # 2. Swap anchors.
    glyph_swap.anchors = glyph_old.anchors
    glyph_old.anchors = glyph_new.anchors
    glyph_new.anchors = glyph_swap.anchors

    # 3. Remap components.
    for g in font:
        for c in g.components:
            if c.baseGlyph == name_old:
                c.baseGlyph = name_new
            elif c.baseGlyph == name_new:
                c.baseGlyph = name_old

    # 4. Swap literal names in kerning.
    kerning_new = {}
    for first, second in font.kerning.keys():
        value = font.kerning[(first, second)]
        if first == name_old:
            first = name_new
        elif first == name_new:
            first = name_old
        if second == name_old:
            second = name_new
        elif second == name_new:
            second = name_old
        kerning_new[(first, second)] = value
    font.kerning = kerning_new

    # 5. Swap names in groups.
    for group_name, group_members in font.groups.items():
        group_members_new = []
        for name in group_members:
            if name == name_old:
                group_members_new.append(name_new)
            elif name == name_new:
                group_members_new.append(name_old)
            else:
                group_members_new.append(name)
        font.groups[group_name] = group_members_new


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Variator:
    """A middle-man class that ingests a mapping of normalized locations to
    masters plus axis definitions and uses varLib to spit out interpolated
    instances at specified normalized locations.

    fontMath objects stand in for the actual master objects from the
    UFO. Upon generating an instance, these objects have to be extracted
    into an actual UFO object.
    """

    masters: List[FontMathObject]
    location_to_master: Mapping[LocationKey, FontMathObject]
    model: varLib.models.VariationModel

    @classmethod
    def from_masters(
        cls, items: List[Tuple[Location, FontMathObject]], axis_order: List[str]
    ):
        masters = []
        master_locations = []
        location_to_master = {}
        for normalized_location, master in items:
            master_locations.append(normalized_location)
            masters.append(master)
            location_to_master[location_to_key(normalized_location)] = master
        model = varLib.models.VariationModel(master_locations, axis_order)

        return cls(masters, location_to_master, model)

    def instance_at(self, normalized_location: Location) -> FontMathObject:
        """Return a FontMathObject for the specified location ready to be
        inflated.

        If an instance location matches a master location, this method
        returns the master data instead of running through varLib. This
        is both an optimization _and_ it enables having a Designspace
        with instances matching their masters without requiring them to
        be compatible. Glyphs.app works this way; it will only generate
        a font from an instance, but compatibility is only required if
        there is actual interpolation to be done. This enables us to
        store incompatible bare masters in one Designspace and having
        arbitrary instance data applied to them.
        """
        normalized_location_key = location_to_key(normalized_location)
        if normalized_location_key in self.location_to_master:
            return copy.deepcopy(self.location_to_master[normalized_location_key])

        return self.model.interpolateFromMasters(normalized_location, self.masters)
