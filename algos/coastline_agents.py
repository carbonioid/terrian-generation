import random, copy, math
from PIL import Image

def init_grid(w, h, defualt_value):
    grid = [
        [defualt_value for i in range(w)] for _ in range(h)
    ]

    return grid

def get_grid_neighbour_coords(x, y, grid):
    deltas = [
        (0, -1),
        (1, 0),
        (0, 1),
        (-1, 0)
    ]
    for dx, dy in deltas:
        cx, cy = x+dx, y+dy
        if 0 <= cx < len(grid[0]) and 0 <= cy < len(grid):
            yield cx, cy

def get_grid_neighbours(x, y, grid):
    for cx, cy in get_grid_neighbour_coords(x, y, grid):
        yield grid[cy][cx]

def generate_random_point(w, h):
    return (random.randint(0, w-1), random.randint(0, h-1))

def generate_coastline(gridw, gridh, init_tokens, actions_per_agent) -> list[list[int]]:
    grid = init_grid(gridw, gridh, 0) # 0 is below sea level / sea, 1 is land

    # To run the simulation, we keep a list of all agents currently operating on the grid
    # Each stores initial # of tokens and coastline (whose length doubles as the # of used tokens)
    # They also store attractor & repulsor positions. Position it not stored as agents jump around.
    # We run one step for each agent in the list every frame, adding and removing agents as necessary.
    # Once the list is empty, the program terminates.

    def initialise_agent(position, tokens, width, height):
        # Generate attractor and repulsor in different directions by making the attractor be +ve, +ve away and the repulsor be -ve, -ve away
        dx_attractor = random.randint(0, (width-position[0])-1)
        dy_attractor = random.randint(0, (height-position[1])-1)

        dx_repulsor = -random.randint(0, position[0])
        dy_repulsor = -random.randint(0, position[1])

        attractor = (position[0]+dx_attractor, position[1]+dy_attractor)
        repulsor = (position[0]+dx_repulsor, position[1]+dy_repulsor)

        return [tokens, [position], attractor, repulsor, random.choice([
                        (0, 1),
                        (0, -1),
                        # (1, 0),
                        # (-1, 0)
                    ])]

    current_agents = [initialise_agent((gridw//2, gridh//2), init_tokens, gridw, gridh)]

    # Some initialisation - we need to start with some filled in coast.
    grid[gridh//2][gridw//2] = 1

    # We also keep a map of all squares which are currently boundary - this is updated dynamically as
    # more squares are added. A 1 indicates a boundary (land bordering sea in 1+ directions) and 0 indicates 
    # non-boundary (land bordering only land or sea)
    boundary_map = copy.deepcopy(grid) # Currently it's exactly the same as the grid.

    ACTIONS = 0
    LOST = 0

    def place_land_on_map(posx, posy):
        """Place land at `posx`, `posy`, updating auxiliary data-structures as needed (boundary_map)"""
        grid[posy][posx] = 1

        # Check if any land has been obstructed
        for nx, ny in get_grid_neighbour_coords(posx, posy, grid):
            # Check all neighbours: if none sea (and it is landd), set to 0 on boundary map
            neighbours = get_grid_neighbours(nx, ny, grid)
            if grid[ny][nx] == 1 and not any(neighbour == 0 for neighbour in neighbours) or \
                grid[ny][nx] == 0:
                boundary_map[ny][nx] = 0

        # Also update that this is a boundary (presumably)
        neighbours = get_grid_neighbours(posx, posy, grid)
        if any(neighbour == 0 for neighbour in neighbours):
            boundary_map[posy][posx] = 1 # This is a boundary now.

    def random_coastline_position(boundary_map, steps=1):
        # TODO: Improve this
        taken = 0
        for y, row in enumerate(boundary_map):
            for x, value in enumerate(row):
                if value == 1: 
                    taken += 1
                    if steps == taken:
                        return (x, y)

        return (x, y)

    while len(current_agents) > 0:
        for i, agent in enumerate(current_agents):
            tokens, coastline, attractor, repulsor, preferred_direction = agent

            if len(coastline) >= tokens or len(coastline) >= actions_per_agent: # if we exceeded the action limit per agent or the total # of tokens
                # Create two new child agents
                current_agents.pop(i)
                print(f"I'm out of tokens! {repulsor=} {attractor=} {tokens=}")

                # Only split if we have > 1 token, otherwise we will create agents with 0 token budget which is dumb.
                if tokens > 1:
                    # Get two random (non-overlapping) positions for new agents which are on a coastline.
                    # `coastline` points are not guaranteed to still be coastline.
                    real_coastline = [point for point in coastline if boundary_map[point[1]][point[0]] == 1]
                    coastline = real_coastline

                    if len(coastline) == 0:
                        agent1_pos = random_coastline_position(boundary_map, steps=1)
                        agent2_pos = random_coastline_position(boundary_map, steps=2)
                    else:
                        agent1_pos = random.choice(coastline)

                        new_coastline = copy.deepcopy(coastline)
                        new_coastline.remove(agent1_pos)

                        if len(new_coastline) == 0:
                            agent2_pos = random_coastline_position(boundary_map)
                        else:
                            agent2_pos = random.choice(new_coastline)

                    # Create two new children & distribut the tokens between them
                    current_agents.append(initialise_agent(agent1_pos, math.floor(tokens/2), gridw, gridh))
                    current_agents.append(initialise_agent(agent2_pos, math.ceil(tokens/2), gridw, gridh))
            else:
                # Choose a random point, then find the highest scoring neighbour
                # And color that point.
                neighbour_locations = []
                found_good_location = False

                # Get a shuffled copy of the coastline to iterate overs
                new_coast = copy.deepcopy(coastline)
                random.shuffle(new_coast)

                for position in new_coast:
                    neighbour_locations = get_grid_neighbour_coords(*position, grid)
                    neighbour_values = get_grid_neighbours(*position, grid)

                    # We only want neighbour locations that are water
                    neighbour_locations = [neighbour for neighbour, neighbour_value in zip(neighbour_locations, neighbour_values) if neighbour_value == 0]
                    if len(neighbour_locations) > 0:
                        found_good_location = True
                        break

                if not found_good_location:
                    # position = random_coastline_position(boundary_map, steps=random.randint(0, len(boundary_map)-1))

                    direction = preferred_direction

                    # Continue in this direction until you find real coastline
                    search_pos = copy.deepcopy(position)
                    while 0 <= search_pos[0] < gridw and 0 <= search_pos[1] < gridh and boundary_map[search_pos[1]][search_pos[0]] != 1:
                        search_pos = [search_pos[0] + direction[0], search_pos[1] + direction[1]]

                    position = search_pos

                    neighbour_locations = get_grid_neighbour_coords(*position, grid)
                    neighbour_values = get_grid_neighbours(*position, grid)
                    neighbour_locations = [neighbour for neighbour, neighbour_value in zip(neighbour_locations, neighbour_values) if neighbour_value == 0]  
                    print(f'From search: {neighbour_locations=}')

                if len(neighbour_locations) > 0:
                    # Score locations
                    # Some auxiliary funcs - `score` is the overall score function and
                    # `d_e` returns dist from (x, y) to the closest edge.
                    def d_e(x, y):
                        return min((
                            abs(x-(gridw-1)), abs(x),
                            abs(y-(gridh-1)), abs(y)
                        ))

                    squared_dist = lambda p, q: (p[0]-q[0])**2 + (p[1]-q[1])**2
                    
                    score = lambda x, y: squared_dist((x, y), repulsor)**2 - squared_dist((x, y), attractor) + 3 * d_e(x, y)**2

                    # Find best location & place land there.
                    best_location = sorted(neighbour_locations, key = lambda pos: score(*pos))[0]
                    place_land_on_map(*best_location)
                    ACTIONS += 1

                    # Add the new location to coastline & decrememnt num tokens & move agent to the new location
                    current_agents[i][1].append(best_location)
                else:
                    print(f'Something has gone horribly wrong, I have no neighbours :( (at {position}) (losing {tokens})')
                    LOST += tokens
                    current_agents.pop(i) # This is just going to buffer forever so remove it. Shouldn't happen.

    print(f'Actions: {ACTIONS}; Lost: {LOST}')
    return grid


def display_grid(grid, pixel_size=50):
    color_map = {
        0: (169, 204, 227), 
        1: (126, 179, 88)
    }

    im = Image.new('RGB', (pixel_size*len(grid[0]), pixel_size*len(grid))) # w, h

    pixel_data = []
    for row in grid:
        im_row = []
        for state in row:
            im_row+=[color_map.get(state, (120, 120, 120))]*pixel_size
        
        pixel_data+=(im_row*pixel_size)
    
    im.putdata(pixel_data)
    im.save(f"img/{random.randint(1, 500)}.png")
    im.show()

w = h = 512
out_grid = generate_coastline(w, h, 5000, 3000)
print('Rendering grid...')
display_grid(out_grid, pixel_size=1)
