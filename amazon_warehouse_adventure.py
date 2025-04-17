#!/usr/bin/env python3
"""
amazon_warehouse_adventure.py: A witty, challenging text adventure game set in a working Amazon warehouse full of robots.
"""
import sys
import random
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def colorize(text, color):
    return f"{color}{text}{Colors.ENDC}"


class Room:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description
        self.exits = {}    # direction -> room id
        self.items = []    # item ids present in the room


class Item:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description


class Player:
    def __init__(self):
        self.inventory = []  # list of item ids


class Game:
    # Grid size for expanded world (20×25 = 500 rooms)
    GRID_WIDTH = 20
    GRID_HEIGHT = 25

    def __init__(self):
        # Build grid of generic rooms
        self.grid = {}
        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):
                rid = f"sec_{x}_{y}"
                name = f"Section {x},{y}"
                desc = f"A generic warehouse section at coordinates ({x},{y}). Endless shelves and mysterious boxes."
                self.grid[(x, y)] = Room(rid, name, desc)
        # Special rooms with unique descriptions
        self.grid[(0, 0)] = Room('dock', 'Receiving Dock',
            'You stand at the Receiving Dock: towering shelves loom overhead, a conveyor belt hums rhythmically, and a lone janitor robot, Model J-12, sweeps the floor with mechanical precision.')
        self.grid[(1, 0)] = Room('sorting', 'Sorting Area',
            'Rows of packages stretch into infinity. Sorting robots whirr around in synchronized chaos. At the far end, a guard robot, Model G-01, bars access to the Maintenance Bay.')
        self.grid[(1, 1)] = Room('maintenance', 'Maintenance Bay',
            'Sparks dance in the dim Maintenance Bay. Tools hang like trophies on the walls. A crate marked "FRAGILE" sits in the center, slightly ajar.')
        self.grid[(2, 0)] = Room('packaging', 'Packaging Zone',
            'Bulky robotic arms seal boxes in plastic wrap, while a half-assembled shipping robot lies dormant, sparks flickering from its torso.')
        self.grid[(3, 0)] = Room('dispatch', 'Dispatch Zone',
            'Shipping trucks line up beyond a massive sliding door, engines idling. You can almost taste freedom...')

        # Items
        self.items = {
            'access_card': Item('access_card', 'access card',
                'A glossy plastic access card. It reads: "Maintenance Bay Code: 472".'),
            'screwdriver': Item('screwdriver', 'screwdriver',
                'A heavy-duty screwdriver, perfect for tightening bolts.')
        }
        # Place items in grid
        self.grid[(0, 0)].items.append('access_card')
        self.grid[(1, 1)].items.append('screwdriver')

        # Player state
        self.player = Player()
        self.x, self.y = 0, 0
        self.guard_attempts = 0
        self.guard_solved = False
        self.robot_fixed = False
        # Fog of war: track visited coordinates
        self.visited = {(self.x, self.y)}

    def play(self):
        print('\nWelcome to the Amazon Warehouse Adventure!')
        print('Type "help" for a list of commands.\n')
        self.describe_current_room()
        while True:
            command = input(colorize('> ', Colors.OKBLUE)).strip()
            if not command:
                continue
            cmd = command.lower().split()
            if cmd[0] in ('quit', 'exit', 'q'):
                print('Thanks for playing. Stay out of HR trouble!')
                break
            self.process_command(command)

    def describe_current_room(self):
        room = self.current_room
        print(f"\n{colorize(room.name, Colors.OKCYAN)}")
        print(colorize('-' * len(room.name), Colors.OKCYAN))
        print(room.description)
        if room.items:
            names = [colorize(self.items[i].name, Colors.WARNING) for i in room.items]
            print('You see here: ' + ', '.join(names) + '.')
        exits = ', '.join([colorize(dir, Colors.OKGREEN) for dir in room.exits.keys()])
        print('Exits: ' + exits + '.')
        # Display ASCII map with highlighted current location
        self.display_map()
    def process_command(self, command):
        cmd = command.lower().strip()
        # fun random commands
        if cmd in ('dance', 'boogie'):
            self.do_dance()
            return
        if cmd == 'sing':
            self.do_sing()
            return
        if cmd in ('complain', 'whine'):
            self.do_complain()
            return
        if cmd in ('bug', 'report bug'):
            self.do_bug_report()
            return
        if cmd == 'status':
            self.do_status()
            return
        if cmd in ('help', 'h', '?'):
            self.show_help()
        elif cmd in ('look', 'l'):
            self.describe_current_room()
        elif cmd in ('inventory', 'i'):
            self.show_inventory()
        elif cmd.startswith(('inspect ', 'examine ')):
            self.inspect_item(cmd)
        elif cmd.startswith(('take ', 'get ')):
            self.take_item(cmd)
        elif cmd.startswith('use '):
            self.use_item(cmd)
        else:
            parts = cmd.split()
            if parts[0] == 'go' and len(parts) > 1:
                self.move(parts[1])
            elif parts[0] in ('north', 'south', 'east', 'west', 'n', 's', 'e', 'w'):
                self.move(parts[0])
            else:
                print(colorize("I don't understand that command. Type 'help' for assistance.", Colors.FAIL))

    def show_help(self):
        print('\nCommands:')
        print('  move/go [north|south|east|west]')
        print('  look (l)')
        print('  inspect/examine [item]')
        print('  take/get [item]')
        print('  use [item] on [target]')
        print('  inventory (i)')
        print('  quit (q)')

    def show_inventory(self):
        if not self.player.inventory:
            print('Your inventory is empty.')
        else:
            names = [self.items[i].name for i in self.player.inventory]
            print('You are carrying: ' + ', '.join(names) + '.')

    def move(self, direction):
        dir_map = {'n': 'north', 's': 'south', 'e': 'east', 'w': 'west'}
        d = dir_map.get(direction, direction)
        # Guard puzzle at Sorting Area
        if self.current_room.id == 'sorting' and d == 'south' and not self.guard_solved:
            self.guard_puzzle()
            if not self.guard_solved:
                return
        # Robot block at Packaging Zone
        if self.current_room.id == 'packaging' and d == 'east' and not self.robot_fixed:
            print('The shipping robot blocks your way, its systems dead. You must fix it first.')
            return
        if d in self.current_room.exits:
            self.current_room = self.rooms[self.current_room.exits[d]]
            self.describe_current_room()
            if self.current_room.id == 'dispatch':
                print(colorize('\nWith a triumphant beep, the shipping robot activates and the door slides open. You roll out into freedom. You win!', Colors.OKGREEN))
                sys.exit(0)
        else:
            print(colorize("You can't go that way.", Colors.FAIL))

    def guard_puzzle(self):
        print(colorize('A guard robot buzzes: "Enter the 3-digit Maintenance Bay code or be detained."', Colors.WARNING))
        while self.guard_attempts < 3:
            choice = input('Enter code: ').strip()
            if choice == '472':
                print(colorize('"Access granted," the robot hums and steps aside respectfully.', Colors.OKGREEN))
                self.guard_solved = True
                return
            else:
                self.guard_attempts += 1
                if self.guard_attempts < 3:
                    print(colorize('Access denied. The robot glows red.', Colors.FAIL))
                else:
                    print(colorize('Alarm sounds! Security drones surround you. You have been detained. Game over.', Colors.FAIL))
                    sys.exit(0)

    def inspect_item(self, cmd):
        target = cmd.split(' ', 1)[1]
        item = self.find_item(target, include_room=False)
        if not item:
            item = self.find_item(target, include_room=True)
        if item:
            print(item.description)
        else:
            print("You don't see that here.")

    def take_item(self, cmd):
        target = cmd.split(' ', 1)[1]
        found = None
        for iid in list(self.current_room.items):
            it = self.items[iid]
            if target in it.name.lower() or target == iid:
                found = iid
                break
        if found:
            self.current_room.items.remove(found)
            self.player.inventory.append(found)
            print(f'You take the {self.items[found].name}.')
        else:
            print("You don't see that here.")

    def use_item(self, cmd):
        if ' on ' not in cmd:
            print("Use what on what? Try 'use screwdriver on robot'.")
            return
        parts = cmd.split(' on ')
        item_name = parts[0][len('use '):].strip()
        target = parts[1].strip()
        # Find item in inventory
        item = None
        for iid in self.player.inventory:
            it = self.items[iid]
            if item_name in it.name.lower() or item_name == iid:
                item = it
                break
        if not item:
            print("You don't have that item.")
            return
        # Specific use cases
        if item.id == 'screwdriver' and 'robot' in target and self.current_room.id == 'packaging':
            if not self.robot_fixed:
                print('You tighten the bolts, reconnect loose wires, and the shipping robot whirs to life!')
                self.robot_fixed = True
            else:
                print('The robot is already operational.')
        else:
            print('Nothing happens.')

    def find_item(self, target, include_room):
        t = target.lower()
        for iid, it in self.items.items():
            name = it.name.lower()
            if t == iid or t in name:
                if include_room and iid in self.current_room.items:
                    return it
                if not include_room and iid in self.player.inventory:
                    return it
        return None
    # Random fun commands
    def do_dance(self):
        moves = [
            "You attempt the Macarena. The robots watch, unblinking, politely confused.",
            "You break into the robot boogie. Conveyor belts pause to admire your moves.",
            "You moonwalk across the polished floor. Even the guard robot nods in approval."
        ]
        print(colorize(random.choice(moves), Colors.OKBLUE))

    def do_sing(self):
        songs = [
            "\"I Will Survive\" echoes off the shelves as a sorting robot hums along.",
            "You belt out \"Under Pressure\". Now everyone's feeling it: pressure to stop singing.",
            "You sing a robot lullaby. A nearby janitor bot drifts into standby mode."
        ]
        print(colorize(random.choice(songs), Colors.OKCYAN))

    def do_complain(self):
        complaints = [
            "\"These packages aren't going to sort themselves,\" you grumble.",
            "\"When's lunch?\" you whine. The robots ignore you.",
            "\"My back hurts from all this walking,\" you moan. The conveyor belt shudders sympathetically."
        ]
        print(colorize(random.choice(complaints), Colors.WARNING))

    def do_bug_report(self):
        reports = [
            "You file an imaginary bug report. Debug information: You are tired.",
            "You tell support that the guard robot is too polite. They respond with automated empathy.",
            "You email warehouse IT: 'Screwdriver doesn't fit my life issues.' No reply."
        ]
        print(colorize(random.choice(reports), Colors.HEADER))

    def do_status(self):
        loc = colorize(self.current_room.name, Colors.OKGREEN)
        inv = ', '.join([self.items[i].name for i in self.player.inventory]) or 'nothing'
        inv = colorize(inv, Colors.WARNING)
        print(colorize(f"Location: {loc}. Inventory: {inv}.", Colors.OKGREEN))
    
    def display_map(self):
        """Display an ASCII map with the current location highlighted."""
        layout = [
            " [dock]---[sorting]---[packaging]---[dispatch]",
            "             |",
            "        [maintenance]"
        ]
        for line in layout:
            mapped = line
            for room_id in ['dock', 'sorting', 'packaging', 'dispatch', 'maintenance']:
                placeholder = f"[{room_id}]"
                if placeholder in mapped:
                    if room_id == self.current_room.id:
                        colored = colorize(placeholder, Colors.OKGREEN)
                    else:
                        colored = colorize(placeholder, Colors.OKBLUE)
                    mapped = mapped.replace(placeholder, colored)
            print(mapped)


if __name__ == '__main__':
    Game().play()