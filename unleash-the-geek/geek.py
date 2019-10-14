import sys
import math
import random

EMPTY = -1
MY_ROBOT = 0
ENEMY_ROBOT = 1
RADAR = 2
TRAP = 3
ORE = 4

# Quick and very dirty state machine :)

width, height = [int(i) for i in input().split()]
moves = [
    (0, 0),  # Here
    (0, -1),  # North
    (0, 1),  # South
    (1, 0),  # East
    (1, -1),  # North East
    (1, 1),  # South East
    (-1, -1),  # North West
    (-1, 1),  # South West
    (-1, 0)  # West
]

radar_idx = 0
radar_targets = [
    (6, 7),
    (10, 3), (10, 10),
    (5, 3), (5, 10),
    (15, 3), (15, 10),
    (19, 3), (19, 10),
    (12, 7),
    (17, 7),
    (22, 7),
    (24, 2), (24, 11)]


def distance(p1, p2):
    (x1, y1) = p1
    (x2, y2) = p2

    # City block
    return abs(x1 - x2) + abs(y1 - y2)

    # Weighted Horizontal
    # return abs(x1 - x2) + (abs(y1 - y2) * 4)

    # Euclidean
    # return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))


class Robot:
    def __init__(self, robot_id, current_x, current_y):
        self.target_x = None
        self.target_y = None
        self.robot_id = robot_id
        self.current_x = current_x
        self.current_y = current_y

    @staticmethod
    def they_dug_it(pos):
        return pos in game_map.all_holes() and pos not in work_log.history

    def good_move(self, pos):
        return (
                0 < pos[0] < width and 0 < pos[1] < height
                # and not game_map.radar_at(pos)
                and not game_map.is_trapped(pos)
                and work_log.is_unclaimed(self.robot_id, pos)
                and not self.they_dug_it(pos)
        )

    def random_dest(self):
        return self.random_dest_within(2, 0, width - 1, height - 1)

    def random_dest_within(self, min_x, min_y, max_x, max_y):
        def rand_point():
            return random.randint(min_x, max_x), random.randint(min_y, max_y)

        p = rand_point()
        while not self.good_move(p):
            p = rand_point()

        return p

    def small_step_from_here(self):
        return self.small_step_from((self.current_x, self.current_y))

    def small_step_from(self, pos):
        (x1, y1) = pos

        abs_moves = [(x1 + x2, y1 + y2) for (x2, y2) in moves]
        good_moves = [loc for loc in abs_moves if self.good_move(loc)]
        clear_ground = [loc for loc in good_moves if not game_map.hole_at(loc)]

        if clear_ground:
            return clear_ground[0]  # random.choice(clear_ground[:3])
        else:
            return None

    def there_is_ore_out_there(self):
        with_ore = [loc for loc, count in game_map.ore_map.items() if count]
        good_moves = [loc for loc in with_ore if self.good_move(loc)]

        return len(good_moves) > 0

    def closest_with_ore(self, p1):
        with_ore = [loc for loc, count in game_map.ore_map.items() if count]
        good_moves = [loc for loc in with_ore if self.good_move(loc)]
        ordered = sorted(good_moves, key=lambda p2: distance(p1, p2))

        if ordered:
            return ordered[0]
        else:
            return None

    def with_most_ore(self):
        with_ore = [(loc, count) for loc, count in game_map.ore_map.items() if count]
        good_moves = [(loc, count) for (loc, count) in with_ore if self.good_move(loc)]
        ordered = sorted(good_moves, reverse=True, key=lambda x: x[1])
        locs = [loc for (loc, count) in ordered]

        if locs:
            return locs[0]
        else:
            return None


class RadarRobot(Robot):
    def __init__(self, robot_id, current_x=None, current_y=None):
        super().__init__(robot_id, current_x, current_y)
        work_log.requested_radar(self.robot_id)

    def next_coords(self):
        global radar_idx
        global radar_targets
        if radar_idx < len(radar_targets):
            target = radar_targets[radar_idx]
            pos = self.small_step_from(target)

            if not pos:
                pos = self.random_dest_within(target[0] - 4, target[1] - 4, target[0] + 4, target[1] + 4)

            if not pos:
                pos = self.random_dest()

            (x, y) = pos
            self.target_x = x
            self.target_y = y
            print("Radar from list {0} from {1} got {2}".format(radar_idx, radar_targets[radar_idx], (x, y)),
                  file=sys.stderr)
            radar_idx += 1
        else:
            min_x = 2
            if turn < 50:
                max_x = width / 2
            else:
                max_x = width - 1
            min_y = 4
            max_y = height - 5

            (x, y) = self.random_dest_within(min_x, min_y, max_x, max_y)
            self.target_x = x
            self.target_y = y

    def turn(self, x, y, item):

        self.current_x = x
        self.current_y = y

        if not self.target_x or not self.target_y:
            self.next_coords()

        if item == RADAR and (x != self.target_x or y != self.target_y):
            print("MOVE {0} {1}".format(self.target_x, self.target_y))
            return self
        elif x == 0:
            print("REQUEST RADAR")
            work_log.dropped_radar()
            return self
        elif x == self.target_x and y == self.target_y:
            print("DIG {0} {1}".format(self.target_x, self.target_y))
            return SearchingRobot(self.robot_id, x, y)
        else:
            print("MOVE {0} {1}".format(0, self.target_y))
            return self


