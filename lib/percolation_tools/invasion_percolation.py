# Making imports
from .heap import Heap
from .cell import Cell # Used only for type annotation
from .lattice import Lattice # Used only for type annotation
import numpy as np

def IPBA(lattice: Lattice, arr: np.ndarray, sinks: dict, ntype: str , projection: str):
    """Executes the IPBA model

    Args:
        lattice (Lattice): _description_
        arr (np.ndarray): The arra
        sinks (dict): A dictionary with the posicion and values of sinks
        ntype (str): 'von_neumann' or 'moore'
        projection (str): 'fixed', 'spheric' or 'torus'
    """
    # setting the lattice
    lattice.set_lattice(arr)

    # defining the isnum
    for posicion in range(lattice.size):
        x: Cell = lattice.cells[posicion]
        if np.isnan(x.height):
            x.isnum = False

    # defining the sinks
    for posicion, value in sinks.items():
        x = lattice.cells[posicion]
        x.sink = value
    
    # performing the DrainageBasins
    DrainageBasins(lattice, ntype, projection)


def DrainageBasins(lattice: Lattice, ntype: str , projection: str):
    """Repeats the process of the invasion percolation with each cell of the lattice"""
    for k in range(lattice.size):
        x: Cell = lattice.cells[k]
        InvasionPercolation(lattice, x, ntype, projection)


def InvasionPercolation(lattice: Lattice, x: Cell, ntype: str , projection: int ):
    """Executes the invasion percolation on a given lattice and cell"""
    if x.isnum and x.sigma is None: # If No one found the cell yet and it is valid
        # Clears the previus percolation
        for y in lattice.burnt:
            y.status = None
        lattice.burnt = []

        # Creates the heap
        heap = Heap()
        
        lattice.burnt.append(x)
        x.status = False
        parent = x
        
        heap.Insert(x.height, x.posicion)

        stop = False
        while heap.size > 0 and stop == False:
            # Only care about the posicion
            _, t = heap.ExtractMin()
            
            # Get the cell
            y: Cell = lattice.cells[t]

            # Invade the cell
            y.status = True

            # Set parent relation
            y.parent = parent
            parent = y
            
            # If found someone who found a sink, get the sigma(posicion of the sink it was drained)
            if y.sigma is not None:
                w = y.sigma
                stop = True
            
            # If found a sink, stop and get it's posicion
            if y.sink is not None:
                w = y.posicion
                stop = True
            
            # If a sink or similar was not found
            if stop == False:
                # Get the neighbors (now respecting projection)
                for z in lattice.get_cell_neighbors(y, ntype, projection):
                    if z.isnum and z.status is None:
                        lattice.burnt.append(z)
                        z.status = False
                        
                        heap.Insert(z.height, z.posicion)
        
        if stop: # If a sink or similar was found
            while y.parent != y:
                # Adds sigma and label for each passed cell
                y.sigma = w
                z: Cell = lattice.cells[w]
                y.label = z.sink
                y = y.parent
            
            y.sigma = w
            z: Cell = lattice.cells[w]
            y.label = z.sink