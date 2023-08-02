from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QSpinBox, QVBoxLayout, QHBoxLayout
from qtpy.QtGui import QWheelEvent, QPixmap
from napari_deeplabcut import _inputs as inputs

import cv2
import os.path
from napari_deeplabcut import misc


class ZoomView(QGraphicsView):

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Converted to Python from https://stackoverflow.com/a/41688654"""
        if event.modifiers() == Qt.ControlModifier:  # ctrl+scroll zooms
            anchor = self.transformationAnchor()
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            angle = event.angleDelta().y()
            factor = 1.1 if angle > 0 else 0.9
            self.scale(factor, factor)
            self.setTransformationAnchor(anchor)
        else:
            super().wheelEvent(event)

    def set_pixmap(self, pm: QPixmap) -> None:
        self._scene.clear()
        self._scene.addPixmap(pm)


class VideoSkimmer(QWidget):
    """A widget for skimming through videos"""

    # list of known video types that work with the video skimmer
    supported_video_ext = ('.mp4', '.avi')

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Attributes

        self._video_path: str | None = None
        self._video: cv2.VideoCapture | None = None
        self._current_frame: int = -1
        self._total_frames: int = 0

        self._frame_preview: ZoomView = ZoomView(self)
        self._frame_preview.setMinimumSize(256, 144)

        # GUI Elements

        self._options = QWidget(self)

        # frame slider is a slider (with an adjustable range) that controls the current frame shown
        self._frame_slider = inputs.AdjustableRangeSlider(Qt.Orientation.Horizontal, self._options)
        self._frame_slider.slider.valueChanged.connect(self._on_frame_slider_change)
        self._frame_slider.rangeChanged.connect(self._sync_spinbox)

        # frame spinbox shows the currently shown frame and allows it to be changed with the keyboard
        self._frame_spinbox = QSpinBox(self._options)
        self._frame_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._frame_spinbox.valueChanged.connect(self._on_frame_spinbox_change)

        # Layout

        self._layout = QVBoxLayout()
        self._layout.addWidget(self._frame_preview)
        self._layout.addWidget(self._options)
        self.setLayout(self._layout)

        self._options_layout = QHBoxLayout()
        self._options_layout.addWidget(self._frame_spinbox)
        self._options_layout.addWidget(self._frame_slider)
        self._options.setLayout(self._options_layout)

    def _sync_spinbox(self):
        """Synchronizes the frame spinbox with the range of the AdjustableRangeSlider"""
        self._frame_spinbox.setRange(self._frame_slider.range.min, self._frame_slider.range.max)

    def _on_frame_slider_change(self):
        """Ensures frame_slider and frame_spinbox hold the same value."""
        new_val = self._frame_slider.slider.value()

        self._frame_spinbox.setValue(new_val)
        self.set_frame(new_val)

    def _on_frame_spinbox_change(self):
        """Ensures frame_slider and frame_spinbox hold the same value."""
        new_val = self._frame_spinbox.value()

        self._frame_slider.slider.setValue(new_val)
        self.set_frame(new_val)

    def update_preview(self):
        """Sets the Pixmap of the frame_preview label to the currently selected frame."""
        self._video.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
        ret, frame = self._video.read()
        self._frame_preview.set_pixmap(misc.frame2pixmap(frame))

    @classmethod
    def is_supported_file(cls, path: str) -> bool:
        return os.path.splitext(path)[-1].lower() in cls.supported_video_ext

    def set_frame_range(self, start: int | float | None = None, stop: int | float | None = None):
        """
        Sets the frame index range that the user can access.

        Parameters
        ----------
        start : int, float, or None, optional
            the start or minimum frame that can be accessed by the user. If not provided, start = 0
        stop : int, float, or None, optional
            the stop or maximum frame that can be accessed by the user. If not provided, stop = the last frame index of
            the video.

        Raises
        ------
        ValueError
            A value error will be raised if start > stop or start < 0 or stop > the number of frames in the video
        """

        # creating a InclusiveInterval object will throw a ValueError if provided min > provided max
        new_range = misc.InclusiveInterval(start or 0, stop or self.get_largest_frame())

        self._frame_slider.set_range(*new_range)
        self._frame_spinbox.setRange(*new_range)

    def has_video(self) -> bool:
        """
        Checks if the VideoSkimmer has a video selected

        Returns
        -------
        bool
            True if a video has been selected; False otherwise
        """
        return self._video_path is not None and self._video is not None

    def set_video(self, video_path: str) -> None:
        """
        Sets the video for the VideoSkimmer to skim

        Parameters
        ----------
        video_path : str
            the path to the video file

        Raises
        ------
        FileNotFoundError
            if the provided video_path does not exist
        ValueError
            if the file type of the provided video is unsupported

        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"'{video_path}' does not exist!")

        if not self.is_supported_file(video_path):
            raise ValueError(f"Video is not of a known supported type. "
                             f"Current supported types are: {self.supported_video_ext}")

        self._video_path = video_path
        self._video = cv2.VideoCapture(video_path)

        self._total_frames = int(self._video.get(cv2.CAP_PROP_FRAME_COUNT))

        # if total frames == 0 here, then the selected video probably doesn't support cv2.CAP_PROP_FRAME_COUNT
        # thus, we must manually count the number of frames (which is really slow)
        if self._total_frames == 0:
            ret, = self._video.read()
            while ret:
                self._total_frames += 1
                ret, = self._video.read()

        # set ranges and range to [0, index of last frame]
        self._frame_slider.set_range_bounds(0, self.get_largest_frame())
        self.set_frame_range()
        self.set_frame(0)

    def in_frame_range(self, frame_num: int) -> bool:
        """Checks if frame_num fits within the current frame_range"""
        return self._frame_slider.range.contains(frame_num)

    def set_frame(self, frame_num: int, assume_closest: bool = True, autoupdate_preview: bool = True) -> None:
        """
        Sets the current frame of the video by frame index (or number). This method does nothing if a video has not been
        selected. (Use VideoSkimmer.has_video() to check if a video has been selected.)

        Parameters
        ----------
        frame_num : int
            the frame index/number to select
        assume_closest : bool, default True
            If True and frame_num is not in the frame range, frame_num will be forced to the closest value in the frame
            range. If False, then any frame_num outside the frame range will raise a ValueError
        autoupdate_preview : bool, default True
            If True, the newly-selected frame will automatically be shown in the GUI; if False, the shown frame will
            remain what it was until self.update_preview() is called.

        Raises
        ------
        ValueError
            if assume_closest is False and frame_num is not within the frame range
        """

        if not self.has_video():
            return

        if assume_closest:
            if frame_num < self._frame_slider.range.min:
                frame_num = self._frame_slider.range.min
            elif frame_num > self._frame_slider.range.max:
                frame_num = self._frame_slider.range.max
        elif not self._frame_slider.range.contains(frame_num):
            raise ValueError(f"When {assume_closest=}, provided frame_num must be within the inclusive range "
                             f"{self._frame_slider.range}.")

        self._current_frame = frame_num
        self._frame_spinbox.setValue(frame_num)

        if autoupdate_preview:
            self.update_preview()

    def next_frame(self, autoupdate_preview: bool = True) -> None:
        """
        Sets the current frame to the next frame if such a frame exists.

        Parameters
        ----------
        autoupdate_preview : bool, default True
            If True, the newly-selected frame will automatically be shown in the GUI; if False, the shown frame will
            remain what it was until self.update_preview() is called.
        """
        if not self.in_frame_range(self._current_frame + 1):
            return
        self.set_frame(self._current_frame + 1, autoupdate_preview=autoupdate_preview)

    def prev_frame(self, autoupdate_preview: bool = True) -> None:
        """
        Sets the current frame to the previous frame if such a frame exists.

        Parameters
        ----------
        autoupdate_preview : bool, default True
            If True, the newly-selected frame will automatically be shown in the GUI; if False, the shown frame will
            remain what it was until self.update_preview() is called.
        """
        if not self.in_frame_range(self._current_frame - 1):
            return
        self.set_frame(self._current_frame - 1, autoupdate_preview=autoupdate_preview)

    def get_largest_frame(self) -> int:
        return self._total_frames - 1
