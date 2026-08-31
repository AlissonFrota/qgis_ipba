from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QDialogButtonBox,
    QLabel,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QSizePolicy,
)
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtCore import Qt


class GenerateSinksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Sinks")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        title = QLabel("Generate Sinks Settings")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.use_defaults_checkbox = QCheckBox("Use default options")
        self.use_defaults_checkbox.setChecked(True)
        layout.addWidget(self.use_defaults_checkbox)

        params_group = QGroupBox("Parameters")
        params_form = QFormLayout()
        params_form.setLabelAlignment(Qt.AlignLeft)
        params_form.setHorizontalSpacing(12)
        params_form.setVerticalSpacing(8)

        self.search_distance_spin = QSpinBox()
        self.search_distance_spin.setRange(1, 10000)
        self.search_distance_spin.setValue(20)
        self.search_distance_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.angle_threshold_spin = QSpinBox()
        self.angle_threshold_spin.setRange(0, 360)
        self.angle_threshold_spin.setValue(1)
        self.angle_threshold_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        params_form.addRow(QLabel("Search distance"), self.search_distance_spin)
        params_form.addRow(QLabel("Angle threshold"), self.angle_threshold_spin)
        params_group.setLayout(params_form)
        layout.addWidget(params_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.use_defaults_checkbox.stateChanged.connect(self._toggle_params)
        self._toggle_params()

    def _toggle_params(self):
        enabled = not self.use_defaults_checkbox.isChecked()
        self.search_distance_spin.setEnabled(enabled)
        self.angle_threshold_spin.setEnabled(enabled)

    def search_distance(self) -> int:
        return self.search_distance_spin.value()

    def angle_threshold(self) -> int:
        return self.angle_threshold_spin.value()


class GenerateWaterSinksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Water-Proximity Sinks")
        self.setMinimumWidth(320)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        title = QLabel("Water-Proximity Sink Settings")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        params_group = QGroupBox("Parameters")
        params_form = QFormLayout()
        params_form.setLabelAlignment(Qt.AlignLeft)
        params_form.setHorizontalSpacing(12)
        params_form.setVerticalSpacing(8)

        self.water_value_spin = QDoubleSpinBox()
        self.water_value_spin.setRange(-1e9, 1e9)
        self.water_value_spin.setValue(0.0)
        self.water_value_spin.setDecimals(4)
        self.water_value_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.water_value_spin.setToolTip(
            "Pixel value that identifies water (e.g. 0 for sea level). "
            "Land cells touching this value become sinks."
        )

        self.border_sinks_check = QCheckBox("Include border sinks")
        self.border_sinks_check.setChecked(True)
        self.border_sinks_check.setToolTip(
            "Non-water cells on the raster edge are automatically treated as sinks. "
            "Each continuous edge segment (broken by water, NaN, or corners) gets its own ID."
        )

        self.water_bodies_spin = QSpinBox()
        self.water_bodies_spin.setRange(1, 1000000)
        self.water_bodies_spin.setValue(1)
        self.water_bodies_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.water_bodies_spin.setToolTip(
            "How many water bodies (largest first) count as the sea and elect "
            "coastline sinks. Interior lakes are always excluded. Raise this when "
            "an island touches the raster border and splits the sea into pieces, "
            "so the coast is sunk all the way around."
        )

        self.min_sink_size_spin = QSpinBox()
        self.min_sink_size_spin.setRange(0, 1000000)
        self.min_sink_size_spin.setValue(10)
        self.min_sink_size_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.min_sink_size_spin.setToolTip(
            "Discard water-sink groups smaller than this many cells. "
            "Removes the tiny clusters that ring small offshore islands. "
            "0 keeps every group."
        )

        self.shoreline_parts_spin = QSpinBox()
        self.shoreline_parts_spin.setRange(1, 1000000)
        self.shoreline_parts_spin.setValue(1)
        self.shoreline_parts_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.shoreline_parts_spin.setToolTip(
            "Cut each connected shoreline into this many equal-length arcs, each "
            "with its own id (ordered around the water body). 1 keeps the whole "
            "shoreline as a single id."
        )

        params_form.addRow(QLabel("Water value:"), self.water_value_spin)
        params_form.addRow(self.border_sinks_check)
        params_form.addRow(QLabel("Water bodies:"), self.water_bodies_spin)
        params_form.addRow(QLabel("Min sink size:"), self.min_sink_size_spin)
        params_form.addRow(QLabel("Shoreline parts:"), self.shoreline_parts_spin)
        params_group.setLayout(params_form)
        layout.addWidget(params_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def water_value(self) -> float:
        return self.water_value_spin.value()

    def include_border_sinks(self) -> bool:
        return self.border_sinks_check.isChecked()

    def min_sink_size(self) -> int:
        return self.min_sink_size_spin.value()

    def n_water_bodies(self) -> int:
        return self.water_bodies_spin.value()

    def shoreline_parts(self) -> int:
        return self.shoreline_parts_spin.value()
