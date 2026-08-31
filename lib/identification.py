import numpy as np
from skimage.morphology import skeletonize
from .geomorphon.geomorphon import geomorphons_cpp
from scipy.ndimage import generic_filter, binary_fill_holes
from scipy import ndimage

from collections import deque

class Site:
    def __init__(self, posicion:int, value: int | float):
        self.value = value
        self.posicion = posicion
        self.status = True
        self.rank = 0
        self.parent = self

class Cleanner:
    """Class to Clean and Separate clusters

        Any value nan is counted as 0 and any other is 1
    """
    def __init__(self, matrix: np.ndarray):
        self._matrix = matrix
        self.rows, self.cols = matrix.shape
        self.size = self.cols * self.rows
        self.site = np.empty(shape=(self.rows, self.cols), dtype=Site)
        self.set_cleanner(matrix)

    def set_cleanner(self, matrix: np.ndarray):
        for num_line in range(self.rows):
            for num_col in range(self.cols):
                self.site[num_line, num_col] = Site(num_col + self.cols * num_line, matrix[num_line, num_col])

        for num_line in range(self.rows):
            for num_col in range(self.cols):
                if np.isnan(self.site[num_line, num_col].value):
                    self.site[num_line, num_col].status = False   

    def restart_cleanner(self):
        self.set_cleanner(self._matrix)

    def _get_neighbors8(self, num_line, num_col) -> np.ndarray:
        return np.array(
            [
                self.site[num_line    , num_col + 1],
                self.site[num_line + 1, num_col + 1],
                self.site[num_line + 1, num_col    ],
                self.site[num_line + 1, num_col - 1],
                self.site[num_line    , num_col - 1],
                self.site[num_line - 1, num_col - 1],
                self.site[num_line - 1, num_col    ],
                self.site[num_line - 1, num_col + 1]
            ]
        )
    
    def _get_neighbors4(self, num_line, num_col) -> np.ndarray:
        return np.array(
            [
                self.site[num_line    , num_col - 1],
                self.site[num_line + 1, num_col    ],
                self.site[num_line    , num_col + 1],
                self.site[num_line - 1, num_col    ],
            ]
        )
    
    def link(self, cellA: Site, cellB: Site):
        if cellA.rank > cellB.rank:
            cellB.parent = cellA
        else:
            cellA.parent = cellB
            if cellA.rank == cellB.rank:
                cellB.rank += 1

    def get_root_parent(self, cell: Site) -> Site:
        if cell.parent != cell:
            cell.parent = self.get_root_parent(cell.parent)
        return cell.parent

    def unionize(self, cellA: Site, cellB: Site):
        self.link(self.get_root_parent(cellA), self.get_root_parent(cellB))

    def separete_clusters(self, type_neighbor:str|None=None):
        """Separates the clusters based on proximity

        Args:
            type_neighbor (str, optional): Select the type of neighbors to use, 4 or 8. Defaults to 4.

        Returns:
            np.ndarray: The map with the clusters separated
        """
        if type_neighbor == "8":
            neighbor_func = self._get_neighbors8
        else:
            neighbor_func = self._get_neighbors4

        for num_line in range(1, self.rows - 1):
            for num_col in range(1, self.cols - 1):
                elem: Site = self.site[num_line, num_col]
                if elem.status:
                    neighbors = neighbor_func(num_line, num_col)
                    for nei in neighbors:
                        if nei.status:
                            self.unionize(elem, nei)

        clusters = np.full((self.rows, self.cols), fill_value=np.nan)
        self.clusters_dict = {}
        for num_line in range(1, self.rows - 1):
            for num_col in range(1, self.cols - 1):
                elem: Site = self.site[num_line, num_col]
                if elem.status:
                    clusters[num_line, num_col] = self.get_root_parent(elem).posicion
                    self.clusters_dict[self.get_root_parent(elem).posicion] = self.clusters_dict.get(self.get_root_parent(elem).posicion, 0) + 1
        
        self.restart_cleanner()
        return clusters
    
    def filter_specks(self, p:float, type_neighbor=None) -> np.ndarray:
        separated = self.separete_clusters(type_neighbor)
        sorted_clusters = sorted(self.clusters_dict.items(), key= lambda x: x[1], reverse=True)

        labels = np.array(list(map(lambda x: x[0], sorted_clusters)))
        counts = np.array(list(map(lambda x: x[1], sorted_clusters)))

        indexes = np.argsort(counts)[::-1]
        counts = counts[indexes]
        labels = labels[indexes]

        if p is None:
            result = labels
        else:
            indexes = np.argwhere(np.cumsum(counts) / np.sum(counts) <= p)
            filtered_indexes = np.squeeze(indexes, axis=1)
            result = labels[filtered_indexes]

        result = set(result)
        final_sinks = separated.copy()

        for num_line in range(1, self.rows - 1):
            for num_col in range(1, self.cols - 1):
                value = separated[num_line, num_col]
                if not np.isnan(value) and (not value in result):
                    final_sinks[num_line, num_col] = np.nan

        return final_sinks

