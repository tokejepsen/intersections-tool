import os
from shutil import rmtree
from tempfile import gettempdir

from capture import capture
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


def capture_frames(start_frame=None, end_frame=None):
    """Capture a single viewport frame with pfx and black background."""

    # Create temporary folder.
    temp_directory = os.path.join(gettempdir(), '.{}'.format(hash(os.times())))
    os.makedirs(temp_directory)

    # Clear selection so pfx does not get highlighted.
    pymel.core.select(clear=True)

    # Capture viewport.
    options = {
        "camera": "persp1",
        "format": "image",
        "compression": "png",
        "start_frame": start_frame,
        "end_frame": end_frame,
        "filename": os.path.join(temp_directory, "temp"),
        "viewer": False,
        "viewport_options": {
            "strokes": True, "headsUpDisplay": False, "imagePlane": False
        },
        "display_options": {"displayGradient": False, "background": (0, 0, 0)},
    }
    capture(**options)

    return temp_directory


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


def get_coverage(start_frame=None, end_frame=None):
    """Get coverage data set on multiple frames."""
    data = []

    # Create pfx.
    pfx, pfx_shape = apply_pfxtoon(pymel.core.ls(type="mesh"))

    # Create render layer for showing pfx only.
    render_layer_nodes = create_material_override()

    # Get white coverage in frames.
    start_frame = start_frame or pymel.core.playbackOptions(
        min=True, query=True
    )
    end_frame = end_frame or pymel.core.playbackOptions(
        max=True, query=True
    )
    capture_directory = capture_frames(
        start_frame=start_frame, end_frame=end_frame
    )

    frame_count = start_frame
    for f in os.listdir(capture_directory):
        data.append(
            [
                frame_count,
                get_white_coverage(os.path.join(capture_directory, f))
            ]
        )
        frame_count += 1

    # Clean up.
    rmtree(capture_directory, ignore_errors=True)

    for node in render_layer_nodes:
        delete_node(node)

    pymel.core.delete(pfx)

    return data
