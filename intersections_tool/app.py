import sys

import maya.OpenMaya as om
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya import cmds

from intersections_tool.vendor.Qt import QtCore, QtWidgets
from intersections_tool import lib


# Modified for standalone from https://github.com/BigRoy/maya-capture-gui/blob
#                               /master/capture_gui/plugins/timeplugin.py#L73
class TimeWidget(QtWidgets.QWidget):
    """Widget for time based options"""

    id = "Time Range"
    section = "app"
    order = 30
    label_changed = QtCore.Signal(str)
    options_changed = QtCore.Signal()
    highlight = "border: 1px solid red;"

    RangeTimeSlider = "Time Slider"
    RangeStartEnd = "Start/End"
    CurrentFrame = "Current Frame"

    def __init__(self, parent=None):
        super(TimeWidget, self).__init__(parent=parent)

        self._event_callbacks = list()

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.RangeTimeSlider,
                            self.RangeStartEnd,
                            self.CurrentFrame])

        frame_input_height = 20
        self.start = QtWidgets.QSpinBox()
        self.start.setRange(-sys.maxint, sys.maxint)
        self.start.setFixedHeight(frame_input_height)
        self.end = QtWidgets.QSpinBox()
        self.end.setRange(-sys.maxint, sys.maxint)
        self.end.setFixedHeight(frame_input_height)

        # unique frames field
        self.custom_frames = QtWidgets.QLineEdit()
        self.custom_frames.setFixedHeight(frame_input_height)
        self.custom_frames.setPlaceholderText("Example: 1-20,25;50;75,100-150")
        self.custom_frames.setVisible(False)

        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.start)
        self._layout.addWidget(self.end)
        self._layout.addWidget(self.custom_frames)

        # Connect callbacks to ensure start is never higher then end
        # and the end is never lower than start
        self.end.valueChanged.connect(self._ensure_start)
        self.start.valueChanged.connect(self._ensure_end)

        self.on_mode_changed()  # force enabled state refresh

        self.mode.currentIndexChanged.connect(self.on_mode_changed)
        self.start.valueChanged.connect(self.on_mode_changed)
        self.end.valueChanged.connect(self.on_mode_changed)
        self.custom_frames.textChanged.connect(self.on_mode_changed)

    def _ensure_start(self, value):
        self.start.setValue(min(self.start.value(), value))

    def _ensure_end(self, value):
        self.end.setValue(max(self.end.value(), value))

    def on_mode_changed(self, emit=True):
        """Update the GUI when the user updated the time range or settings.
        Arguments:
            emit (bool): Whether to emit the options changed signal
        Returns:
            None
        """

        mode = self.mode.currentText()
        if mode == self.RangeTimeSlider:
            start, end = lib.get_time_slider_range()
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            self.start.setVisible(True)
            self.end.setVisible(True)
            self.custom_frames.setVisible(False)
            mode_values = int(start), int(end)
        elif mode == self.RangeStartEnd:
            self.start.setEnabled(True)
            self.end.setEnabled(True)
            self.start.setVisible(True)
            self.end.setVisible(True)
            self.custom_frames.setVisible(False)
            mode_values = self.start.value(), self.end.value()

        else:
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            self.start.setVisible(True)
            self.end.setVisible(True)
            self.custom_frames.setVisible(False)
            currentframe = int(lib.get_current_frame())
            mode_values = "({})".format(currentframe)

        # Update label
        self.label = "Time Range {}".format(mode_values)
        self.label_changed.emit(self.label)

        if emit:
            self.options_changed.emit()

    def get_outputs(self, panel=""):
        """Get the plugin outputs that matches `capture.capture` arguments
        Returns:
            dict: Plugin outputs
        """

        mode = self.mode.currentText()

        if mode == self.RangeTimeSlider:
            start, end = lib.get_time_slider_range()

        elif mode == self.RangeStartEnd:
            start = self.start.value()
            end = self.end.value()

        elif mode == self.CurrentFrame:
            start = end = lib.get_current_frame()

        return {"start_frame": start,
                "end_frame": end}

    def get_inputs(self, as_preset):
        return {"time": self.mode.currentText(),
                "start_frame": self.start.value(),
                "end_frame": self.end.value()}

    def apply_inputs(self, settings):
        # get values
        mode = self.mode.findText(settings.get("time", self.RangeTimeSlider))
        startframe = settings.get("start_frame", 1)
        endframe = settings.get("end_frame", 120)
        custom_frames = settings.get("frame", None)

        # set values
        self.mode.setCurrentIndex(mode)
        self.start.setValue(int(startframe))
        self.end.setValue(int(endframe))
        if custom_frames is not None:
            self.custom_frames.setText(custom_frames)

    def initialize(self):
        self._register_callbacks()

    def uninitialize(self):
        self._remove_callbacks()

    def _register_callbacks(self):
        """Register maya time and playback range change callbacks.
        Register callbacks to ensure Capture GUI reacts to changes in
        the Maya GUI in regards to time slider and current frame
        """

        callback = lambda x: self.on_mode_changed(emit=False)

        # this avoid overriding the ids on re-run
        currentframe = om.MEventMessage.addEventCallback("timeChanged",
                                                         callback)
        timerange = om.MEventMessage.addEventCallback("playbackRangeChanged",
                                                      callback)

        self._event_callbacks.append(currentframe)
        self._event_callbacks.append(timerange)

    def _remove_callbacks(self):
        """Remove callbacks when closing widget"""
        for callback in self._event_callbacks:
            try:
                om.MEventMessage.removeCallback(callback)
            except Exception as error:
                lib.error("Encounter error : {}".format(error))


