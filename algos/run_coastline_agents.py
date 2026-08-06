from coastline_agents import generate_coastline, display_grid

w = h = 1000
SMOOTHING_FACTOR = 1 # the lower the value the less fractal the coastlines will look

budget = 250000
out_grid = generate_coastline(w, h, [budget], budget, SMOOTHING_FACTOR, [(w//2, h//2)])
display_grid(out_grid, pixel_size=1, addendum='Colored')

# cnt = 10
# ma, mn = 15000, 3000
# random_points = [
#     (random.randint(0, w-1), random.randint(0, h-1)) for _ in range(cnt)
# ]

# budgets = [random.randint(mn, ma) for _ in range(cnt)]
# print(f'Expected tiles: {sum(budgets)}')
# out_grid = generate_coastline(w, h, budgets, ma, SMOOTHING_FACTOR, random_points)

# print('Rendering grid...')
# display_grid(out_grid, pixel_size=1, addendum=f'S: {SMOOTHING_FACTOR}; B: {sum(budgets)}; {cnt} points; {w}x{h}')
