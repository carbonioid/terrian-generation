import random, copy, math, datetime
from PIL import Image
from scipy.special import lambertw
from util import init_grid

# Basic grid operations
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


# Grid parsing
def is_sea(value): return value == 0

def is_boundary(value): return value == 1

def is_land(value): return value != 0

def is_on_boundary(boundary_map, position):
    gridh = len(boundary_map)
    gridw = len(boundary_map[0])
    
    if 0 <= position[0] < gridw and 0 <= position[1] < gridh:
        return is_boundary(boundary_map[position[1]][position[0]])
    else:
        return False # if its out of bounds, not on coastline.

def get_sea_neighbour_locations(grid, position):
    neighbour_locations = get_grid_neighbour_coords(*position, grid)
    neighbour_values = get_grid_neighbours(*position, grid)
    neighbour_locations = [neighbour for neighbour, neighbour_value in zip(neighbour_locations, neighbour_values) if is_sea(neighbour_value)]  
    return neighbour_locations

class Agent:
    def __init__(self, position, tokens, width, height):
        # Generate attractor and repulsor in different directions by making the attractor be +ve, +ve away and the repulsor be -ve, -ve away
        dx_attractor = random.randint(0, (width-position[0])-1)
        dy_attractor = random.randint(0, (height-position[1])-1)

        dx_repulsor = -random.randint(0, position[0])
        dy_repulsor = -random.randint(0, position[1])

        attractor = (position[0]+dx_attractor, position[1]+dy_attractor)
        repulsor = (position[0]+dx_repulsor, position[1]+dy_repulsor)

        # Generate directions
        directions_length = 20 # This is an arbitrary value

        # We want to go in one consistent directions so we need to chose two of
        # four base cardinal directions to go (one x dir, one y dir)
        base_dirs = random.choice([
            [(1, 0), (0, 1)],
            [(-1, 0), (0, 1)],
            [(1, 0), (0, -1)],
            [(-1, 0), (0, -1)]
        ])

        # Direction is a list of repeated directions (dx, dy) to perform in succession. This allows
        # us to program more complex directions than the standard four/eight cardinal directions 
        # while never missing coastline.
        directions = list(random.choices(base_dirs, k=directions_length))

        self.tokens = tokens
        self.tokens_used = 1 # We've already been placed somewhere so
        self.coastline = [position]
        self.attractor = attractor
        self.repulsor = repulsor
        self.preferred_direction = directions
        self.gridw = width
        self.gridh = height

    def split_agent(self, boundary_map):
        """Create two new child agents and return them."""
        # Get two random (non-overlapping) positions for new agents, ideally on a castline.

        # `coastline` points are not guaranteed to still be coastline.
        real_coastline = [point for point in self.coastline if is_boundary(boundary_map[point[1]][point[0]])]

        # If we can, we prefer to use guaranteed coastline (This helps agents not mess up inner features
        # of the landscape) but otherwise we will use normal coastline and let the agents find their
        # way out once they spawn.
        # Create the new list so agent1_pos is distinct from agent2_pos
        if len(real_coastline) >= 2:
            agent1_pos = random.choice(real_coastline)
            new_coastline = copy.deepcopy(real_coastline)
            new_coastline.remove(agent1_pos)
            agent2_pos = random.choice(new_coastline)
        else:
            agent1_pos = random.choice(self.coastline)
            new_coastline = copy.deepcopy(self.coastline)
            new_coastline.remove(agent1_pos)
            agent2_pos = random.choice(new_coastline)

        # Create two new children & distribut the tokens between them
        return (Agent(agent1_pos, math.floor(self.tokens/2), self.gridw, self.gridh),
                Agent(agent2_pos, math.ceil(self.tokens/2), self.gridw, self.gridh))

    def score_location(self, location):
        x, y = location

        min_edge_dist = min((
            abs(x-(self.gridw-1)), abs(x),
            abs(y-(self.gridh-1)), abs(y)
        ))

        squared_dist = lambda p, q: (p[0]-q[0])**2 + (p[1]-q[1])**2

        return squared_dist((x, y), self.repulsor) - squared_dist((x, y), self.attractor) + 3 * min_edge_dist**2

    def search_for_coastline_from_current_position(self, boundary_map):
        # Continue in this direction until you find real coastline
        search_pos = copy.deepcopy(self.coastline[-1]) # coastline[-1] is our latest position

        dir_index = 0
        while 0 <= search_pos[0] < self.gridw and 0 <= search_pos[1] < self.gridh and not is_on_boundary(boundary_map, search_pos):
            direction = self.preferred_direction[dir_index % len(self.preferred_direction)]
            search_pos = [search_pos[0] + direction[0], search_pos[1] + direction[1]]

            dir_index += 1 # Go to the next direction in the list.

        # If we correctly found something, return. Otherwise return None
        if is_on_boundary(boundary_map, search_pos):
            return search_pos
        else:
            return None
    
    def choose_coastline_position(self, boundary_map) -> list[int]|None:
        """Find a random position on our current coastline (or move to find a 
        position elsewhere if there is one) to place the next land around."""
        # Choose a random point on coastline, then find the highest scoring neighbour
        # And raise that point above sea level.

        # Get a shuffled copy of the coastline to iterate over
        new_coast = copy.deepcopy(self.coastline)
        random.shuffle(new_coast)

        for position in new_coast:
            if is_on_boundary(boundary_map, position):
                return position

        # Debugging
        print(f'⊡', end='')

        # If we can't find a valid point on our coastline, move in our preferred direction to find one.
        return self.search_for_coastline_from_current_position(boundary_map)

    def choose_placement_locaiton(self, grid, boundary_map) -> list[int]|None:
        position = self.choose_coastline_position(boundary_map)
        if position: # it may be None if we couldn't find anything.
            neighbour_locations = get_sea_neighbour_locations(grid, position)

            # Find the location with maximum score, place there.
            best_location = sorted(neighbour_locations, key=self.score_location)[-1]

            return best_location

