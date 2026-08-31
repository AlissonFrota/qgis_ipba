import numpy as np
import math
import ctypes
import os
from pathlib import Path

def _load_geomorphon_library():
    module_dir = Path(__file__).resolve().parent
    if os.name == "nt":
        candidates = [module_dir / "geomorphon.dll"]
    else:
        candidates = [
            module_dir / "geomorphon.so",
            module_dir / "libgeomorphons.so",
        ]

    for candidate in candidates:
        if candidate.exists():
            try:
                return ctypes.CDLL(str(candidate))
            except OSError:
                continue

    return None

lib = _load_geomorphon_library()

if lib is not None:
    lib.compute_geomorphons.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS'),
        ctypes.c_int,
        ctypes.c_int,
        np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS'),
        ctypes.c_int,
        ctypes.c_double
    ]
    lib.compute_geomorphons.restype = None

def geomorphons_cpp(heights, L=20, threshold=1.0):
    """Wrapper Python para a função C++ de geomorphon"""
    if lib is None:
        return full_geomorphon_process_optimized(heights, L=L, threshold=threshold)

    heights = np.ascontiguousarray(heights, dtype=np.float64)
    nrows, ncols = heights.shape
    geo_results = np.zeros_like(heights, dtype=np.float64)
    
    lib.compute_geomorphons(
        heights,
        nrows,
        ncols,
        geo_results,
        L,
        threshold
    )
    
    return geo_results



def full_geomorphon_process_optimized(heights: np.ndarray, L: int=20, threshold: float=1):
    GEOMORPHONS_MATRIX = [
    [4, 4, 4, 3, 3, 1, 1, 1, 0],# Valleys and Pits
    [4, 4, 3, 3, 3, 1, 1, 1],#
    [4, 6, 5, 5, 2, 2, 1],#
    [6, 6, 5, 5, 5, 2],#
    [6, 6, 7, 5, 5],#
    [8, 8, 7, 7],#
    [8, 8, 8],#
    [8, 8],#
    [9] # Ridges and Peaks
    ]
    geo_results = np.empty(heights.shape)
    nrows, ncols = heights.shape
    L += 1

    col_values = np.array([1, 1, 0, -1, -1, -1, 0, 1])
    row_values = np.array([0, 1, 1, 1, 0, -1, -1, -1])
    distance_values = np.sqrt((col_values ** 2) + (row_values ** 2))

    for num_line in range(1, nrows - 1):
        for num_cols in range(1, ncols - 1):
            positive = 0
            negative = 0

            for direction in range(8):
                row_increment = row_values[direction]
                col_increment = col_values[direction]
                dist_inc = distance_values[direction]
                steps = int(L // dist_inc)

                valid_count = 0
                max_angle = -9999.0
                min_angle = 9999.0

                for step in range(1, steps):
                    r = num_line + step * row_increment
                    c = num_cols + step * col_increment
                    if r < 0 or r >= nrows or c < 0 or c >= ncols:
                        break
                    d = step * dist_inc
                    dh = heights[r, c] - heights[num_line, num_cols]
                    angle = math.atan(dh / d) * (180 / math.pi)
                    
                    if angle > max_angle:
                        max_angle = angle
                    if angle < min_angle:
                        min_angle = angle
                    if np.isnan(angle):
                        valid_count -= 1
                    valid_count += 1

                if valid_count == 0:
                    continue

                if max_angle - abs(min_angle) > threshold:
                    positive += 1
                elif abs(max_angle - abs(min_angle)) <= threshold:
                    pass  # neutral
                else:
                    negative += 1

            # Acessa a matriz de resultados
            geo_results[num_line, num_cols] = GEOMORPHONS_MATRIX[negative][positive]

    return geo_results
