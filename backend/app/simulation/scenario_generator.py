"""Deterministic (seeded) random warehouse scenario generator."""
from __future__ import annotations

import random
from typing import Any

from ..domain.grid import Grid, Position


def warehouse_map(width: int, height: int) -> list[str]:
    """Shelf blocks (2 wide x 2 tall) separated by aisles; guarantees a connected free space."""
    rows = []
    for y in range(height):
        row = ""
        for x in range(width):
            shelf = (x % 5 in (1, 2)) and (y % 4 in (1, 2)) and x < width - 1 and y < height - 1
            row += "#" if shelf else "."
        rows.append(row)
    return rows


def generate_random_scenario(n_agents: int, seed: int = 0, width: int = 20, height: int = 14,
                             tasks_per_robot: int = 1, name: str | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    rows = warehouse_map(width, height)
    grid = Grid.from_ascii(rows)
    free = grid.traversable_cells()
    if n_agents > len(free):
        raise ValueError("more agents than free cells")
    starts = rng.sample(free, n_agents)
    robots = []
    for i, s in enumerate(starts):
        tasks = []
        for j in range(tasks_per_robot):
            pu, de = rng.sample(free, 2)
            tasks.append({"id": f"T{i + 1}.{j + 1}", "pickup": [pu.x, pu.y], "delivery": [de.x, de.y], "priority": 1})
        robots.append({"id": f"R{i + 1}", "start": [s.x, s.y], "priority": n_agents - i, "tasks": tasks})
    return {"id": f"random-{n_agents}-{seed}", "name": name or f"Random ({n_agents} robots, seed {seed})",
            "description": f"Random warehouse scenario, {n_agents} robots, seed {seed}.",
            "map": rows, "robots": robots, "disruptions": [], "seed": seed}