def generate_coastline(gridw, gridh, sizes: list[int], max_actions_per_agent, min_actions_per_agent, init_positions: list) -> list[list[int]]:
    """
    Generate coastline using coastline agents.
    Program will force all agents to not do more than `max_actions_per_agent`, and agents with a token budget 
    of less then `min_actions_per_agent` will not be able to split.

    `init_positions` is the list of initail positiosn for the agents; none of these positions should border each other.
    `sizes` is an array for each spawned agent detailling how many tiles they and all their sub-agents should place.
        This is converted into a token budget by the equation S/2*e^(W(2t/S*ln(2))) where S=min_actions_per_agent and t is the size.
    """
    # Auxiliary functions
    def place_land_on_map(posx, posy, t):
        """Place land at `posx`, `posy`, updating auxiliary data-structures as needed (boundary_map)"""
        grid[posy][posx] = t

        # Check if any land has been obstructed and thus should no longer be marked as a boundary
        for nx, ny in get_grid_neighbour_coords(posx, posy, grid):
            # Check all neighbours: if no sea neighbours (and it is land), set to 0 on boundary map
            if is_land(grid[ny][nx]) and not any(is_sea(neighbour) for neighbour in get_grid_neighbours(nx, ny, grid)) or \
                is_sea(grid[ny][nx]):
                boundary_map[ny][nx] = 0

        # Also update that this is a boundary, if it is.
        neighbours = get_grid_neighbours(posx, posy, grid)
        if any(is_sea(neighbour) for neighbour in neighbours):
            boundary_map[posy][posx] = 1 # This is a boundary now.

    grid = init_grid(gridw, gridh, 0) # 0 is below sea level / sea, 1 is land

    # Create init_tokens list
    # The user inputs sizes but we need to give tokens to the agents, so
    # we use this equation to convert a desired size to a desired token count.
    S = min_actions_per_agent
    init_tokens = [math.floor(S/2*math.exp(lambertw(2*N/S*math.log(2)).real)) for N in sizes]

    # We run one step for each agent in the list every frame, adding and removing agents as necessary.
    # Once the list is empty, the program terminates.
    current_agents = [
        Agent(pos, token_budget, gridw, gridh) 
        for pos, token_budget in zip(init_positions, init_tokens)
    ]

    # Some initialisation - we need to start with some filled in coast where the agents are.
    for pos in init_positions:
        grid[pos[1]][pos[0]] = 1

    # We also keep a map of all squares which are currently boundary - this is updated dynamically as
    # more squares are added. A 1 indicates a boundary (land bordering sea in 1+ directions) and 0 indicates 
    # non-boundary (land bordering only land or sea)
    boundary_map = copy.deepcopy(grid) # Currently it's exactly the same as the grid.

    ACTIONS = 0
    LOST = 0

    while len(current_agents) > 0:
        for i, agent in enumerate(current_agents):
            # if we exceeded the action limit per agent or the total # of tokens the agent has, split
            if agent.tokens_used >= agent.tokens or agent.tokens_used >= max_actions_per_agent:
                # First rmemove the agent.
                current_agents.pop(i)

                # Printouts
                sum_tokens = sum(agent.tokens for agent in current_agents)
                print(f"\nI'm out of tokens! (Tokens: {agent.tokens}; Remaining agent tokens: {sum_tokens+agent.tokens}) ", end='')

                # Now split the agent, on certain criteria.
                # We don't want to split when lower than 4 because we *never* want to split into 1-token agents because they do literally nothing.
                if agent.tokens > min_actions_per_agent and agent.tokens >= 4:
                    new_agents = agent.split_agent(boundary_map)
                    for agent in new_agents:
                        current_agents.append(agent) # Appending to the end ensures the iteration won't get messed up.
                
            else:
                position = agent.choose_placement_locaiton(grid, boundary_map)
                
                # if position is None we couldn't find a valid location, otherwise place land in the location.
                if position is not None:
                    place_land_on_map(*position, agent.tokens)
                    agent.tokens_used += 1 # increment tokens used as we just placed land
                    agent.coastline.append(position)

                    ACTIONS += 1
                else:
                    # If None run a fail-safe
                    print(f'\nSomething has gone horribly wrong, I have no neighbours :( (losing {agent.tokens})', end='')
                    current_agents.pop(i) # This is just going to buffer forever so remove it. Shouldn't happen meaningfully often.

                    LOST += agent.tokens

    print(f'\nActions: {ACTIONS}; Lost: {LOST}')
    return grid