class TrapperRobot(Robot):
    def __init__(self, robot_id, current_x=None, current_y=None):
        super().__init__(robot_id, current_x, current_y)

    def next_coords(self):
        coords = self.with_most_ore() \
                 or self.random_dest_within(self.current_x - 4, self.current_y - 4, self.current_x + 4,
                                            self.current_y + 4) \
                 or self.random_dest_within(1, 0, 5, height - 1)

        (x, y) = coords
        self.target_x = x
        self.target_y = y
        work_log.register_work(self.robot_id, (x, y))

    def turn(self, x, y, item):
        self.current_x = x
        self.current_y = y

        # Not got a trap yet?
        if x == 0 and item != TRAP:
            print("REQUEST TRAP")
            self.next_coords()
            return self

        # Is this still a good idea?
        if not self.good_move((self.target_x, self.target_y)):
            self.next_coords()

        # Has something closer turned up?
        possible = self.with_most_ore()
        if possible and distance((x, y), possible) < distance((x, y), (self.target_x, self.target_y)):
            self.next_coords()

        # Move or dig
        if distance((x, y), (self.target_x, self.target_y)) > 4:
            print("MOVE {0} {1}".format(self.target_x, self.target_y))
            return self
        else:
            game_map.add_trap(self.target_x, self.target_y)
            print("DIG {0} {1}".format(self.target_x, self.target_y))
            return SearchingRobot(self.robot_id, x, y)


class ReturningRobot(Robot):
    def __init__(self, robot_id, current_x=None, current_y=None):
        super().__init__(robot_id, current_x, current_y)

    def turn(self, x, y, item):
        self.current_x = x
        self.current_y = y

        if x == 0:
            if not self.there_is_ore_out_there() and work_log.can_request_radar() and radar_cooldown <= 0:
                return RadarRobot(self.robot_id).turn(x, y, item)
            elif radar_cooldown <= 0 and random.randint(0, 5) == 0:
                return RadarRobot(self.robot_id, x, y).turn(x, y, item)
            elif trap_cooldown <= 0:
                return TrapperRobot(self.robot_id, x, y).turn(x, y, item)
            else:
                return SearchingRobot(self.robot_id, x, y).turn(x, y, item)
        else:
            print("MOVE 0 {0}".format(y))
            return self


class SearchingRobot(Robot):
    def __init__(self, robot_id, current_x=None, current_y=None):
        super().__init__(robot_id, current_x, current_y)
        self.last_dug = None
        self.miss_count = 0

    def next_coords(self):
        if self.current_x == 0:
            (x, y) = self.closest_with_ore((self.current_x, self.current_y)) \
                     or self.random_dest_within(4, self.current_y - 2, 4 + math.ceil(turn * (width - 4) / 200),
                                                self.current_y + 2)
        else:
            (x, y) = self.closest_with_ore((self.current_x, self.current_y)) \
                     or self.small_step_from_here() \
                     or self.random_dest_within(self.current_x - 4, self.current_y - 4, self.current_x + 4,
                                                self.current_y + 4) \
                     or self.random_dest()

        self.target_x = x
        self.target_y = y
        work_log.register_work(self.robot_id, (x, y))

    def turn(self, x, y, item):
        self.current_x = x
        self.current_y = y

        if not self.target_x or not self.target_y:
            self.next_coords()

        if item == ORE:
            # Found Ore
            return ReturningRobot(self.robot_id, x, y).turn(x, y, item)
        elif self.last_dug == (self.target_x, self.target_y):
            # Didn't find Ore
            self.next_coords()
            self.miss_count += 1

        # Still a good idea to mine here?
        if not self.good_move((self.target_x, self.target_y)):
            self.next_coords()

        # Has something closer turned up?
        possible = self.closest_with_ore((self.current_x, self.current_y))
        if possible and distance((x, y), possible) < distance((x, y), (self.target_x, self.target_y)):
            self.next_coords()

        # Have we dug up nothing for a few turns?
        if self.miss_count > 8 and radar_cooldown == 0 and work_log.can_request_radar():
            return ReturningRobot(self.robot_id).turn(x, y, item)

        # Mine or move to target
        if distance((x, y), (self.target_x, self.target_y)) > 4:
            print("MOVE {0} {1}".format(self.target_x, self.target_y))
            return self
        else:
            print("DIG {0} {1}".format(self.target_x, self.target_y))
            self.last_dug = (self.target_x, self.target_y)
            return self


