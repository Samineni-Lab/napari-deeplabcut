from __future__ import annotations

import qtpy.QtWidgets as Widgets
from qtpy.QtCore import Qt
import qtpy.QtGui as Gui

from typing import Callable

from napari_deeplabcut import misc


def _is_int(string: str) -> bool:
    """
    Checks if string represents and integer. "Integer, in this case, does not necessarily mean "can be cast to an int
    object without causing errors" since cases like string="10.0" will return False. This function only returns true
    if the provided string is an int without modification.

    Parameters
    ----------
    string : str
        the string to be checked

    Returns
    -------
    bool
        True if string represents an int, False otherwise
    """
    if string.startswith(('+', '-')):
        return string[1:].isdigit()
    return string.isdigit()


class PyIntValidator(Gui.QValidator):

    def __init__(self, parent: Widgets.QWidget):
        super().__init__(parent)

    def validate(self, input_: str, pos: int) -> object:
        state = Gui.QValidator.Invalid
        if input_ in ('', '+', '-'):
            state = Gui.QValidator.Intermediate
        elif _is_int(input_):
            state = Gui.QValidator.Acceptable

        return state, input_, pos


class AdjustableRangeSlider(Widgets.QWidget):

    def __init__(self, orientation: Qt.Orientation, parent: Widgets.QWidget):
        super().__init__(parent)

        # Attributes

        # absolute limits are bounds for what limits can be, since the user can adjust limits manually
        self._limits: misc.Limits = misc.Limits(0, 0)  # the bounds of the slider's range
        self._absolute_limits: misc.Limits = misc.Limits(0, 0)  # absolute bounds for slider's range

        # Widgets

        self.slider = Widgets.QSlider(orientation, self)
        self.range_min_line_edit = Widgets.QLineEdit('0', self)
        self.range_max_line_edit = Widgets.QLineEdit('0', self)

        self.range_min_line_edit.setValidator(PyIntValidator(self))
        self.range_max_line_edit.setValidator(PyIntValidator(self))
        self.range_min_line_edit.setFixedWidth(60)
        self.range_max_line_edit.setFixedWidth(60)

        self.range_min_line_edit.editingFinished.connect(self._min_edited)
        self.range_max_line_edit.editingFinished.connect(self._max_edited)

        # Layout

        if orientation == Qt.Orientation.Horizontal:
            self._layout = Widgets.QHBoxLayout(self)
        else:
            self._layout = Widgets.QVBoxLayout(self)

        self._layout.addWidget(self.range_min_line_edit)
        self._layout.addWidget(self.slider)
        self._layout.addWidget(self.range_max_line_edit)
        self.setLayout(self._layout)

    def _min_edited(self):
        new_min = int(self.range_min_line_edit.text())

        if new_min > self._limits.max or not self._absolute_limits.contains(new_min):
            self.range_min_line_edit.setText(str(self._limits.min))
            return

        self._limits.min = new_min
        self.slider.setRange(self._limits.min, self._limits.max)

    def _max_edited(self):
        new_max = int(self.range_max_line_edit.text())

        if new_max < self._limits.min or not self._absolute_limits.contains(new_max):
            self.range_max_line_edit.setText(str(self._limits.max))
            return

        self._limits.max = new_max
        self.slider.setRange(self._limits.min, self._limits.max)

    def _update_widgets(self):
        self.range_min_line_edit.setText(str(self._limits.min))
        self.range_max_line_edit.setText(str(self._limits.max))
        self.slider.setRange(self._limits.min, self._limits.max)

    @property
    def limits(self):
        return self._limits.copy()  # returning a copy because user shouldn't be able to directly modify limits

    @property
    def absolutes(self):
        return self._absolute_limits.copy()

    def set_limits(self, min_: int, max_: int, stretch_absolutes: bool = False):
        if stretch_absolutes:
            self._limits.set(min_, max_)
            self._absolute_limits.normalize(self._limits)
        elif self._absolute_limits.contains(misc.Limits(min_, max_)):
            self._limits.set(min_, max_)
        else:
            raise ValueError(f"When {stretch_absolutes=}, new limits [{min_}, {max_}] must fit within absolute limits "
                             f"{self._absolute_limits}")

        self._update_widgets()

    def set_absolutes(self, min_: int, max_: int):
        self._absolute_limits.set(min_, max_)
        self._limits.normalize(self._absolute_limits)

        self._update_widgets()

