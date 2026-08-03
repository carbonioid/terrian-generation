import random

def init_grid(w, h, defualt_value):
    grid = [
        [defualt_value for i in range(w)] for _ in range(h)
    ]

    return grid

def diamond_square(size, corners, roughness_scale, roughness_decay):
    # Only the corners of the initial grid are taken into account. Returns heightmap.
    # Size is the power of 2 to use i.e. 2**size
    # Adapted from https://every-algorithm.github.io/2024/10/18/diamond-square_algorithm.html

    grid = init_grid(2**size+1, 2**size+1, 0)

    # Set up corners
    # 1 --- 2
    # *     *
    # *     *
    # 3 --- 4

    grid[0][0] = corners[0]
    grid[0][-1] = corners[1]
    grid[-1][0] = corners[2]
    grid[-1][-1] = corners[3]

    roughness = lambda iteration: (random.random()-0.5)*2*roughness_scale * roughness_decay**iteration

    step_size = 2**size
    iteration = 0

    while step_size > 1:
        half_step = step_size // 2
        
        # Diamond
        for x in range(half_step, 2**size, step_size):
            for y in range(half_step, 2**size, step_size):
                avg = (
                    grid[y - half_step][x - half_step] +
                    grid[y + half_step][x - half_step] +
                    grid[y - half_step][x + half_step] +
                    grid[y + half_step][x + half_step]
                ) / 4.0

                avg += roughness(iteration)
                grid[y][x] = avg
        
        for x in range(0, 2**size, half_step):
            for y in range((x+half_step) % step_size, 2**size, step_size):
                sum_vals = 0.0
                count = 0
                if x - half_step >= 0:
                    sum_vals += grid[y][x - half_step]
                    count += 1
                if x + half_step < size:
                    sum_vals += grid[y][x + half_step]
                    count += 1
                if y - half_step >= 0:
                    sum_vals += grid[y-half_step][x]
                    count += 1
                if y + half_step < size:
                    sum_vals += grid[y+half_step][x]
                    count += 1
                avg = sum_vals / count
                # avg = (
                #     (grid[x - half_step, y] if x - half_step >= 0 else 0) +
                #     (grid[x + half_step, y] if x + half_step < size else 0)
                # ) / (2 if count else 1)
                grid[y][x] = avg + roughness(iteration)
            
        iteration += 1
        step_size //= 2
    
    return grid