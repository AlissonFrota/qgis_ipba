""" This module is dedicated to implementing the heap to be used in the ipba model
"""
class Heap:
    def __init__(self):
        self.height = []
        self.posicion = []
        self.size = 0
    
    def _Parent(self, i: int) -> int:
        """Find the parent based on the posicion index i

        Args:
            i (int): The posicion index of the son's

        Returns:
            int: The posicion index of the parent
        """
        return (i - 1) // 2
    
    def _Left(self, i : int) -> int:
        return 2 * i + 1
    
    def _Right(self, i: int) -> int:
        return 2 * i + 2
    
    def _DecreaseKey(self, i: int) -> None:
        parent = self._Parent(i)
        while i > 0 and self.height[parent] > self.height[i]:
            self.height[i], self.height[parent] = self.height[parent], self.height[i]
            self.posicion[i], self.posicion[parent] = self.posicion[parent], self.posicion[i]
            
            i = parent
            parent = self._Parent(i)
    
    def _Heapify(self, i: int) -> None:
        left = self._Left(i)
        right = self._Right(i)
        
        if left < self.size and self.height[left] < self.height[i]:
            smallest = left
        else:
            smallest = i
        
        if right < self.size and self.height[right] < self.height[smallest]:
            smallest = right
        
        if smallest != i:
            self.height[i], self.height[smallest] = self.height[smallest], self.height[i]
            self.posicion[i], self.posicion[smallest] = self.posicion[smallest], self.posicion[i]
            
            self._Heapify(smallest)
    
    def Insert(self, height: float | int, posicion: int) -> None:
        """ Inserts a item into the heap

        Args:
            height (int): The height value of a cell
            posicion (int): The posicion value of a cell
        """
        self.height.append(height)
        self.posicion.append(posicion)
        self.size += 1
        
        self._DecreaseKey(self.size - 1)
    
    def ExtractMin(self) -> tuple[int,int]:
        """ Returns the top and removes it from the heap

        Returns:
        
            tuple[int, int]: A tuple with the height value and the posicion
        """
        height = self.height[0]
        item = self.posicion[0]
        
        self.height[0] = self.height[self.size - 1]
        self.posicion[0] = self.posicion[self.size - 1]
        
        del self.height[self.size - 1]
        del self.posicion[self.size - 1]
        self.size -= 1
        
        self._Heapify(0)
        
        return height, item