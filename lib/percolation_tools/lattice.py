import numpy as np
from .cell import Cell

class Lattice:
    def __init__(self, nrows: int, ncols: int):
        self.nrows = nrows
        self.ncols = ncols
        self.size = self.nrows * self.ncols

        self.cells = np.empty(self.size, dtype = Cell)

        self.burnt = []
        self.label_sinks = - np.ones((self.nrows, self.ncols), dtype = np.int64)
        self.label_antis = - np.ones((self.nrows, self.ncols), dtype = np.int64)
        self.new_label = -np.ones((self.nrows, self.ncols), dtype = np.int64)

        # Spheric wrap defaults to full grid; updated in set_lattice if a NaN
        # frame is detected.
        self._spheric_col_min = 0
        self._spheric_col_max = self.ncols - 1
        self._spheric_top_row = 0
        self._spheric_bottom_row = self.nrows - 1
    
    def set_lattice(self, arr: np.ndarray):
        """ Initializes the cells of the lattice given a array of heights

        Args:
            arr (np.ndarray): A one dimensional array with the heights
        """
        flat_arr = np.asarray(arr).reshape(-1)
        if flat_arr.size != self.size:
            raise ValueError(
                f"Expected {self.size} heights, got {flat_arr.size}"
            )

        # Detect padded NaN frame to choose the spherical horizontal domain.
        arr2d = flat_arr.reshape(self.nrows, self.ncols)
        has_nan_frame = (
            self.nrows >= 3 and self.ncols >= 3 and
            np.all(np.isnan(arr2d[0, :])) and
            np.all(np.isnan(arr2d[-1, :])) and
            np.all(np.isnan(arr2d[:, 0])) and
            np.all(np.isnan(arr2d[:, -1]))
        )
        if has_nan_frame:
            self._spheric_col_min = 1
            self._spheric_col_max = self.ncols - 2
            self._spheric_top_row = 1
            self._spheric_bottom_row = self.nrows - 2
        else:
            self._spheric_col_min = 0
            self._spheric_col_max = self.ncols - 1
            self._spheric_top_row = 0
            self._spheric_bottom_row = self.nrows - 1

        for k in range(self.size):
            self.cells[k] = Cell(k, flat_arr[k])
    
    # Revisitar depois

    def _projection_mode(self, projection: int | str) -> int:
        """Normalize projection input to internal mode code."""
        if isinstance(projection, str):
            proj = projection.strip().lower()
            if proj == "spheric":
                return 0
            if proj == "fixed":
                return 1
            raise ValueError(f"Unknown projection: {projection}")

        if projection in (0, 1):
            return int(projection)

        raise ValueError(f"Unknown projection code: {projection}")

    def _pos_to_index(self, row: int, col: int, projection: int | str):
        """Convert row/col to linear index applying projection wrap rules.

        projection codes:
        - 0: spheric (wrap columns in spherical domain, keep rows bounded)
        - 1: fixed (no wrapping)
        """
        mode = self._projection_mode(projection)

        if mode == 0: # spheric
            col_span = self._spheric_col_max - self._spheric_col_min + 1
            if col_span <= 0:
                return None
            col = self._spheric_col_min + ((col - self._spheric_col_min) % col_span)
            if row < 0 or row >= self.nrows:
                return None
            
        elif mode == 1: # fixed
            if row < 0 or row >= self.nrows or col < 0 or col >= self.ncols:
                return None

        return row * self.ncols + col

    def get_cell_neighbors(self, x: Cell, ntype: str, projection: int | str):
        """
        Get the neighbors around the given x using the chosen neighborhood and projection.
        Returns a list of existing neighbors (omits out-of-bounds for fixed projection).
        """
        if ntype == 'von_neumann':
            return self.get_cell_four_neighbors(x, projection)
        elif ntype == 'moore':
            return self.get_cells_eight_neighbors(x, projection)

    def _get_spheric_polar_coords(self, row: int, col: int, projection: int | str) -> list[tuple[int, int]]:
        """Extra neighbors for spheric poles: all spherical-domain cells on the same pole row."""
        if self._projection_mode(projection) != 0:
            return []

        if row not in (self._spheric_top_row, self._spheric_bottom_row):
            return []
        if self._spheric_col_max < self._spheric_col_min:
            return []

        return [
            (row, pole_col)
            for pole_col in range(self._spheric_col_min, self._spheric_col_max + 1)
            if pole_col != col
        ]

    def get_cell_four_neighbors(self, x: Cell, projection: int | str) -> list[Cell]:
        """Return available 4-neighbors in order: Right, Up, Left, Down."""
        row = x.posicion // self.ncols
        col = x.posicion % self.ncols

        coords = [
            (row, col + 1),    # Right
            (row - 1, col),    # Up
            (row, col - 1),    # Left
            (row + 1, col),    # Down
        ]

        mode = self._projection_mode(projection)

        neighbors = []
        visited = set()
        for r, c in coords:
            idx = self._pos_to_index(r, c, mode)
            if idx is not None and idx not in visited:
                visited.add(idx)
                neighbors.append(self.cells[idx])

        if mode == 0:
            for r, c in self._get_spheric_polar_coords(row, col, mode):
                idx = self._pos_to_index(r, c, mode)
                if idx is not None and idx not in visited:
                    visited.add(idx)
                    neighbors.append(self.cells[idx])
        return neighbors
    
    def get_cells_eight_neighbors(self, x: Cell, projection: int | str) -> list[Cell]:
        """Get the eight cell neighbors around the given x position, starting from the right and going clockwise."""
        row = x.posicion // self.ncols
        col = x.posicion % self.ncols

        coords = [
            (row, col + 1),        # Right
            (row + 1, col + 1),    # Bottom right
            (row + 1, col),        # Down
            (row + 1, col - 1),    # Bottom left
            (row, col - 1),        # Left
            (row - 1, col - 1),    # Top left
            (row - 1, col),        # Up
            (row - 1, col + 1),    # Top right
        ]

        mode = self._projection_mode(projection)

        neighbors = []
        visited = set()
        for r, c in coords:
            idx = self._pos_to_index(r, c, mode)
            if idx is not None and idx not in visited:
                visited.add(idx)
                neighbors.append(self.cells[idx])

        if mode == 0:
            for r, c in self._get_spheric_polar_coords(row, col, mode):
                idx = self._pos_to_index(r, c, mode)
                if idx is not None and idx not in visited:
                    visited.add(idx)
                    neighbors.append(self.cells[idx])
        return neighbors
    

    
    def get_basins(self, p: None | float = None):
        areas = {}
        for k in range(self.size):
            x: Cell = self.cells[k]
            if x.label is not None:
                areas[x.label] = areas.get(x.label, 0) + 1
                # if x.label in areas:
                #     areas[x.label] += 1
                # else:
                #     areas[x.label] = 1
        
        # Sort the items with regard to the ammount
        ordered_areas = sorted(areas.items(),
                               key = lambda x: x[1],
                               reverse = True)

        # Get the labels and the ammount of each
        labels, counts = np.asarray(list(zip(*ordered_areas)))

        # If p is None, no post-processing is done
        if p is None:
            basins = labels
        else:
            # Filter the least important indexes
            indexes = np.argwhere(np.cumsum(counts) / np.sum(counts) <= p)
            filtered_indexes = np.squeeze(indexes,
                                          axis = 1)

            basins = labels[filtered_indexes]

        return basins
    
    def set_labels_sinks(self):
        """Transfers the label of the cells to the lattice
        """
        for j in range(1, self.nrows - 1):
            for i in range(1, self.ncols - 1):
                k = i + j * self.ncols
                x: Cell = self.cells[k]
                if x.label is not None:
                    self.label_sinks[j, i] = x.label

    def set_labels_antis(self):
        """Transfers the label of the cells to the lattice
        """
        for j in range(1, self.nrows - 1):
            for i in range(1, self.ncols - 1):
                k = i + j * self.ncols
                x: Cell = self.cells[k]
                if x.label is not None:
                    self.label_antis[ j, i] = x.label
    
    def merge_labels(self, p: float | None = None):
        """Merge the sinks and antis labels to find the slope units

        Args:
            p (float, optional): The value of acceptence of slope units size. Defaults to None.
        """
        for j in range(self.nrows):
            for i in range(self.ncols):
                a = self.label_sinks[j, i]
                b = self.label_antis[j, i]

                if a >= 0 and b >= 0:
                    self.new_label[j, i] = int(0.5 * (a + b) * (a + b + 1) + b) # Cantor paring function
                else:
                    self.new_label[j, i] = -1
        
        labels, counts = np.unique(self.new_label,
                                   return_counts = True)
        
        indexes = np.argsort(counts)[::-1]
        counts = counts[indexes]
        labels = labels[indexes]
        
        if p is None:
            slope_units = labels
        else:
            indexes = np.argwhere(np.cumsum(counts) / np.sum(counts) <= p)
            filtered_indexes = np.squeeze(indexes,
                                          axis = 1)
            
            slope_units = labels[filtered_indexes]
        
        for j in range(self.nrows):
            for i in range(self.ncols):
                if self.new_label[j, i] not in slope_units:
                    self.new_label[j, i] = -1


    def link(self, cellA: Cell, cellB: Cell) -> None:
        """
        Makes parent association depending on the rank of the cells

        A > B  --> A is parent of B

        A < B  --> B is parent of A

        A = B  --> B is parent of A, B.rank += 1
        """
        if cellA.rank > cellB.rank:
            cellB.parent = cellA
        else:
            cellA.parent = cellB
            if cellA.rank == cellB.rank:
                cellB.rank += 1
        
            # No need for recursion?
            # Personal Note: In some cases one rotation is not enough,
            # so we utilize 2 rotations to make sure that all conections
            # are made.

    def find_root_parent(self,site: Cell) -> Cell:
        """
        Find the \"Greatest\" parent of a Cell
        """
        if site.parent != site:
            # Straight foward recursion
            site.parent = self.find_root_parent(site.parent)
        return site.parent
    
    def union(self, cellA: Cell, cellB: Cell) -> None:
        self.link(self.find_root_parent(cellA), self.find_root_parent(cellB))
