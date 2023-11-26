from typing import Tuple

import numpy as np # type: ignore

graphic_dt = np.dtype([
  ("ch", np.int32),
  # Foreground color (3 unsigned bytes -> RGB)
  ("fg", "3B"),
  # Background color (3 unsigned bytes -> RGB)
  ("bg", "3B")
])

tile_dt = np.dtype([
  # Set if this tile can be walked over
  ("walkable", bool),
  # Set it this tile blocks FOV
  ("transparent", bool),
  # Set what this tile looks like when not in FOV
  ("dark", graphic_dt)
])

def new_tile(
  *,
  walkable: int,
  transparent: int,
  dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]]) -> np.ndarray:
  return np.array((walkable, transparent, dark), dtype=tile_dt)

floor = new_tile(
  walkable=True, transparent=True, dark=(ord(" "), (255, 255, 255), (50, 50, 150))
)

wall = new_tile(
  walkable=False, transparent=False, dark=(ord(" "), (255, 255, 255), (0, 0, 100))
)