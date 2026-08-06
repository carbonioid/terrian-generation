from PIL import Image
from collections import Counter
from pprint import pprint
from util import init_grid
import random

W = H = 20
STATES = ["coast", "land", "sea"]

# Rules format:
# {(1): [{state: weight, ...}, {state: weight, ...}, ...], ...}
# four lists: north, east, south, west, a state in that respective list can border (1) in that direction with that weight (weight is 0-1)
rules = {}

def get_grid_neighbours(x, y, grid, count=4, return_deltas=False, pad_values=False):
    # count can be 4 or 8
    if count not in [4, 8]: raise ValueError(f"`count` must be 4 or 8 in `get_grid_neighbours` but it was {count}")
    if count == 4:
        deltas = [
            (0, -1),
            (1, 0),
            (0, 1),
            (-1, 0)
        ]
    elif count == 8:
        deltas = [
            (-1, 0),
            (0, -1),
            (1, 0),
            (0, 1),
            (-1, 1),
            (-1, -1),
            (1, 1),
            (1, -1)
        ]

    for dx, dy in deltas:
        cx, cy = x+dx, y+dy
        if 0 <= cx < len(grid[0]) and 0 <= cy < len(grid):
            if return_deltas:
                yield (dx, dy, grid[cy][cx]) # im fancy
            else:
                yield grid[cy][cx]
        elif pad_values:
            yield None

def initial_rules_from_exemplar(exemplar_grid):
    neighbour_instances = {} # state: [[north], [east], [south], [west]]

    # convert cardinal directions to the lists in [[north], [east], [south], [west]] (cardinal directions are returned by get_grid_neighbours)
    directions_to_index = {
        (0, 1): 0, # north
        (1, 0): 1, # east
        (0, -1): 2, # south
        (-1, 0): 3, # west
    }

    for y in range(len(exemplar_grid)):
        for x in range(len(exemplar_grid[y])):
            state = exemplar_grid[y][x]
            neighbours = get_grid_neighbours(x, y, exemplar_grid, count=4, return_deltas=True)
            for dx, dy, neighbour_state in neighbours:
                # We need to figure out which of the four lists to add it to based on the cardinal directions its in from the tile
                dir_index = directions_to_index[(dx, dy)]

                if not neighbour_instances.get(state):
                    neighbour_instances[state] = [[], [], [], []]
                
                neighbour_instances[state][dir_index].append(neighbour_state)
    
    # Construct ruleset
    rules = {}
    for main_state, neighbours_list in neighbour_instances.items():
        print(f'{state=}')
        final_lists = []

        # For each direction, construct its list
        for dir_list in neighbours_list:
            unnormalised_dir_dict = {}
            appearing_states = Counter(dir_list) # we need to count these so we can weight them appropriately

            total = 0
            for state, count in appearing_states.items():
                total += count
                unnormalised_dir_dict[state] = count
            
            # Normalise weights
            final_dir_dict = {}
            for state, cnt in unnormalised_dir_dict.items():
                final_dir_dict[state] = cnt/total

            final_lists.append(final_dir_dict) # we iterate in north, east, south, west so they will be added in the correct order
        
        rules[main_state] = final_lists
    
    pprint(rules)
    return rules

