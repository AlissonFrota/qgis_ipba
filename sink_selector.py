from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QDialogButtonBox,
    QLabel,
    QComboBox,
    QRadioButton,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QSizePolicy,
    QButtonGroup,
    QWidget,
)
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer


class SinkSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Sink Layer")
        self.setMinimumSize(480, 360)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        title = QLabel("Drainage Basin Settings")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # ── Inputs group ─────────────────────────────────────────────────────
        input_group = QGroupBox("Inputs")
        input_layout = QVBoxLayout()
        input_layout.setSpacing(6)

        # Source radio buttons (mutually exclusive via QButtonGroup)
        self.source_group = QButtonGroup(self)

        # Option 1 – use an existing layer
        self.radio_layer = QRadioButton("Use sink layer")
        self.radio_layer.setChecked(True)
        self.source_group.addButton(self.radio_layer, 0)

        self.layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, (QgsRasterLayer, QgsVectorLayer))
        ]
        self.combo = QComboBox()
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for layer in self.layers:
            self.combo.addItem(layer.name())

        layer_sub = QWidget()
        layer_sub_layout = QHBoxLayout(layer_sub)
        layer_sub_layout.setContentsMargins(20, 0, 0, 0)
        layer_sub_layout.addWidget(QLabel("Layer:"))
        layer_sub_layout.addWidget(self.combo)

        # Option 2 – geomorphon auto-detection
        self.radio_geomorphon = QRadioButton("Detect sinks with geomorphons")
        self.source_group.addButton(self.radio_geomorphon, 1)

        # Option 3 – water-proximity detection
        self.radio_water = QRadioButton("Detect sinks by water proximity")
        self.source_group.addButton(self.radio_water, 2)

        water_sub = QWidget()
        water_sub_layout = QFormLayout(water_sub)
        water_sub_layout.setContentsMargins(20, 0, 0, 4)
        water_sub_layout.setHorizontalSpacing(12)
        water_sub_layout.setVerticalSpacing(6)

        self.water_value_spin = QDoubleSpinBox()
        self.water_value_spin.setRange(-1e9, 1e9)
        self.water_value_spin.setValue(0.0)
        self.water_value_spin.setDecimals(4)
        self.water_value_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.water_value_spin.setToolTip(
            "Pixel value that represents water (e.g. 0 for sea level). "
            "A cell touching this value becomes a sink."
        )

        self.border_sinks_check = QCheckBox("Include border sinks")
        self.border_sinks_check.setChecked(True)
        self.border_sinks_check.setToolTip(
            "Non-water cells on the raster edge are automatically treated as sinks. "
            "Each continuous edge segment (broken by water or corners) gets its own ID."
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

        self.shoreline_parts_spin = QSpinBox()
        self.shoreline_parts_spin.setRange(1, 1000000)
        self.shoreline_parts_spin.setValue(1)
        self.shoreline_parts_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.shoreline_parts_spin.setToolTip(
            "Cut each connected shoreline into this many equal-length arcs, each "
            "with its own id (ordered around the water body). 1 keeps the whole "
            "shoreline as a single id."
        )

        water_sub_layout.addRow(QLabel("Water value:"), self.water_value_spin)
        water_sub_layout.addRow(self.border_sinks_check)
        water_sub_layout.addRow(QLabel("Water bodies:"), self.water_bodies_spin)
        water_sub_layout.addRow(QLabel("Min sink size:"), self.min_sink_size_spin)
        water_sub_layout.addRow(QLabel("Shoreline parts:"), self.shoreline_parts_spin)

        input_layout.addWidget(self.radio_layer)
        input_layout.addWidget(layer_sub)
        input_layout.addWidget(self.radio_geomorphon)
        input_layout.addWidget(self.radio_water)
        input_layout.addWidget(water_sub)
        input_group.setLayout(input_layout)

        # ── Options group ─────────────────────────────────────────────────────
        self.neighborhood_combo = QComboBox()
        self.neighborhood_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.neighborhood_combo.addItem("von Neumann")
        self.neighborhood_combo.addItem("Moore")

        self.projection_combo = QComboBox()
        self.projection_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.projection_combo.addItem("fixed")
        self.projection_combo.addItem("spheric")

        options_group = QGroupBox("Options")
        options_form = QFormLayout()
        options_form.setLabelAlignment(Qt.AlignLeft)
        options_form.setFormAlignment(Qt.AlignTop)
        options_form.setHorizontalSpacing(12)
        options_form.setVerticalSpacing(8)
        options_form.addRow(QLabel("Neighborhood"), self.neighborhood_combo)
        options_form.addRow(QLabel("Projection"), self.projection_combo)
        options_group.setLayout(options_form)

        layout.addWidget(input_group)
        layout.addWidget(options_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.source_group.buttonClicked.connect(self._update_controls)
        self._update_controls()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _update_controls(self):
        is_layer = self.radio_layer.isChecked()
        is_water = self.radio_water.isChecked()
        self.combo.setEnabled(is_layer)
        self.water_value_spin.setEnabled(is_water)
        self.border_sinks_check.setEnabled(is_water)
        self.water_bodies_spin.setEnabled(is_water)
        self.min_sink_size_spin.setEnabled(is_water)
        self.shoreline_parts_spin.setEnabled(is_water)

    # ── Public accessors ──────────────────────────────────────────────────────

    def selected_layer(self):
        if self.layers and self.combo.currentIndex() >= 0:
            return self.layers[self.combo.currentIndex()]
        return None

    def use_geomorphon_sinks(self) -> bool:
        return self.radio_geomorphon.isChecked()

    def use_water_sinks(self) -> bool:
        return self.radio_water.isChecked()

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

    def selected_neighborhood(self) -> str:
        text = self.neighborhood_combo.currentText()
        return "von_neumann" if text.lower().startswith("von") else "moore"

    def selected_projection(self):
        text = self.projection_combo.currentText().lower()
        return 1 if text == "fixed" else 0