def display_grid(grid, pixel_size=50, addendum=''):
    def lerp(a, b, t):
        return a + (b - a) * t

    def lerp_color(color, t, target=(0, 0, 0)):
        return tuple(round(lerp(c, tc, t)) for c, tc in zip(color, target))


    water = (169, 204, 227)
    lightg = (126, 179, 88)
    darkg = (82, 116, 57)
    # color_map = {
    #     0: (169, 204, 227), 
    #     1: (126, 179, 88)
    # }

    land_values = list(set(sum(grid, [])))
    land_values.sort()

    im = Image.new('RGB', (pixel_size*len(grid[0]), pixel_size*len(grid))) # w, h

    pixel_data = []
    for row in grid:
        im_row = []
        for state in row:
            if is_sea(state): color = water
            else:
                # Interpolate
                ind = land_values.index(state)
                flt = ind/(len(land_values)-1)
                color = lerp_color(darkg, flt, lightg)

            im_row+=[color]*pixel_size
            # im_row+=[color_map.get(state, (120, 120, 120))]*pixel_size
        
        pixel_data+=(im_row*pixel_size)
    
    im.putdata(pixel_data)
    path = datetime.datetime.now().strftime("%Y-%m-%d %H:%M") # ah yes datetime.datetime
    print(f'Saved as {path}.png')
    if len(addendum) > 0:
        im.save(f"img/{path} {addendum}.png")
    else:
        im.save(f"img/{path}.png")
    im.show()
