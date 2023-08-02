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

        # absolute range are bounds for what range can be, since the user can adjust range manually
        self._range: misc.InclusiveInterval = misc.InclusiveInterval(0, 0)  # the bounds of the slider's range
        self._range_bounds: misc.InclusiveInterval = misc.InclusiveInterval(0, 0)  # absolute bounds for slider's range

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
        """Ensures new maximum value fits within range bounds and is smaller than the current max."""
        new_min = int(self.range_min_line_edit.text())

        # checks if new_min is invalid
        if new_min > self._range.max or not self._range_bounds.contains(new_min):
            self.range_min_line_edit.setText(str(self._range.min))  # reset to previous value
            return

        # if the function makes it here, new_min is valid -- update range and slider
        self._range.min = new_min
        self.slider.setRange(self._range.min, self._range.max)
        self.rangeChanged.emit()

    def _max_edited(self):
        """Ensures new maximum value fits within range bounds and is larger than the current min."""
        new_max = int(self.range_max_line_edit.text())

        # checks if new_max is invalid
        if new_max < self._range.min or not self._range_bounds.contains(new_max):
            self.range_max_line_edit.setText(str(self._range.max))
            return

        # if the function makes it here, new_max is valid -- update range and slider
        self._range.max = new_max
        self.slider.setRange(self._range.min, self._range.max)
        self.rangeChanged.emit()

    def _update_widgets(self):
        """Makes GUI elements congruent with programmatic values"""

        self.range_min_line_edit.setText(str(self._range.min))
        self.range_max_line_edit.setText(str(self._range.max))
        self.slider.setRange(self._range.min, self._range.max)

    @property
    def range(self):
        # returning a copy because user shouldn't be able to modify range outside provided method
        return self._range.copy()

    @property
    def range_bounds(self):
        return self._range_bounds.copy()

    def set_range(self, min_: int, max_: int | None = None, *, stretch_bounds: bool = False, emit: bool = True):
        """
        Sets the range of the slider.

        Parameters
        ----------
        min_ : int
            The minimum value of the slider
        max_ : int
            the maximum value of the slider
        stretch_bounds : bool, default False
            If True, the range boundaries will be stretched (changed) to fit range provided to this method.
        emit : bool
            Whether to emit the rangeChanged signal on the calling of this function

        Raises
        ------
        ValueError
            If provided min_ or max_ does not fit within self.max_range and stretch_absolutes=False

        """

        # raises a ValueError if min_ > max_
        new_range = misc.InclusiveInterval(min_, max_)

        if stretch_bounds:
            self._range = new_range # since we're stretching range_bounds, no special requirements for new_range
            self._range_bounds.normalize(self._range)  # change range_bounds to fit self._range
        elif self._range_bounds.contains(new_range):  # check if new max_ and min_ fits
            self._range = new_range
        else:  # not stretching range_bounds and new range do not fit within the absolute range
            raise ValueError(f"When {stretch_bounds=}, new range [{min_}, {max_}] must fit within absolute range "
                             f"{self._range_bounds}")

        if emit:
            self.rangeChanged.emit()

        self._update_widgets()

    def set_range_bounds(self, min_: int, max_: int, *, emit: bool = True):
        """
        Sets the absolute range that self.range must fit within. self.range is automatically normalized to the new
        range_bounds to guarantee it fits within them.

        Parameters
        ----------
        min_ : int
            The new minimum value of self.range_bounds
        max_ : int
            The new maximum value of self.range_bounds
        emit : bool
            Whether to emit the rangeChanged signal on the calling of this function (if the range is changed)

        Raises
        ------
        ValueError
            If min_ > max_

        """

        # will raise the error in the case stated above
        new_bounds = misc.InclusiveInterval(min_, max_)

        if new_bounds == self._range_bounds:
            return

        self._range_bounds = new_bounds
        self._range.normalize(self._range_bounds)

        if emit:
            self.rangeChanged.emit()

        self._update_widgets()
