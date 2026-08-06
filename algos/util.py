def init_grid(w, h, defualt_value):
    grid = [
        [defualt_value for i in range(w)] for _ in range(h)
    ]

    return grid