def run_wavefunction_collapse(grid_w, grid_h, states, rules):
    init_superposition = states
    grid = init_grid(grid_w, grid_h, init_superposition)
    entropy_grid = init_grid(grid_w, grid_h, len(STATES)) # useful caching for how many options left in each superposition

    # Some axuiliary functions
    def choose_state(weights):
        r = random.random()
        total = 0
        for state, weight in weights.items():
            total += weight
            if r <= total: return state
    
    def validate_state(neighbours, state_rules):
        # can this state be here, according to its respective rules?
        # neighbours should be in order north, east, south, west
        # True if state can be here

        for dir_rules, neighbour in zip(state_rules, neighbours):
            if neighbour not in list(dir_rules.keys()) and type(neighbour) == str: # neighbours may be None or lists, ignore those 
                return False
        
        return True
    
    solution_found = False
    start_state_index = -1
    while not solution_found:
        start_state_index += 1
        if start_state_index >= len(STATES):
            raise Exception('Could not find solution')

        initx, inity = 0, 0 # start in top left
        grid[inity][initx] = STATES[start_state_index]
        entropy_grid[inity][initx] = 0 # we chose so 1 option left

        solved_tiles = 1
        contradiction_found = False
        while solved_tiles < grid_w*grid_h:
            # Collapse superpositions
            for y, row in enumerate(grid):
                for x, superposition in enumerate(row):
                    if type(superposition) != list: 
                        continue # Already decided
                    
                    new_superposition = []
                    neighbours = list(get_grid_neighbours(x, y, grid, pad_values=True)) # ignore non-collapsed neighbours
                    # if neighbours: print(f'{neighbours=}')

                    for possible_state in superposition:
                        if rules.get(possible_state) is not None and validate_state(neighbours, rules.get(possible_state)):
                            new_superposition.append(possible_state)
                    
                    if len(new_superposition) == 0:
                        contradiction_found = True
                    
                    grid[y][x] = new_superposition
                    entropy_grid[y][x] = len(new_superposition)
            
            if contradiction_found: break

            # Find lowest entropy
            low_entropy_x = -1
            low_entropy_y = -1
            lowest_entropy = len(STATES) + 1
            for y, row in enumerate(entropy_grid):
                for x, value in enumerate(row):
                    if value < lowest_entropy and value != 0: # we dont want to choose alr collapsed ones at 0 entropy
                        lowest_entropy = value
                        low_entropy_y, low_entropy_x = y, x

                    if lowest_entropy == 1: break # bailout if we found an optimal candidate
                if lowest_entropy == 1: break
            
            if lowest_entropy == len(STATES) + 1: break
            
            print(f'Lowest entropy at {low_entropy_x, low_entropy_y} ({lowest_entropy}) ({list(get_grid_neighbours(low_entropy_x, low_entropy_y, grid))})')
            # Collapse this one. But we need to find the weights first.
            # We want to iterate over the neighbours keeping in mind that the direction should be flipped to get
            # the correct weights (the neighbour north of us has our weight as a southerly neighbour)
            direction_mapping = {
                0: 2, # north -> south etc
                1: 3,
                2: 0,
                3: 1
            }

            weights_sum = {} # Naive sum of all 0-1 weights from all directions, by state. Normalise later.

            neighbours = get_grid_neighbours(low_entropy_x, low_entropy_y, grid, pad_values=True, return_deltas=False)

            le_possible_states = grid[low_entropy_y][low_entropy_x]
            for i, neighbour_state in enumerate(neighbours):
                if neighbour_state is None or type(neighbour_state) == list: 
                    continue # ignore invalid neighbours & uncollapsed neighbours

                dir_to_check = direction_mapping[i]
                if rules.get(neighbour_state) is not None:
                    weights = rules[neighbour_state][dir_to_check]


                    for state in le_possible_states:
                        w = weights.get(state, 0)
                        print(f'----> weight {w} for {state}')
                        if state not in weights_sum: weights_sum[state] = w
                        weights_sum[state] += w

            print(f'{weights_sum=}')

            if len(weights_sum) > 0:
                # normalise weights sum
                total = sum(weights_sum.values())
                weights_normalised = {state: weight/total for state, weight in weights_sum.items()}

                new_state = choose_state(weights_normalised)

                print(f'-> Chose {new_state}')

                grid[low_entropy_y][low_entropy_x] = new_state
                entropy_grid[low_entropy_y][low_entropy_x] = 0
            else:
                # if we didn't have any valid neighbours choose randomly
                print('Guessing...')
                new_state = choose_state({s: 1/len(STATES) for s in STATES})
        
        if not contradiction_found: solution_found = True

    return grid

def display_grid(grid, pixel_size=50):
    color_map = {
        "land": (119, 209, 34),
        "sea": (50,50, 50),
        "coast": (255, 0, 0)
    }

    im = Image.new('RGB', (pixel_size*len(grid[0]), pixel_size*len(grid))) # w, h

    pixel_data = []
    for row in grid:
        im_row = []
        for state in row:
            im_row+=[color_map.get(state, (120, 120, 120))]*pixel_size
        
        pixel_data+=(im_row*pixel_size)
    
    im.putdata(pixel_data)
    im.show()

from wc_aux import exemplar

# exemplar = [
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'coast', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'coast', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'coast', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'coast', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'coast', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['coast', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['coast', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'coast', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'coast', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'coast', 'land', 'land', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'coast', 'land', 'land', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'coast', 'land', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'coast', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
#     ['sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea', 'sea'],
# ]

# exemplar = [
#     ["land", "land", "coast", "sea", "sea"],
#     ["land", "land", "coast", "sea", "sea"],
#     ["land", "land", "land", "coast", "sea"],
#     ["coast", "land", "land", "land", "coast"],
#     ["sea", "coast", "coast", "coast", "sea"],
#     ["sea", "sea", "sea", "sea", "sea"]
# ]

rules = initial_rules_from_exemplar(exemplar)

g = run_wavefunction_collapse(40, 40, STATES, rules)
pprint(g)
display_grid(g, 15)
display_grid(exemplar, 50)
print(f'RULES:')
pprint(rules)