class Map:
    def __init__(self):
        self.ore_map = {}
        self.hole_map = {}
        self.trap_map = {}
        self.radar_map = {}
        self.dodgy_map = {}

    def new_turn(self):
        self.ore_map = {}
        self.hole_map = {}

    def add_ore(self, x, y, val):
        if val == '?':
            ore = None
        else:
            ore = int(val)
        self.ore_map[(x, y)] = ore

    def add_hole(self, x, y):
        self.hole_map[(x, y)] = True

    def add_trap(self, x, y):
        self.trap_map[(x, y)] = True

    def add_radar(self, x, y):
        self.radar_map[(x, y)] = True

    def add_dodgy_square(self, x, y):
        self.dodgy_map[(x, y)] = True

    def is_trapped(self, loc):
        return self.trap_map.get(loc, False)

    def is_dodgy(self, loc):
        return self.dodgy_map.get(loc, False)

    def hole_at(self, loc):
        return self.hole_map.get(loc, False)

    def radar_at(self, loc):
        return self.radar_map.get(loc, False)

    def ore_count(self, x, y):
        return self.ore_map.get((x, y))

    def all_holes(self):
        return self.hole_map.keys()


class WorkLog:
    def __init__(self):
        self.robot_to_pos = {}
        self.history = []
        self.radar_requested = None

    def requested_radar(self, robot_id):
        print("Radar requested", file=sys.stderr)
        self.radar_requested = robot_id

    def dropped_radar(self):
        print("Radar dropped", file=sys.stderr)
        self.radar_requested = None

    def can_request_radar(self):
        print("Can request radar: {0}".format((self.radar_requested is None)), file=sys.stderr)
        return self.radar_requested is None

    def register_work(self, robot_id, pos):
        # Update history
        self.history.append(pos)

        self.robot_to_pos.pop(robot_id, None)

        # Create new reservation
        self.robot_to_pos[robot_id] = pos

    def is_unclaimed(self, robot_id, pos):
        ore = game_map.ore_count(*pos) or 1  # only one miner to unknown squares

        miners = [k for k, v in self.robot_to_pos.items() if v == pos and k != robot_id]
        return len(miners) < ore

    def is_claimed(self, robot_id, pos):
        return not self.is_unclaimed(robot_id, pos)


turn = 0

game_map = Map()
work_log = WorkLog()

robots = None


def go_team(first_id):
    global robots
    robots = {
                0 + first_id: RadarRobot(0 + first_id),
                1 + first_id: TrapperRobot(1 + first_id),
                2 + first_id: SearchingRobot(2 + first_id),
                3 + first_id: SearchingRobot(3 + first_id),
                4 + first_id: SearchingRobot(4 + first_id)
              }
    print(robots, file=sys.stderr)


# game loop
while True:
    turn += 1
    my_score, opponent_score = [int(i) for i in input().split()]

    game_map.new_turn()
    for i in range(height):
        inputs = input().split()
        for j in range(width):
            # ore: amount of ore or "?" if unknown
            # hole: 1 if cell has a hole
            lore = inputs[2 * j]
            hole = int(inputs[2 * j + 1])
            game_map.add_ore(j, i, lore)
            if hole:
                game_map.add_hole(j, i)

    # entity_count: number of entities visible to you
    # radar_cooldown: turns left until a new radar can be requested
    # trap_cooldown: turns left until a new trap can be requested
    entity_count, radar_cooldown, trap_cooldown = [int(i) for i in input().split()]

    robot_locations = []
    for i in range(entity_count):
        # entity_id: unique id of the entity
        # entity_type: 0 for your robot, 1 for other robot, 2 for radar, 3 for trap
        # x y: position of the entity
        # item: if this entity is a robot, the item it is carrying (-1 for NONE, 2 for RADAR, 3 for TRAP, 4 for ORE)

        # WAIT|MOVE x y|DIG x y|REQUEST item
        entity_id, entity_type, lx, ly, litem = [int(j) for j in input().split()]

        if entity_type == TRAP:
            game_map.add_trap(lx, ly)

        if entity_type == RADAR:
            game_map.add_radar(lx, ly)

        if entity_type == ENEMY_ROBOT:
            game_map.add_dodgy_square(lx, ly)

        if entity_type == MY_ROBOT:
            if not robots:
                go_team(entity_id)

            robot_locations.append((entity_id, lx, ly, litem))
            # print("{0}".format(entity_id), file=sys.stderr)

    for (entity_id, rx, ry, litem) in robot_locations:
        robot = robots[entity_id]
        robots[entity_id] = robot.turn(rx, ry, litem)
