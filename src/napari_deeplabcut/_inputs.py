from __future__ import annotations

import qtpy.QtWidgets as Widgets
from qtpy.QtCore import Qt, Signal
import qtpy.QtGui as Gui

from napari_deeplabcut import misc


def _is_int(string: str) -> bool:
    """
    Checks if string represents and integer. "Integer," in this case, does not necessarily mean "can be cast to an int
    object without causing errors" since cases like string="10.0" will return False. This function only returns true
    if the provided string is an int represented as an integer without modification.

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
    """A validator that correctly validates all integers, regardless of size."""

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

    rangeChanged = Signal()

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
        """Ensures new maximum value fits within absolute limits and is smaller than the current max."""
        new_min = int(self.range_min_line_edit.text())

        # checks if new_min is invalid
        if new_min > self._limits.max or not self._absolute_limits.contains(new_min):
            self.range_min_line_edit.setText(str(self._limits.min))  # reset to previous value
            return

        # if the function makes it here, new_min is valid -- update limits and slider
        self._limits.min = new_min
        self.slider.setRange(self._limits.min, self._limits.max)
        self.rangeChanged.emit()

    def _max_edited(self):
        """Ensures new maximum value fits within absolute limits and is larger than the current min."""
        new_max = int(self.range_max_line_edit.text())

        # checks if new_max is invalid
        if new_max < self._limits.min or not self._absolute_limits.contains(new_max):
            self.range_max_line_edit.setText(str(self._limits.max))
            return

        # if the function makes it here, new_max is valid -- update limits and slider
        self._limits.max = new_max
        self.slider.setRange(self._limits.min, self._limits.max)
        self.rangeChanged.emit()

    def _update_widgets(self):
        """Makes GUI elements congruent with programmatic values"""

        self.range_min_line_edit.setText(str(self._limits.min))
        self.range_max_line_edit.setText(str(self._limits.max))
        self.slider.setRange(self._limits.min, self._limits.max)

    @property
    def limits(self):
        return self._limits.copy()  # returning a copy because user shouldn't be able to directly modify limits

    @property
    def absolutes(self):
        return self._absolute_limits.copy()

    def set_limits(self, min_: int, max_: int, stretch_absolutes: bool = False, emit: bool = True):
        """
        Sets the limits of the slider.

        Parameters
        ----------
        min_ : int
            The minimum value of the slider
        max_ : int
            the maximum value of the slider
        stretch_absolutes : bool, default False
            If True, absolute limits will be stretched (changed) to fit limits provided to this method.
        emit : bool
            Whether to emit the rangeChanged signal on the calling of this function

        Raises
        ------
        ValueError
            If provided min_ or max_ does not fit within self.absolutes and stretch_absolutes=False

        """

        if stretch_absolutes:
            self._limits.set(min_, max_)  # since we're stretching absolutes, provided min_ and max_ will be limits
            self._absolute_limits.normalize(self._limits)  # change absolutes to fit self._limits
        elif self._absolute_limits.contains(misc.Limits(min_, max_)):
            # not stretching absolutes, so must check if new max_ and min_ fits
            self._limits.set(min_, max_)
        else:  # not stretching absolutes and new limits do not fit within the absolute limits
            raise ValueError(f"When {stretch_absolutes=}, new limits [{min_}, {max_}] must fit within absolute limits "
                             f"{self._absolute_limits}")

        if emit:
            self.rangeChanged.emit()

        self._update_widgets()

    def set_absolutes(self, min_: int, max_: int, emit: bool = True):
        """
        Sets the absolute limits that self.limits must fit within. self.limits is automatically normalized to the new
        absolutes to guarantee it fits within them.

        Parameters
        ----------
        min_ : int
            The new minimum value of self.absolutes
        max_ : int
            The new maximum value of self.absolutes
        emit : bool
            Whether to emit the rangeChanged signal on the calling of this function

        """
        self._absolute_limits.set(min_, max_)
        self._limits.normalize(self._absolute_limits)

        self.rangeChanged.emit()
        self._update_widgets()