# Modified for standalone from https://github.com/BigRoy/maya-capture-gui/blob
#                               /master/capture_gui/plugins/cameraplugin.py#L8
class CameraWidget(QtWidgets.QWidget):
    """Camera widget.
    Allows to select a camera.
    """
    id = "Camera"
    section = "app"
    order = 10
    label_changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(CameraWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.cameras = QtWidgets.QComboBox()
        self.cameras.setMinimumWidth(200)

        self.get_active = QtWidgets.QPushButton("Get active")
        self.get_active.setToolTip("Set camera from currently active view")
        self.refresh = QtWidgets.QPushButton("Refresh")
        self.refresh.setToolTip("Refresh the list of cameras")

        self._layout.addWidget(self.cameras)
        self._layout.addWidget(self.get_active)
        self._layout.addWidget(self.refresh)

        # Signals
        self.connections()

        # Force update of the label
        self.set_active_cam()
        self.on_update_label()

    def connections(self):
        self.get_active.clicked.connect(self.set_active_cam)
        self.refresh.clicked.connect(self.on_refresh)

        self.cameras.currentIndexChanged.connect(self.on_update_label)
        self.cameras.currentIndexChanged.connect(self.validate)

    def set_active_cam(self):
        cam = lib.get_current_camera()
        self.on_refresh(camera=cam)

    def select_camera(self, cam):
        if cam:
            # Ensure long name
            cameras = cmds.ls(cam, long=True)
            if not cameras:
                return
            cam = cameras[0]

            # Find the index in the list
            for i in range(self.cameras.count()):
                value = str(self.cameras.itemText(i))
                if value == cam:
                    self.cameras.setCurrentIndex(i)
                    return

    def validate(self):

        errors = []
        camera = self.cameras.currentText()
        if not cmds.objExists(camera):
            errors.append("{} : Selected camera '{}' "
                          "does not exist!".format(self.id, camera))
            self.cameras.setStyleSheet(self.highlight)
        else:
            self.cameras.setStyleSheet("")

        return errors

    def get_outputs(self):
        """Return currently selected camera from combobox."""

        idx = self.cameras.currentIndex()
        camera = str(self.cameras.itemText(idx)) if idx != -1 else None

        return {"camera": camera}

    def on_refresh(self, camera=None):
        """Refresh the camera list with all current cameras in scene.
        A currentIndexChanged signal is only emitted for the cameras combobox
        when the camera is different at the end of the refresh.
        Args:
            camera (str): When name of camera is passed it will try to select
                the camera with this name after the refresh.
        Returns:
            None
        """

        cam = self.get_outputs()['camera']

        # Get original selection
        if camera is None:
            index = self.cameras.currentIndex()
            if index != -1:
                camera = self.cameras.currentText()

        self.cameras.blockSignals(True)

        # Update the list with available cameras
        self.cameras.clear()

        cam_shapes = cmds.ls(type="camera")
        cam_transforms = cmds.listRelatives(cam_shapes,
                                            parent=True,
                                            fullPath=True)
        self.cameras.addItems(cam_transforms)

        # If original selection, try to reselect
        self.select_camera(camera)

        self.cameras.blockSignals(False)

        # If camera changed emit signal
        if cam != self.get_outputs()['camera']:
            idx = self.cameras.currentIndex()
            self.cameras.currentIndexChanged.emit(idx)

    def on_update_label(self):

        cam = self.cameras.currentText()
        cam = cam.rsplit("|", 1)[-1]  # ensure short name
        self.label = "Camera ({0})".format(cam)

        self.label_changed.emit(self.label)


class table_widget_item(QtWidgets.QTableWidgetItem):
    def __init__(self, value):
        super(table_widget_item, self).__init__(str(value))

    def __lt__(self, other):
        if (isinstance(other, table_widget_item)):
            selfDataValue = float(self.data(QtCore.Qt.EditRole))
            otherDataValue = float(other.data(QtCore.Qt.EditRole))
            return selfDataValue < otherDataValue
        else:
            return QtWidgets.QTableWidgetItem.__lt__(self, other)


class Window(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.setWindowTitle("Intersections Tool")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.setLayout(QtWidgets.QVBoxLayout())

        self.layout().addWidget(QtWidgets.QLabel("Time Range"))
        self.time_widget = TimeWidget()
        self.layout().addWidget(self.time_widget)

        self.layout().addWidget(QtWidgets.QLabel("Camera"))
        self.camera_widget = CameraWidget()
        self.layout().addWidget(self.camera_widget)

        layout = QtWidgets.QHBoxLayout()
        self.prune_checkbox = QtWidgets.QCheckBox("Prune Zero Coverage Frames")
        self.prune_checkbox.setChecked(True)
        layout.addWidget(self.prune_checkbox)
        self.delete_pfx = QtWidgets.QCheckBox("Delete intersect PFX")
        layout.addWidget(self.delete_pfx)
        self.layout().addLayout(layout)

        self.analyze_button = QtWidgets.QPushButton("Analyze Frames")
        self.layout().addWidget(self.analyze_button)
        self.analyze_button.clicked.connect(self.on_analyze_button_clicked)

        self.table_widget = QtWidgets.QTableWidget(1, 2)
        self.layout().addWidget(self.table_widget)
        self.table_widget.setHorizontalHeaderLabels(["frame", "coverage"])
        self.table_widget.verticalHeader().hide()
        self.table_widget.setSortingEnabled(True)
        self.table_widget.setEditTriggers(
            QtWidgets.QTableWidget.NoEditTriggers
        )
        self.table_widget.cellClicked.connect(
            self.on_table_widget_cell_clicked
        )

    def on_table_widget_cell_clicked(self, row, column):
        self.table_widget.selectRow(row)
        frame = float(self.table_widget.item(row, 0).text())
        lib.set_current_frame(frame)

    def on_analyze_button_clicked(self):
        settings = {}
        settings.update(self.time_widget.get_outputs())
        settings.update(self.camera_widget.get_outputs())
        settings["delete_pfx"] = self.delete_pfx.isChecked()

        # Get coverage date set.
        coverage_data = lib.get_coverage(**settings)

        self.table_widget.clearContents()
        self.table_widget.setRowCount(len(coverage_data))
        row = 0
        for frame, coverage in coverage_data:
            if self.prune_checkbox.isChecked() and coverage == 0.0:
                continue

            self.table_widget.setItem(row, 1, table_widget_item(coverage))
            self.table_widget.setItem(row, 0, table_widget_item(frame))
            row += 1

        self.table_widget.setRowCount(row)
        self.table_widget.sortItems(0, QtCore.Qt.AscendingOrder)


def show(parent=None):
    window = Window(parent)
    window.show()

    return window
