from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QSizePolicy,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont

try:
    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    except ImportError:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class LayerPickerDialog(QDialog):
    def __init__(self, raster_layers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benchmark Layers")
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        title = QLabel("Select Layers to Benchmark")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QLabel(
            "Geomorphon and IPBA will run on each selected layer. "
            "Processing time scales with layer size."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.MultiSelection)
        self._layers = raster_layers
        for layer in raster_layers:
            provider = layer.dataProvider()
            w = provider.xSize()
            h = provider.ySize()
            item = QListWidgetItem(f"{layer.name()}  ({w}×{h})")
            item.setData(Qt.UserRole, layer)
            self._list.addItem(item)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def selected_layers(self):
        return [item.data(Qt.UserRole) for item in self._list.selectedItems()]


class BenchmarkOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benchmark Settings")
        self.setMinimumSize(340, 200)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        title = QLabel("IPBA Options")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        group = QGroupBox("Options")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._neighborhood = QComboBox()
        self._neighborhood.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._neighborhood.addItem("von Neumann")
        self._neighborhood.addItem("Moore")
        form.addRow(QLabel("Neighborhood"), self._neighborhood)

        self._projection = QComboBox()
        self._projection.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._projection.addItem("fixed")
        self._projection.addItem("spheric")
        form.addRow(QLabel("Projection"), self._projection)

        group.setLayout(form)
        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def neighborhood(self):
        text = self._neighborhood.currentText()
        return "von_neumann" if text.lower().startswith("von") else "moore"

    def projection(self):
        return 1 if self._projection.currentText().lower() == "fixed" else 0


class BenchmarkResultsDialog(QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benchmark Results")
        self.setMinimumSize(920, 540)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 8)

        if not results:
            layout.addWidget(QLabel("No benchmark results to display."))
            self._add_close(layout)
            self.setLayout(layout)
            return

        if not HAS_MATPLOTLIB:
            layout.addWidget(QLabel("matplotlib is not available — cannot display graphs."))
            self._add_close(layout)
            self.setLayout(layout)
            return

        sorted_results = sorted(results, key=lambda r: r["total_pixels"])
        labels = [f"{r['cols']}×{r['rows']}" for r in sorted_results]
        x = list(range(len(sorted_results)))

        geo_times = [r["geo_time"] for r in sorted_results]
        ipba_times = [r["ipba_time"] for r in sorted_results]
        total_times = [r["total_time"] for r in sorted_results]

        geo_rams = [r["geo_ram_mb"] for r in sorted_results]
        ipba_rams = [r["ipba_ram_mb"] for r in sorted_results]
        total_rams = [r["total_ram_mb"] for r in sorted_results]

        fig = Figure(figsize=(12, 5), tight_layout=True)

        ax1 = fig.add_subplot(1, 2, 1)
        ax1.plot(x, geo_times, "o-", label="Geomorphon", color="steelblue")
        ax1.plot(x, ipba_times, "s-", label="IPBA", color="darkorange")
        ax1.plot(x, total_times, "^-", label="Total", color="seagreen")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=30, ha="right")
        ax1.set_xlabel("Layer size (W×H)")
        ax1.set_ylabel("Time (s)")
        ax1.set_title("Processing Time")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.plot(x, geo_rams, "o-", label="Geomorphon", color="steelblue")
        ax2.plot(x, ipba_rams, "s-", label="IPBA", color="darkorange")
        ax2.plot(x, total_rams, "^-", label="Total", color="seagreen")
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=30, ha="right")
        ax2.set_xlabel("Layer size (W×H)")
        ax2.set_ylabel("Peak RAM (MB)")
        ax2.set_title("Memory Usage (Peak per Phase)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas)

        self._add_close(layout)
        self.setLayout(layout)

    def _add_close(self, layout):
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
