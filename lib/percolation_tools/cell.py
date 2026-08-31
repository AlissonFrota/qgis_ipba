class Cell:
    def __init__(self, posicion: int, height: float | int):

        self.posicion = posicion
        """The posicion of a Cell"""
        self.height = height
        """The height of a Cell
        """

        self.isnum = True
        self.sink = None
        """The sink number if it is a sink, else None
        """
        self.sigma = None
        """The posicion of the sink that drains the cell
        """
        self.status = None
        """If the cell is invaded(True), on the heap(False) or not Checked(None)
        """
        self.parent = self
        """The parent of the cell
        """
        self.label = None
        """The number of the sink that drains the cells
        """
        self.rank = 0