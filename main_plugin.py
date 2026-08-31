import os
import tempfile
import uuid

from qgis.PyQt.QtWidgets import QAction, QApplication, QFileDialog, QInputDialog
from qgis.core import QgsRasterLayer, QgsProject, QgsVectorLayer, QgsDefaultValue
from .sink_selector import SinkSelectorDialog
from .generate_sinks_dialog import GenerateSinksDialog, GenerateWaterSinksDialog
from .lib.io import raster_layer_to_numpy, numpy_to_geotiff, vector_layer_to_raster, read_band_raw
from .lib.percolation_tools.lattice import Lattice
from .lib.percolation_tools.invasion_percolation import IPBA
from .lib.data_prep import convert_array_to_dict
import numpy as np


class IPBAPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.generate_sinks_action = None
        self.generate_water_sinks_action = None
        self.vector_to_raster_action = None
        self.create_line_layer_action = None
        self.benchmark_action = None

    def initGui(self):
        self.action = QAction("Find Drainage Basins", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&IPBA", self.action)

        self.generate_sinks_action = QAction("Generate Sinks", self.iface.mainWindow())
        self.generate_sinks_action.triggered.connect(self.generate_sinks)
        self.iface.addPluginToMenu("&IPBA", self.generate_sinks_action)

        self.generate_water_sinks_action = QAction("Generate Water-Proximity Sinks", self.iface.mainWindow())
        self.generate_water_sinks_action.triggered.connect(self.generate_water_sinks)
        self.iface.addPluginToMenu("&IPBA", self.generate_water_sinks_action)

        self.vector_to_raster_action = QAction("Vector Layer to Raster", self.iface.mainWindow())
        self.vector_to_raster_action.triggered.connect(self.vector_layer_to_raster_action)
        self.iface.addPluginToMenu("&IPBA", self.vector_to_raster_action)

        self.create_line_layer_action = QAction("Create Line Drawing Layer", self.iface.mainWindow())
        self.create_line_layer_action.triggered.connect(self.create_line_drawing_layer)
        self.iface.addPluginToMenu("&IPBA", self.create_line_layer_action)

        self.benchmark_action = QAction("Benchmark Layers", self.iface.mainWindow())
        self.benchmark_action.triggered.connect(self.run_benchmark)
        self.iface.addPluginToMenu("&IPBA", self.benchmark_action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&IPBA", self.action)
        if self.generate_sinks_action:
            self.iface.removePluginMenu("&IPBA", self.generate_sinks_action)
        if self.generate_water_sinks_action:
            self.iface.removePluginMenu("&IPBA", self.generate_water_sinks_action)
        if self.vector_to_raster_action:
            self.iface.removePluginMenu("&IPBA", self.vector_to_raster_action)
        if self.create_line_layer_action:
            self.iface.removePluginMenu("&IPBA", self.create_line_layer_action)
        if self.benchmark_action:
            self.iface.removePluginMenu("&IPBA", self.benchmark_action)

    def _choose_layer(self, layers, title, label):
        names = [layer.name() for layer in layers]
        if not names:
            return None

        selected_name, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            title,
            label,
            names,
            0,
            False,
        )

        if not ok:
            return None

        return layers[names.index(selected_name)]

    def generate_sinks(self):
        dem_layer = self.iface.activeLayer()
        if not isinstance(dem_layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning("IPBA", "Please select a DEM raster layer.")
            return

        dialog = GenerateSinksDialog(self.iface.mainWindow())
        if not dialog.exec_():
            return

        dem_array, _, _ = raster_layer_to_numpy(dem_layer)
        nodata = dem_layer.dataProvider().sourceNoDataValue(1)
        if nodata is not None:
            dem_array = np.where(np.isclose(dem_array, nodata), np.nan, dem_array)

        try:
            from .lib.identification import find_sinks_raster
            sinks_array, _ = find_sinks_raster(
                dem_array,
                search_distance=dialog.search_distance(),
                angle_threshold=dialog.angle_threshold(),
            )
        except Exception as exc:
            self.iface.messageBar().pushCritical("IPBA", f"Sink generation failed: {exc}")
            return

        if not np.any(sinks_array > 0):
            self.iface.messageBar().pushWarning("IPBA", "No sinks were found.")
            return

        output_base = os.path.join(tempfile.gettempdir(), f"ipba_sinks_{uuid.uuid4().hex}")
        numpy_to_geotiff(sinks_array[1:-1, 1:-1], output_base, dem_layer)

        sinks_layer = QgsRasterLayer(f"{output_base}.tif", f"{dem_layer.name()}_sinks")
        if not sinks_layer.isValid():
            self.iface.messageBar().pushCritical("IPBA", "Generated sinks raster is invalid.")
            return

        QgsProject.instance().addMapLayer(sinks_layer)

    def generate_water_sinks(self):
        dem_layer = self.iface.activeLayer()
        if not isinstance(dem_layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning("IPBA", "Please select a DEM raster layer.")
            return

        dialog = GenerateWaterSinksDialog(self.iface.mainWindow())
        if not dialog.exec_():
            return

        # Read the RAW band, exactly like the reference notebook's
        # ``rasterio.open(...).read(1)``. Do NOT use raster_layer_to_numpy
        # (injects noise + rewrites nodata to NaN) nor as_numpy(use_masking=True)
        # (rewrites nodata to NaN); either corrupts value-based water detection.
        raw_dem = read_band_raw(dem_layer)
        dem_nodata = dem_layer.dataProvider().sourceNoDataValue(1)

        try:
            from .lib.identification import find_sinks_water_adjacent
            sinks_array = find_sinks_water_adjacent(
                raw_dem,
                water_value=dialog.water_value(),
                use_border_sinks=dialog.include_border_sinks(),
                min_sink_size=dialog.min_sink_size(),
                shoreline_parts=dialog.shoreline_parts(),
                n_water_bodies=dialog.n_water_bodies(),
                nodata=dem_nodata,
            )
        except Exception as exc:
            self.iface.messageBar().pushCritical("IPBA", f"Water-proximity sink generation failed: {exc}")
            return

        if not np.any(sinks_array > 0):
            self.iface.messageBar().pushWarning("IPBA", "No sinks were found.")
            return

        output_base = os.path.join(tempfile.gettempdir(), f"ipba_water_sinks_{uuid.uuid4().hex}")
        numpy_to_geotiff(sinks_array, output_base, dem_layer)

        sinks_layer = QgsRasterLayer(f"{output_base}.tif", f"{dem_layer.name()}_water_sinks")
        if not sinks_layer.isValid():
            self.iface.messageBar().pushCritical("IPBA", "Generated water sinks raster is invalid.")
            return

        QgsProject.instance().addMapLayer(sinks_layer)

    def vector_layer_to_raster_action(self):
        vector_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, QgsVectorLayer)
        ]
        dem_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, QgsRasterLayer)
        ]

        if not vector_layers:
            self.iface.messageBar().pushWarning("IPBA", "No vector layers available.")
            return

        if not dem_layers:
            self.iface.messageBar().pushWarning("IPBA", "No DEM raster layers available.")
            return

        vector_layer = self._choose_layer(
            vector_layers,
            "Vector Layer to Raster",
            "Select vector layer:",
        )
        if vector_layer is None:
            return

        dem_layer = self._choose_layer(
            dem_layers,
            "Vector Layer to Raster",
            "Select DEM layer:",
        )
        if dem_layer is None:
            return

        try:
            out_raster = vector_layer_to_raster(vector_layer, dem_layer)
        except Exception as exc:
            self.iface.messageBar().pushCritical("IPBA", f"Rasterization failed: {exc}")
            return

        QgsProject.instance().addMapLayer(out_raster)

    def create_line_drawing_layer(self):
        source_layer = self.iface.activeLayer()
        if source_layer is None:
            self.iface.messageBar().pushWarning("IPBA", "No layer selected. Select a layer first.")
            return

        crs_authid = source_layer.crs().authid()
        layer = QgsVectorLayer(
            f"LineString?crs={crs_authid}&field=id:integer",
            "Line Drawing",
            "memory",
        )

        if not layer.isValid():
            self.iface.messageBar().pushCritical("IPBA", "Failed to create line drawing layer.")
            return

        field_idx = layer.fields().indexOf("id")
        layer.setDefaultValueDefinition(
            field_idx,
            QgsDefaultValue('if(maximum("id") is null, 1, maximum("id") + 1)'),
        )

        QgsProject.instance().addMapLayer(layer)
        self.iface.setActiveLayer(layer)
        layer.startEditing()

        self.iface.messageBar().pushSuccess(
            "IPBA",
            f'Line drawing layer created (CRS: {crs_authid}). Draw lines — "id" auto-increments.',
        )

    def run(self):
        dem_layer = self.iface.activeLayer()
        if not isinstance(dem_layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning("IPBA", "Please select a DEM raster layer.")
            return

        arr, nrows, ncols = raster_layer_to_numpy(dem_layer)

        dem_for_sink_detection = arr.copy()
        
        dialog = SinkSelectorDialog(self.iface.mainWindow())
        if not dialog.exec_():
            return

        neighborhood = dialog.selected_neighborhood()
        projection = dialog.selected_projection()

        if dialog.use_geomorphon_sinks():
            try:
                from .lib.identification import find_sinks_raster
                sinks_array, _ = find_sinks_raster(dem_for_sink_detection)
                sinks_array = sinks_array[1:-1, 1:-1]
            except Exception as exc:
                self.iface.messageBar().pushCritical(
                    "IPBA",
                    f"Geomorphon sink detection failed: {exc}"
                )
                return
            sink_nodata = 0
        elif dialog.use_water_sinks():
            try:
                from .lib.identification import find_sinks_water_adjacent
                # Water detection is value-based and must match the reference
                # notebook, so feed it the RAW band (like rasterio.read(1)),
                # not the noise-injected / nodata-masked loader output.
                raw_dem = read_band_raw(dem_layer)
                dem_nodata = dem_layer.dataProvider().sourceNoDataValue(1)
                sinks_array = find_sinks_water_adjacent(
                    raw_dem,
                    water_value=dialog.water_value(),
                    use_border_sinks=dialog.include_border_sinks(),
                    min_sink_size=dialog.min_sink_size(),
                    shoreline_parts=dialog.shoreline_parts(),
                    n_water_bodies=dialog.n_water_bodies(),
                    nodata=dem_nodata,
                )
            except Exception as exc:
                self.iface.messageBar().pushCritical(
                    "IPBA",
                    f"Water-proximity sink detection failed: {exc}"
                )
                return
            sink_nodata = 0
        else:
            sink_layer = dialog.selected_layer()
            if sink_layer is None:
                self.iface.messageBar().pushWarning("IPBA", "No sink layer selected.")
                return
            if isinstance(sink_layer, QgsVectorLayer):
                sink_layer = vector_layer_to_raster(sink_layer, dem_layer)

            sinks_array, _, _ = raster_layer_to_numpy(sink_layer)
            sinks_array = sinks_array[1:-1, 1:-1]
            sink_nodata = sink_layer.dataProvider().sourceNoDataValue(1)

        sinks = convert_array_to_dict(sinks_array, sink_nodata)
        if not sinks:
            self.iface.messageBar().pushWarning("IPBA", "No sinks were found.")
            return
        
        heights = arr.flatten()

        lattice = Lattice(nrows, ncols)
        IPBA(lattice, heights, sinks, ntype=neighborhood, projection=projection)
        lattice.set_labels_sinks()
        result = lattice.label_sinks

        out_path, _ = QFileDialog.getSaveFileName(None, "Save basins", "", "GeoTIFF (*.tif)")
        if out_path:
            numpy_to_geotiff(
                result[1:lattice.nrows - 1, 1:lattice.ncols - 1],
                out_path,
                dem_layer
            )

            new_layer = QgsRasterLayer("{}.tif".format(out_path), "Basins")
            QgsProject.instance().addMapLayer(new_layer)

    def run_benchmark(self):
        import tracemalloc
        import time
        from .benchmark_dialog import LayerPickerDialog, BenchmarkOptionsDialog, BenchmarkResultsDialog
        from .lib.identification import find_sinks_raster

        raster_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, QgsRasterLayer)
        ]

        if not raster_layers:
            self.iface.messageBar().pushWarning("IPBA", "No raster layers in project.")
            return

        picker = LayerPickerDialog(raster_layers, self.iface.mainWindow())
        if not picker.exec_():
            return

        selected = picker.selected_layers()
        if not selected:
            self.iface.messageBar().pushWarning("IPBA", "No layers selected.")
            return

        options = BenchmarkOptionsDialog(self.iface.mainWindow())
        if not options.exec_():
            return

        ntype = options.neighborhood()
        projection = options.projection()

        results = []

        for layer in selected:
            provider = layer.dataProvider()
            cols = provider.xSize()
            rows = provider.ySize()

            self.iface.messageBar().pushInfo(
                "IPBA", f"Benchmarking {layer.name()} ({cols}×{rows})…"
            )
            QApplication.processEvents()

            try:
                arr, nrows, ncols = raster_layer_to_numpy(layer)
            except Exception as exc:
                self.iface.messageBar().pushCritical(
                    "IPBA", f"Failed to load {layer.name()}: {exc}"
                )
                continue

            # --- Geomorphon ---
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            tracemalloc.start()
            t0 = time.perf_counter()
            try:
                sinks_array, _ = find_sinks_raster(arr)
                sinks_array = sinks_array[1:-1, 1:-1]
            except Exception as exc:
                tracemalloc.stop()
                self.iface.messageBar().pushCritical(
                    "IPBA", f"Geomorphon failed for {layer.name()}: {exc}"
                )
                continue
            t1 = time.perf_counter()
            _, geo_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            geo_time = t1 - t0
            geo_ram_mb = geo_peak / 1024 / 1024

            # --- IPBA ---
            sinks = convert_array_to_dict(sinks_array, 0)
            if not sinks:
                self.iface.messageBar().pushWarning(
                    "IPBA", f"No sinks found for {layer.name()}, skipping."
                )
                continue

            if tracemalloc.is_tracing():
                tracemalloc.stop()
            tracemalloc.start()
            t2 = time.perf_counter()
            try:
                lattice = Lattice(nrows, ncols)
                IPBA(lattice, arr.flatten(), sinks, ntype=ntype, projection=projection)
                lattice.set_labels_sinks()
            except Exception as exc:
                tracemalloc.stop()
                self.iface.messageBar().pushCritical(
                    "IPBA", f"IPBA failed for {layer.name()}: {exc}"
                )
                continue
            t3 = time.perf_counter()
            _, ipba_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            ipba_time = t3 - t2
            ipba_ram_mb = ipba_peak / 1024 / 1024

            results.append({
                "name": layer.name(),
                "rows": rows,
                "cols": cols,
                "total_pixels": rows * cols,
                "geo_time": geo_time,
                "geo_ram_mb": geo_ram_mb,
                "ipba_time": ipba_time,
                "ipba_ram_mb": ipba_ram_mb,
                "total_time": geo_time + ipba_time,
                "total_ram_mb": geo_ram_mb + ipba_ram_mb,
            })

        if not results:
            self.iface.messageBar().pushWarning(
                "IPBA", "No layers were successfully benchmarked."
            )
            return

        BenchmarkResultsDialog(results, self.iface.mainWindow()).exec_()
