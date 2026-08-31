---
layout: default
title: IPBA QGIS Plugin
description: Invasion Percolation-Based Algorithm for drainage basin delineation
---

# IPBA — Invasion Percolation-Based Algorithm

> A QGIS plugin for automatic delineation of multiple drainage basins from Digital Elevation Models (DEMs).

**Version:** 1.0  
**QGIS Minimum Version:** 3.4  
**Author:** Alisson Frota  
**Repository:** [github.com/AlissonFrota/ipba_qgis_plugin](https://github.com/AlissonFrota/ipba_qgis_plugin)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
  - [Find Drainage Basins](#find-drainage-basins)
  - [Generate Sinks](#generate-sinks)
  - [Vector Layer to Raster](#vector-layer-to-raster)
- [Configuration Options](#configuration-options)
- [Architecture](#architecture)
- [Dependencies](#dependencies)
- [Building the Geomorphon Library](#building-the-geomorphon-library)
- [Contributing](#contributing)
- [Contact](#contact)

---

## Overview

The **IPBA plugin** implements an extension of the *Invasion Percolation-Based Algorithm* to delineate multiple drainage basins directly within QGIS. Given a Digital Elevation Model (DEM) and a set of sink points (depressions or outlets), the algorithm traces which area of terrain drains into each sink — producing a labeled raster where every pixel belongs to exactly one drainage basin.

Sinks can be provided as an existing vector or raster layer, or automatically detected from the DEM itself using **geomorphon** terrain classification.

---

## Features

| Feature | Description |
|---|---|
| Drainage basin delineation | Labels every DEM cell with its corresponding basin ID |
| Automatic sink detection | Uses geomorphon classification to find surface depressions |
| Custom sink layer support | Accepts user-provided vector or raster sink layers |
| Neighborhood types | Von Neumann (4-cell) or Moore (8-cell) connectivity |
| Projection modes | Fixed (flat) or Spheric (polar-wrap) boundary conditions |
| Vector-to-raster conversion | Converts vector layers to raster aligned with DEM resolution |
| C++ acceleration | Geomorphon classification compiled with OpenMP parallelization |
| GeoTIFF output | Preserves original coordinate reference system and spatial metadata |

---

## How It Works

### Invasion Percolation

Invasion percolation is a physical simulation of a fluid invading a porous medium. In the hydrological context, the algorithm simulates water flowing from any given cell downhill until it reaches a sink (a local depression or outlet). The core steps are:

1. **Initialization** — Each cell on the DEM lattice is assigned its elevation value. Sink cells are labeled with a basin ID.
2. **Percolation** — For every unlabeled cell, the algorithm performs an invasion percolation: starting from that cell, it follows the path of least resistance (lowest neighboring elevation) using a min-heap priority queue.
3. **Basin assignment** — When the percolation path reaches a labeled sink, all cells along the path are assigned that sink's basin ID.
4. **Termination** — The process repeats until all cells have been assigned to a basin.

This bottom-up approach ensures that the resulting basins respect the full topological complexity of the DEM without requiring pit-filling preprocessing.

### Geomorphon Sink Detection

When no sink layer is provided, the plugin uses **geomorphon** classification to automatically identify surface depressions:

1. The DEM is smoothed with a Gaussian blur and a delta weight is applied.
2. Zenith angles are computed in 8 cardinal and intercardinal directions within a configurable search radius.
3. The resulting pattern is matched against a 9×9 geomorphon lookup table to classify each cell (valley, ridge, flat, etc.).
4. Valley cells (geomorph ≤ 1) are isolated, small clusters are filtered out, and centerlines are extracted via skeletonization.
5. Each connected centerline segment is assigned a unique sink ID.

---

## Installation

### 1. Download the plugin

```bash
git clone https://github.com/AlissonFrota/ipba_qgis_plugin.git
```

### 2. Copy to QGIS plugins directory

Copy the `ipba_qgis_plugin` folder to your QGIS user plugins directory:

| Operating System | Plugins Directory |
|---|---|
| Linux | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |
| macOS | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |
| Windows | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\` |

### 3. Install Python dependencies

The plugin requires **numpy**, **scipy**, **scikit-image**, and **GDAL**. Install them into QGIS's Python environment or via the provided script:

```bash
bash venv.sh
```

Or manually:

```bash
pip install numpy scipy scikit-image
pip install gdal[numpy]
```

> **Note:** On Windows, it is recommended to install GDAL via the [OSGeo4W](https://trac.osgeo.org/osgeo4w/) installer, which ships with QGIS.

### 4. Enable the plugin in QGIS

1. Open QGIS.
2. Go to **Plugins → Manage and Install Plugins**.
3. Search for **IPBA**.
4. Check the box to enable it.

The plugin will appear under the **Plugins** menu and as a toolbar button.

---

## Usage

### Find Drainage Basins

This is the main function of the plugin. It delineates drainage basins from a DEM.

**Steps:**

1. Load a DEM raster layer into QGIS and make it the active layer.
2. Click **Plugins → IPBA → Find Drainage Basins** (or the toolbar icon).
3. The configuration dialog will open:
   - Choose a **sink layer** from the dropdown, or check **Use Geomorphons** to auto-detect sinks.
   - Select the **neighborhood type** (Von Neumann or Moore).
   - Select the **projection** (Fixed or Spheric).
4. Click **OK**.
5. Choose a location to save the output GeoTIFF.
6. The result is loaded automatically into QGIS as a new layer.

**Output:** A single-band GeoTIFF raster where each pixel value is an integer basin ID. Pixels with the same value belong to the same drainage basin.

---

### Generate Sinks

Automatically detects sink locations from the active DEM layer using geomorphon terrain classification and saves them as a raster.

**Steps:**

1. Make the DEM raster layer active in QGIS.
2. Click **Plugins → IPBA → Generate Sinks**.
3. Choose a location to save the output GeoTIFF.
4. The sink raster is loaded automatically into QGIS.

This tool is useful for inspecting sink locations before running the full basin delineation.

---

### Vector Layer to Raster

Converts a vector layer (points, lines, or polygons) into a raster aligned with the active DEM layer.

**Steps:**

1. Make the DEM raster layer active in QGIS.
2. Click **Plugins → IPBA → Vector Layer to Raster**.
3. In the dialog, select the vector layer to convert and the field whose values will be burned into the raster.
4. Choose a save location for the output GeoTIFF.
5. The raster is loaded automatically into QGIS.

---

## Configuration Options

The **Find Drainage Basins** dialog exposes the following options:

### Sink Source

| Option | Description |
|---|---|
| **Sink layer** (dropdown) | Select an existing raster or vector layer as the sink source. Each unique pixel value or feature ID becomes a separate sink. |
| **Use Geomorphons** (checkbox) | Ignore the sink layer dropdown and auto-detect sinks from the DEM using geomorphon classification. |

### Neighborhood Type

Defines which neighboring cells are considered during percolation.

| Option | Connections | Description |
|---|---|---|
| **Von Neumann** | 4 | Only orthogonal neighbors (N, S, E, W). |
| **Moore** | 8 | Orthogonal and diagonal neighbors (N, NE, E, SE, S, SW, W, NW). |

### Projection

Defines the boundary conditions of the lattice.

| Option | Description |
|---|---|
| **Fixed** | Standard flat-grid projection. Cells at the border have no neighbors beyond the edge. |
| **Spheric** | Polar-wrap projection. The grid wraps around so that the top connects to the bottom and left connects to right. |

---

## Architecture

```
ipba_qgis_plugin/
│
├── __init__.py                     # QGIS plugin entry point
├── main_plugin.py                  # Main plugin class — menu actions and workflow
├── sink_selector.py                # Qt configuration dialog
├── metadata.txt                    # QGIS plugin metadata
│
├── lib/                            # Core algorithm library
│   ├── io.py                       # Raster/vector I/O (GDAL, numpy, GeoTIFF)
│   ├── data_prep.py                # Array utilities and data preparation
│   ├── identification.py           # Sink/ridge detection and clustering
│   ├── generation.py               # Fractal Brownian Motion terrain generation
│   │
│   ├── percolation_tools/          # IPBA algorithm implementation
│   │   ├── cell.py                 # Cell data structure (height, label, status)
│   │   ├── heap.py                 # Min-heap priority queue
│   │   ├── lattice.py              # Grid structure with neighborhood and projection
│   │   └── invasion_percolation.py # Core IPBA algorithm (DrainageBasins, IPBA)
│   │
│   └── geomorphon/                 # Terrain classification module
│       ├── geomorphon.py           # Python wrapper with C++ fallback
│       ├── geomorphon.cpp          # C++ implementation (OpenMP parallelized)
│       ├── geomorphon.dll          # Pre-compiled binary for Windows
│       └── libgeomorphons.so       # Pre-compiled binary for Linux
│
└── docs/
    └── index.md                    # This documentation file
```

### Data Flow

```
Active DEM layer
       │
       ▼
raster_layer_to_numpy()          ← converts DEM to numpy array
       │
       ▼
find_sinks_raster()              ← auto-detect OR user-provided sink layer
       │
       ▼
convert_array_to_dict()          ← builds sink dictionary {(row, col): id}
       │
       ▼
Lattice()                        ← initializes grid with cells and neighborhoods
       │
       ▼
IPBA() → DrainageBasins()        ← runs invasion percolation for all cells
       │
       ▼
lattice.set_labels_sinks()       ← assigns final basin IDs to all cells
       │
       ▼
numpy_to_geotiff()               ← writes georeferenced output GeoTIFF
       │
       ▼
QgsRasterLayer()                 ← loads result into QGIS canvas
```

---

## Dependencies

| Package | Purpose | Required |
|---|---|---|
| [numpy](https://numpy.org/) | Array operations and numerical computing | Yes |
| [scipy](https://scipy.org/) | Morphological operations (ndimage) | Yes |
| [scikit-image](https://scikit-image.org/) | Skeletonization (skeleton extraction) | Yes |
| [GDAL / OGR](https://gdal.org/) | Raster and vector geospatial I/O | Yes |
| QGIS (≥ 3.4) | PyQGIS API and Qt bindings | Yes |
| C++ compiler + OpenMP | Building the geomorphon native library | Optional |

---

## Building the Geomorphon Library

Pre-compiled binaries are included for Windows (`geomorphon.dll`) and Linux (`libgeomorphons.so`). If you need to recompile for your platform:

### Linux / macOS

```bash
g++ -O3 -ffast-math -march=native -fopenmp -DNDEBUG \
    -shared -fPIC \
    lib/geomorphon/geomorphon.cpp \
    -o lib/geomorphon/libgeomorphons.so
```

### Windows (MSVC)

```bat
cl /LD /O2 /fp:fast /arch:AVX2 /openmp /DNDEBUG ^
   lib\geomorphon\geomorphon.cpp ^
   /Fe:lib\geomorphon\geomorphon.dll
```

> If no compiled binary is found at runtime, the plugin automatically falls back to a pure-Python geomorphon implementation.

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repository on GitHub.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request against the `main` branch.

Please ensure that any new functionality is covered by appropriate tests and that existing behavior is not broken.

---

## Contact

**Alisson Frota**  
Email: [alissonfrotat@gmail.com](mailto:alissonfrotat@gmail.com)  
GitHub: [@AlissonFrota](https://github.com/AlissonFrota)

---

*Generated for [IPBA QGIS Plugin](https://github.com/AlissonFrota/ipba_qgis_plugin) — version 1.0*