def extract_centerlines_with_ids(binary_array):
    """Extract centerlines with unique IDs from binary array"""
    skeleton = skeletonize(binary_array).astype(np.uint8)
    labeled_result = np.zeros_like(skeleton, dtype=np.int32)
    visited = np.zeros_like(skeleton, dtype=bool)
    id_counter = 1

    def get_neighbors(x, y):
        cords = np.array([[i, j] for i in range(x - 1, x + 2) for j in range(y - 1, y + 2)])
        cords = np.delete(cords, 4, axis=0)
        for k in range(len(cords)):
            yield cords[k]

    def count_neighbors(x, y):
        return sum(skeleton[num_line, num_col] for num_line, num_col in get_neighbors(x, y))

    endpoints = [(x, y) for x in range(skeleton.shape[0])
                        for y in range(skeleton.shape[1])
                        if skeleton[x, y] == 1 and count_neighbors(x, y) == 1]

    def queue_process(x, y):
        if visited[x, y]:
            return

        queue = deque()
        queue.append((x, y))
        nonlocal id_counter
        current_id = id_counter
        id_counter += 1

        while queue:
            x, y = queue.pop()
            if visited[x, y]:
                continue

            visited[x, y] = True
            labeled_result[x, y] = current_id

            neighbors = [(nx, ny) for nx, ny in get_neighbors(x, y)
                        if skeleton[nx, ny] == 1 and not visited[nx, ny]]

            if len(neighbors) == 1:
                queue.append(neighbors[0])
            elif len(neighbors) > 1:
                for i, j in neighbors:
                    queue_process(i, j)
    
    for ex, ey in endpoints:
        queue_process(ex, ey)

    return labeled_result

def wei_the_dem(heights: np.ndarray) -> np.ndarray:
    """Weight the DEM for better sink detection"""
    blur = generic_filter(heights, np.nanmean, size=7)
    delta = heights - blur
    acc = heights + 10 * delta
    acc = generic_filter(acc, np.nanmean, size=7)
    return acc

def find_sinks_raster(dem: np.ndarray, search_distance: int=20, angle_threshold:int=1) -> tuple[np.ndarray, np.ndarray]:
    """Find sinks and ridges from DEM"""
    blur_dem = generic_filter(dem, np.nanmean, size=7)
    delta = dem - blur_dem
    acc = dem + 10 * delta
    acc = generic_filter(acc, np.nanmean, size=7)
    
    geo = geomorphons_cpp(acc, search_distance, angle_threshold)
    geo = np.where(np.isnan(dem), np.nan, geo)
    
    valleys = np.where(np.less_equal(geo, 1), 1, 0)
    ridges = np.where(np.greater_equal(geo, 8), 1, 0)
    
    valleys = binary_fill_holes(valleys)
    ridges = binary_fill_holes(ridges)
    
    valleys = np.where(np.isclose(valleys, 0), np.nan, 1)
    ridges = np.where(np.isclose(ridges, 0), np.nan, 1)
    
    valleys = Cleanner(valleys).filter_specks(0.95, "8")
    ridges = Cleanner(ridges).filter_specks(0.95, "8")
    
    valleys = np.where(np.isnan(valleys), 0, 1)
    ridges = np.where(np.isnan(ridges), 0, 1)
   
    valleys = extract_centerlines_with_ids(valleys)
    ridges = extract_centerlines_with_ids(ridges)
  
    return valleys, ridges

def _subdivide_shoreline(water_sinks, n_water_sinks, is_water, n_parts):
    """Cut each shoreline component into ``n_parts`` contiguous arcs.

    Each connected water-sink group is split by ordering its cells by angle
    around the water body's centroid and slicing that order into ``n_parts``
    equal-count runs — so every id is a continuous stretch of coast. A group
    with fewer cells than ``n_parts`` is split into as many single-cell parts as
    it has cells.

    Parameters
    ----------
    water_sinks : 2-D int array
        Connected-component labels of the shoreline (0 = background).
    n_water_sinks : int
        Number of shoreline components in ``water_sinks``.
    is_water : 2-D bool array
        The main water body (used for the centroid the coast is ordered around).
    n_parts : int
        Number of arcs to cut each component into.

    Returns
    -------
    (new_ids, total) : 2-D int array and int
        Relabelled shoreline with ascending ids 1..total (0 = background).
    """
    if n_parts <= 1 or n_water_sinks == 0:
        return water_sinks, n_water_sinks

    water_rows, water_cols = np.nonzero(is_water)
    if water_rows.size == 0:
        return water_sinks, n_water_sinks
    cy, cx = water_rows.mean(), water_cols.mean()

    new_ids = np.zeros_like(water_sinks)
    next_id = 1
    for comp in range(1, n_water_sinks + 1):
        rows, cols = np.nonzero(water_sinks == comp)
        if rows.size == 0:
            continue
        # Order the component's cells along the coast by angle around the water
        # centroid, then split into equal-count contiguous arcs.
        order = np.argsort(np.arctan2(rows - cy, cols - cx), kind="stable")
        for part in np.array_split(order, min(n_parts, rows.size)):
            if part.size == 0:
                continue
            new_ids[rows[part], cols[part]] = next_id
            next_id += 1

    return new_ids, next_id - 1


