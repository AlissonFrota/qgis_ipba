""" This file is for making repetitive processes that can make the code a mess / data preparation"""
import numpy as np
from numpy.random import MT19937, SeedSequence, RandomState
from pathlib import Path

print(f"Importing {__name__}")

def _make_random_state(seed:int = 42):
    """Generate a Random State with the seed value

    Args:
        seed (int, optional): The value for the specific RandomState. Defaults to 42.

    Returns:
        RandomState: A numpy random class for generating random values
    """
    return RandomState(MT19937(SeedSequence(seed)))

def _make_random_matrix(rows: int, cols: int, epsilon=1/100, seed = 42):
    """
    Generate a random noise matrix

    Parameters
    ----------
    rows : int
        The ammount of rows.
    cols : int
        The ammount of columns.
    epsilon : _type_, optional
        A multiplier of the whole matrix. Defaults to 1/100.
    random_state : RandomState, optional 
        The RandomState used for the random numbers Defaults to make_random_state(seed=42).

    Returns
    -------
    matrix : np.ndarray
        A random matrix with dimensions rows x cols.
    """
    
    # Making the random state
    random_state =_make_random_state(seed)
    
    # Return the random matrix
    return (random_state.rand(rows, cols) * epsilon)

def format_border(matrix:np.ndarray, border_value:int | float = np.nan):
    """Given a matrix, generates a border around it

    Args:
        matrix (np.ndarray): A matrix
        border_value (int | float, optional): The value for the border. Defaults to np.nan.

    Returns:
        np.ndarray: The formated matrix
    """
    num_rows, num_cols = matrix.shape
    border_rows, border_cols = num_rows + 2, num_cols + 2

    result_array = np.full(shape=(border_rows, border_cols), fill_value=border_value)
    result_array[1:border_rows - 1, 1:border_cols - 1] = matrix

    return result_array

def convert_array_to_dict(sinks: np.ndarray, nodata:int | float) -> dict:
    """Convert a numpy array to a dictionary of sinks, accounting for border

    Args:
        sinks (np.ndarray): The sinks array
        nodata (int | float): The no data value

    Returns:
        dict: Dictionary with position as key and sink value as value
    """
    sinks_dict = {}
    nrows, ncols = sinks.shape
    for j in range(nrows):
        for i in range(ncols):
            if sinks[j, i] > 0 and (sinks[j, i] != nodata or sinks[j, i] == -1):
                k = (i + 1) + (j + 1) * (ncols + 2)  # Accounting for border
                sinks_dict[k] = sinks[j, i]
                
    return sinks_dict

def get_new_sinks(old_sinks: dict, basins: np.ndarray) -> dict:
    """Given the basins, find the new sinks

    Args:
        old_sinks (dict): The old sinks
        basins (np.ndarray): The basins array

    Returns:
        dict: The filtered sinks
    """
    new_sinks = {}
    for key, value in old_sinks.items():
        if value in basins:
            new_sinks[key] = value

    return new_sinks

def load_data_geo(load_heights:np.ndarray, seed=42, epsilon=1/100, border: int | float = np.nan):
    """
    Load a matrix prepared for IPBA (Border and small noise)

    Parameters
    ----------
    array : np.ndarray
        The matrix to load
    seed : int, optional
        Value used to create the RandomState. Defaults to 42.
    epsilon : float, optional
        Multiplier for the noise. Defaults to 1/100.
    border : int | float, optional
        Value used for the borders. Defaults to np.nan
        
    Returns
    -------
    matrix: np.ndarray
        The formated matrix
    """
    # Get the shape
    rows, cols = load_heights.shape

    # Making a noise array
    random_array = _make_random_matrix(rows, cols, epsilon=epsilon, seed=seed)

    # Making the border around the lattice
    array_heights = format_border(load_heights, border_value=border)

    # Adding the noise
    array_heights[1:-1, 1:-1] += random_array

    return array_heights

def filter_no_data(array,no_data_value, **kwargs):
    """
    A function used to substitute the No_Data_Values in a matrix for another

    Assumes the array is already with a border

    Args:
        array (NDARRAY): The matrix to filter the values

    Kwargs:

        no_data_value (int | float, optional): The value that the matrix used when no data is available. Defaults to 0.
        
        atol (float, optional): The value of "how close" the value must be to be considered close. Defaults to 0.01.
        
        sub_value (int | float | np.nan, optional): The value a detected no_data_value will be replaced by. Defaults to np.nan.

    Returns:
        filtered_matrix NDARRAY: The matrix with the values close to no_data substituted for sub_value
    """
    
    temp_matrix = np.copy(array)

    unformated_matrix = temp_matrix[1:-1, 1:-1]

    unformated_matrix = np.where(np.isclose(unformated_matrix,                  # The matrix to analazy
                                            no_data_value,     # The Value to compare to
                                            atol=kwargs.get("atol", 0.01)),     # The margin for error
                                            kwargs.get("sub_value", np.nan),    # The value to substitute if is close
                                            unformated_matrix                   # The value if not
                                            )

    temp_matrix[1:-1, 1:-1] = unformated_matrix

    return temp_matrix

def quick_load(array:np.ndarray):
    matrix = load_data_geo(load_heights=array, epsilon=0, border=np.nan)
    return filter_no_data(matrix, np.nan)