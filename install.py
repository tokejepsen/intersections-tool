"""
Drag and drop for Maya 2018+
"""
import os
import sys


try:
    import maya.mel
    import maya.cmds
    isMaya = True
except ImportError:
    isMaya = False


def onMayaDroppedPythonFile(*args, **kwargs):
    """This function is only supported since Maya 2017 Update 3"""
    pass


def _onMayaDropped():
    """Dragging and dropping this file into the scene executes the file."""

    source_path = os.path.join(os.path.dirname(__file__))
    source_path = os.path.normpath(source_path)

    command = """
# -----------------------------------
# intersections-tool
# -----------------------------------
import os
import sys

if not os.path.exists(r'{path}'):
    raise IOError(r'The source path "{path}" does not exist!')

if r'{path}' not in sys.path:
    sys.path.insert(0, r'{path}')

import intersections_tool
intersections_tool.show()
""".format(path=source_path)

    shelf = maya.mel.eval('$gShelfTopLevel=$gShelfTopLevel')
    parent = maya.cmds.tabLayout(shelf, query=True, selectTab=True)
    maya.cmds.shelfButton(
        command=command,
        annotation="Intersections Tool",
        sourceType="Python",
        parent=parent,
        image="pythonFamily.png",
        image1="pythonFamily.png",
        imageOverlayLabel="Intersections Tool"
    )


if isMaya:
    _onMayaDropped()