def find_sinks_water_adjacent(
    dem: np.ndarray,
    water_value: float,
    use_border_sinks: bool = True,
    min_sink_size: int = 0,
    shoreline_parts: int = 1,
    n_water_bodies: int = 1,
    nodata: float | None = None,
) -> np.ndarray:
    """Label the sink cells of a DEM.

    A cell is elected as a sink when it is LAND and:
      * at least one of its Moore (8-connected) neighbours is WATER, OR
      * (when ``use_border_sinks``) it lies on a DATA EDGE — either the matrix
        border or the boundary of the valid-data footprint (i.e. it has a
        nodata neighbour).

    Moore-adjacent sinks are merged into a single group. Each group gets a
    distinct, ascending id (1, 2, 3, ...); non-sink cells are 0.

    This is designed to work on rasters as they actually appear in QGIS,
    including **reprojected** DEMs. Reprojection has two consequences the naive
    version cannot handle: valid data no longer fills the whole grid (it becomes
    a rotated footprint padded with nodata), and water/land values are
    resampled to non-exact numbers. Handling nodata as a boundary makes the
    "edge is an outlet" rule follow the real data footprint instead of the
    meaningless matrix rectangle, and prevents nodata fill from being mislabeled
    as land sinks.

    Parameters
    ----------
    dem : 2-D array
        Digital elevation model (raw band values).
    water_value : scalar
        Value that represents water in ``dem``.
    use_border_sinks : bool, default True
        Whether data-edge cells (matrix border or nodata boundary) are outlets.
    min_sink_size : int, default 0
        Minimum number of cells a water-sink group must contain to be kept.
        Groups smaller than this are discarded. This removes the little clusters
        of sinks that form around the shorelines of small offshore islands. 0
        disables the filter (keep every group).
    shoreline_parts : int, default 1
        Number of contiguous parts to cut each connected shoreline group into.
        Even a single connected coast is split into this many equal-length arcs,
        each with its own id (ordered by angle around the water body). 1 keeps
        each shoreline as one id (no division).
    n_water_bodies : int, default 1
        How many water bodies (the largest by cell count) are treated as the sea
        and elect adjacent land as shoreline sinks. Interior lakes/rivers not
        touching the raster edge are always excluded. Raise this when an island
        touches the raster border and splits the sea into several pieces, so the
        coast is sunk all the way around instead of on one side only.
    tolerance : float, default 0.01
        Absolute tolerance for the water/nodata value comparison. Resampling and
        upstream noise mean an exact ``==`` is unreliable.
    nodata : scalar or None
        The raster's nodata sentinel (from the provider). Cells equal to it, and
        any NaN cells, are treated as no-data. ``None`` means "no sentinel"
        (only NaN counts as no-data).

    Returns
    -------
    sinks : 2-D int array (same shape as ``dem``)
        0 for non-sinks; 1..N ascending ids for the N sink groups.
    """
    from scipy.ndimage import label, binary_dilation
    #dem = np.asarray(dem, dtype=float)

    # No-data: NaN, plus the raster's sentinel value if one was supplied.
    is_nodata = np.isnan(dem)
    if nodata is not None and not np.isnan(nodata):
        is_nodata |= np.isclose(dem, nodata)

    # Full 3x3 Moore structuring element, reused for neighbour tests and for the
    # connected-component merge below (diagonal touches merge into one group).
    moore = np.ones((3, 3), dtype=bool)

    # Water cells (exact match to ``water_value``, never a no-data cell).
    is_water_all = (dem == water_value)

    # Decide which water bodies are "sea" and get to elect adjacent land.
    # Fully-enclosed interior lakes/rivers (which touch no raster edge) are
    # dropped so they never generate sinks. Among the sea bodies we keep the
    # largest ``n_water_bodies`` by size: when an island touches the raster
    # border it splits the surrounding sea into separate pieces, so raising this
    # count re-includes the far side(s) and the coast is sunk all the way round.
    water_labels, n_bodies = label(is_water_all, structure=moore)
    if n_bodies > 0:
        counts = np.bincount(water_labels.ravel())
        counts[0] = 0  # ignore the background label

        # "Sea" = water that reaches the raster edge (the matrix border).
        on_edge = np.zeros(dem.shape, dtype=bool)
        on_edge[0, :] = on_edge[-1, :] = on_edge[:, 0] = on_edge[:, -1] = True
        sea_labels = np.unique(water_labels[on_edge & is_water_all])
        sea_labels = sea_labels[sea_labels != 0]

        if sea_labels.size == 0:
            # No water reaches the matrix border — e.g. a reprojected DEM whose
            # real sea touches the nodata padding, not the raster rectangle.
            # Fall back to ranking every water body so the sea is still elected.
            sea_labels = np.nonzero(counts)[0]

        # Keep the largest ``n_water_bodies`` sea bodies (by cell count).
        order = sea_labels[np.argsort(counts[sea_labels])[::-1]]
        keep = order[: max(1, n_water_bodies)]
        is_water = np.isin(water_labels, keep)
    else:
        is_water = is_water_all

    # Land is everything that is neither water nor no-data. Note: interior water
    # bodies we dropped above are treated as land here, so they will never be
    # flagged as (or adjacent to) sinks.
    is_land = ~is_water_all & ~is_nodata

    # Rule 1 — land adjacent to the main water body (8-connected).
    water_neighbor = binary_dilation(is_water, structure=moore) & is_land

    # Rule 2 — data-edge outlets (only when requested): the matrix border plus
    # the boundary of the valid-data footprint (land touching nodata).
    edge = np.zeros(dem.shape, dtype=bool)
    if use_border_sinks:
        edge[0, :] = edge[-1, :] = True
        edge[:, 0] = edge[:, -1] = True
        edge |= binary_dilation(is_nodata, structure=moore)
    edge &= is_land

    # A cell that is both water-adjacent and on a data edge is counted as a
    # water sink, so the two categories stay disjoint.
    edge &= ~water_neighbor

    # Break the matrix border ring at its four corner cells. The border is a
    # closed loop, so even under 4-connectivity the bottom-left corner (and the
    # other three) would still join two perpendicular sides into one component.
    # Clearing the corner cells cuts those links so each side becomes its own
    # edge-sink group.
    if use_border_sinks:
        edge[0, 0] = edge[0, -1] = edge[-1, 0] = edge[-1, -1] = False

    # Label the two sink categories INDEPENDENTLY, then place edge ids in a
    # separate range above the water ids. This guarantees a water sink and an
    # edge sink never share an id — even when they touch — and that every group
    # of each category is distinct from every other.
    #
    # Edge sinks are labeled with 4-connectivity (the cross) so that edge groups
    # meeting only at a diagonal corner get DIFFERENT ids instead of being
    # merged: at a corner, one side keeps one id and the other side gets another.
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    water_sinks, n_water_sinks = label(water_neighbor, structure=moore)

    # Drop water-sink groups smaller than ``min_sink_size``. These are the tiny
    # clusters ringing small offshore islands. After removing them we relabel so
    # the remaining water ids stay contiguous (1..N), which also keeps the edge
    # id offset below correct.
    if min_sink_size > 1 and n_water_sinks > 0:
        sizes = np.bincount(water_sinks.ravel())
        too_small = np.nonzero(sizes < min_sink_size)[0]
        too_small = too_small[too_small != 0]  # never touch the background label
        if too_small.size:
            water_neighbor &= ~np.isin(water_sinks, too_small)
            water_sinks, n_water_sinks = label(water_neighbor, structure=moore)

    # Optionally cut each shoreline group into ``shoreline_parts`` contiguous
    # arcs, so a single connected coast still gets several ids.
    water_sinks, n_water_sinks = _subdivide_shoreline(
        water_sinks, n_water_sinks, is_water, shoreline_parts
    )

    edge_sinks, _ = label(edge, structure=cross)

    sinks = np.zeros(dem.shape, dtype=int)
    sinks[water_neighbor] = water_sinks[water_neighbor]
    sinks[edge] = edge_sinks[edge] + n_water_sinks

    return sinks


def filtrar_por_ocorrencias(matriz, min_ocorrencias=3):
    """Remove numbers that appear less than min_ocorrencias times"""
    resultado = matriz.astype(float)
    valores_validos = resultado[~np.isnan(resultado)]
    unicos, contagens = np.unique(valores_validos, return_counts=True)
    numeros_remover = unicos[contagens < min_ocorrencias]
    
    for num in numeros_remover:
        resultado[resultado == num] = np.nan
    
    return resultado