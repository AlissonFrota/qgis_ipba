import numpy as np
from osgeo import gdal, osr
from qgis.core import QgsRasterLayer,QgsVectorLayer ,QgsRasterDataProvider, QgsProject
from .data_prep import format_border, quick_load


def read_band_raw(layer: QgsRasterLayer, band: int = 1) -> np.ndarray:
    """Read a raster band as RAW stored values, exactly like ``rasterio.read``.

    This is the QGIS-side equivalent of the reference notebook's
    ``rasterio.open(path).read(1)``: it returns the untouched pixel values,
    nodata sentinels included. It deliberately does NOT use
    ``QgsRasterLayer.as_numpy(use_masking=True)`` (which rewrites nodata to NaN)
    nor ``raster_layer_to_numpy`` (which additionally injects tie-breaking
    noise). Value-based algorithms such as water-sink detection must use this so
    their output matches the notebook rather than being corrupted by nodata
    masking or noise.
    """
    ds = gdal.Open(layer.source())
    if ds is None:
        raise RuntimeError(f"GDAL could not open raster source: {layer.source()}")
    return ds.GetRasterBand(band).ReadAsArray()


def raster_layer_to_numpy(layer: QgsRasterLayer):
    dem_array = layer.as_numpy(1)[0]
    dem_provider = layer.dataProvider()

    nrows = dem_provider.ySize() + 2
    ncols = dem_provider.xSize() + 2

    np.random.seed(42) 

    dem_array = np.where(
        np.isclose(dem_array, dem_provider.sourceNoDataValue(1)),
        np.nan,
        dem_array
    )

        
    dem_array += (1 / 1000) * np.random.random(dem_array.shape)

    arr = np.full((nrows, ncols), np.nan, dtype = np.float32)
    arr[1 : nrows - 1, 1 : ncols - 1] = dem_array

    return arr, nrows, ncols

def numpy_to_geotiff(arr: np.ndarray,filename: str ,reference_layer: QgsRasterLayer):
    
    nrows, ncols = arr.shape

    # Densely relabel the (possibly huge, non-contiguous) basin ids to 0..n-1,
    # sorted ascending, so the smallest label (the -1 "no basin" background)
    # maps to 0 and is written as nodata. searchsorted keeps arr's 2-D shape and
    # is robust across numpy versions (unlike np.unique(return_inverse=...)).
    uniq = np.unique(arr)
    n = uniq.size
    labels = np.searchsorted(uniq, arr)   # each cell -> its 0-based rank (0..n-1)

    # uint16 holds 0..65535; when a run yields more than 65536 distinct basins
    # the ids no longer fit, so widen to uint32.
    if n <= 2 ** 16:
        np_dtype, gdal_dtype = np.uint16, gdal.GDT_UInt16
    else:
        np_dtype, gdal_dtype = np.uint32, gdal.GDT_UInt32

    arr_tiff = labels.astype(np_dtype)

    provider = reference_layer.dataProvider()
    extent = reference_layer.extent()

    driver = gdal.GetDriverByName('GTiff')
    raster = driver.Create(r'{}.tif'.format(filename),
                           provider.xSize(),
                           provider.ySize(),
                           1,
                           gdal_dtype,
                        )
    
    gt = (
        extent.xMinimum(),
        reference_layer.rasterUnitsPerPixelX(),
        0,
        extent.yMaximum(),
        0,
        -reference_layer.rasterUnitsPerPixelY()
    )

    crs = reference_layer.crs()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(crs.toWkt())
    
    raster.SetGeoTransform(gt)
    raster.SetProjection(srs.ExportToWkt())
    
    #colors = [(0.0, 0.0, 0.0)] + [(0.2 + 0.6 * np.random.random(),
    #                               0.2 + 0.6 * np.random.random(),
    #                               0.2 + 0.6 * np.random.random()) for i in range(n - 1)]
    
    raster.GetRasterBand(1).SetNoDataValue(0)
    raster.GetRasterBand(1).WriteArray(arr_tiff)
    
    band = raster.GetRasterBand(1)
    #color_table = gdal.ColorTable()
    
    #for i, color in enumerate(colors):
    #    color_table.SetColorEntry(i, (int(255 * color[0]),
    #                                  int(255 * color[1]),
    #                                  int(255 * color[2])))
    
    #band.SetRasterColorTable(color_table)
    #band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    
    raster.FlushCache()
    
    del band
    del raster

def vector_layer_to_raster(vector_layer: QgsVectorLayer, raster_layer: QgsRasterLayer):
    
    import processing

    extent = raster_layer.extent()
    crs = raster_layer.crs()
    extent_str = "{xmin},{xmax},{ymin},{ymax} [{authid}]".format(
        xmin=extent.xMinimum(),
        xmax=extent.xMaximum(),
        ymin=extent.yMinimum(),
        ymax=extent.yMaximum(),
        authid=crs.authid()
    )

    if not vector_layer.fields():
        raise ValueError("Vector layer has no attributers to burn")
    
    burn_field = vector_layer.fields()[0].name()

    print("Burn field", burn_field)
    print("Input", vector_layer)

    width = raster_layer.width()
    height = raster_layer.height()

    params = {
        'CREATION_OPTIONS': None,
        'EXTRA': '',
        'INVERT': False,
        'USE_Z' : False,
        'INPUT': vector_layer,
        'FIELD': burn_field,
        'UNITS': 0,
        'WIDTH': width,
        'HEIGHT': height,
        'EXTENT': extent_str,
        'NODATA': 0,
        'DATA_TYPE': 4,
        'INIT': None,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }

    res = processing.run("gdal:rasterize", params)


    out_path = res.get('OUTPUT')
    if not out_path:
        raise RuntimeError("No Output")
        
    out_raster = QgsRasterLayer(out_path, f"{vector_layer.name()}_rasterized")
    if not out_raster.isValid():
        raise RuntimeError(f"Created raster is invalid: {out_path}")
        
    return out_raster
