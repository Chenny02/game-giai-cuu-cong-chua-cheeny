import heapq


class AStarPathfinder:
    """A* nhẹ cho maze grid; hỗ trợ nhiều loại heuristic và né tránh vật cản động."""

    def __init__(self, grid):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height else 0

    def heuristic_manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def heuristic_euclidean(self, a, b):
        return ((a[0] - b[0])**2 + (a[1] - b[1])**2)**0.5

    def heuristic_chebyshev(self, a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

    def walkable(self, cell):
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == 0

    def neighbors(self, cell):
        x, y = cell
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nxt = (x + dx, y + dy)
            if self.walkable(nxt):
                yield nxt

    def find_path(self, start, goal, heuristic_type="manhattan", enemy_positions=None):
        if not self.walkable(start) or not self.walkable(goal):
            return []
        if start == goal:
            return []

        # Chọn hàm heuristic
        h_func = self.heuristic_manhattan
        if heuristic_type == "euclidean":
            h_func = self.heuristic_euclidean
        elif heuristic_type == "chebyshev":
            h_func = self.heuristic_chebyshev

        frontier = [(0, start)]
        came_from = {start: None}
        cost_so_far = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break

            for nxt in self.neighbors(current):
                # Cost cơ bản là 1
                move_cost = 1
                
                # Bonus cost nếu gần kẻ địch (Safety Heuristic)
                if enemy_positions:
                    for ex, ey in enemy_positions:
                        dist_sq = (nxt[0] - ex)**2 + (nxt[1] - ey)**2
                        if dist_sq < 9: # Trong tầm 3 ô
                            move_cost += 10 / (dist_sq + 1)

                new_cost = cost_so_far[current] + move_cost
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    priority = new_cost + h_func(nxt, goal)
                    heapq.heappush(frontier, (priority, nxt))
                    came_from[nxt] = current

        if goal not in came_from:
            return []

        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path
