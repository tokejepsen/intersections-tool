import os
import time

from capture import snap
import png

import pymel.core
from maya.app.renderSetup.model import renderSetup, typeIDs, renderLayer


def apply_pfxtoon(meshes):
    """Apply a white intersections pfx to all meshes in the scene."""

    # Find previous pfx and delete to make sure settings on pfx is correct.
    for node in pymel.core.ls(type="pfxToon"):
        if hasattr(node, "intersections_tool"):
            pymel.core.delete(node.getParent())

    # Create pfx.
    pfxtoon_shape = pymel.core.createNode("pfxToon")
    preset = {
        "displayPercent": 100,
        "intersectionLines": 1,
        "selfIntersect": 1,
        "creaseLines": 0,
        "profileLines": 0,
        "intersectionLineWidth": 10,
        "screenspaceWidth": 1,
        "intersectionColor": (1, 1, 1),
        "maxPixelWidth": 15
    }
    for attribute, value in preset.iteritems():
        pfxtoon_shape.attr(attribute).set(value)

    # Tag pfx for later retrieval.
    pymel.core.addAttr(longName="intersections_tool")

    # Connect all meshes to pfx.
    index = 0
    for mesh in meshes:
        pymel.core.connectAttr(
            mesh + ".outMesh",
            "{0}.inputSurface[{1}].surface".format(pfxtoon_shape, index)
        )
        pymel.core.connectAttr(
            mesh + ".worldMatrix[0]",
            "{0}.inputSurface[{1}].inputWorldMatrix".format(
                pfxtoon_shape, index
            )
        )
        index += 1

    return [pfxtoon_shape.getParent(), pfxtoon_shape]


def snap_frame(frame=None):
    """Capture a single viewport frame with pfx and black background."""

    pymel.core.select(clear=True)
    options = {
        "camera": "persp1",
        "format": "image",
        "compression": "png",
        "frame": frame or pymel.core.currentTime(),
        "viewport_options": {
            "strokes": True, "headsUpDisplay": False, "imagePlane": False
        },
        "display_options": {"displayGradient": False, "background": (0, 0, 0)},
    }
    return snap(**options)


def get_white_coverage(file_path):
    """Analyze the luminance coverage as 0-1 float in an image."""

    img = png.Reader(filename=file_path)
    data = img.read()

    # A full white image has 255 in RGBA.
    pixel_count = data[0] * data[1]
    values_max = pixel_count * 4 * 255

    # Scan pixels for values.
    values_count = 0.0
    for row in data[2]:
        values_count += sum(row)

    # Return 0-1 value of white coverage.
    return values_count / values_max


def create_material_override():
    """Setup a render layer which only shows pfx shapes."""

    # Create useBackground shader.
    shader = pymel.core.shadingNode(
        "useBackground", asShader=True, name="intersections_background"
    )
    shading_group = pymel.core.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name="intersections_backgroundSG"
    )
    pymel.core.connectAttr(
        shader + ".outColor", shading_group + ".surfaceShader"
    )

    # Create render setup layer.
    render_setup = renderSetup.instance()
    layer = render_setup.createRenderLayer("intersections")

    all_shapes_collection = layer.createCollection("shapes")
    all_shapes_collection.getSelector().setFilterType(2)
    all_shapes_collection.getSelector().setPattern("*")

    except_pfx_collection = all_shapes_collection.createCollection(
        "except_pfx"
    )
    except_pfx_collection.getSelector().setFilterType(2)
    except_pfx_collection.getSelector().setPattern("*;-pfxToonShape*")

    override = except_pfx_collection.createOverride(
        "material_override", typeIDs.materialOverride
    )
    pymel.core.connectAttr(
        shading_group.message, override.name() + ".attrValue"
    )

    render_setup.switchToLayer(layer)

    return [shader, shading_group, layer]


def delete_node(node):
    """Convenience method for delete dag node and render layers."""
    if isinstance(node, renderLayer.RenderLayer):
        renderLayer.delete(node)
    else:
        pymel.core.delete(node)


def get_frame_coverage(frame=None, delete_pfx=False):
    """Get the coverage on a single frame."""

    # Create pfx.
    pfx, pfx_shape = apply_pfxtoon(pymel.core.ls(type="mesh"))

    # Create render layer for showing pfx only.
    nodes = create_material_override()

    # Get white coverage in frame.
    frame_file = snap_frame(frame)
    coverage = get_white_coverage(frame_file)

    # Clean up.
    os.remove(frame_file)

    for node in nodes:
        delete_node(node)

    if delete_pfx:
        pymel.core.delete(pfx)

    return coverage


def get_frames_coverage(start_frame=None, end_frame=None):
    """Get a data set of coverage over a frame range."""

    start_frame = start_frame or pymel.core.playbackOptions(
        min=True, query=True
    )
    end_frame = end_frame or pymel.core.playbackOptions(
        max=True, query=True
    )
    data = []
    for frame in range(int(start_frame), int(end_frame) + 1):
        data.append([frame, get_frame_coverage(frame)])

    return data
