#!/usr/bin/env python3
"""
amazon_warehouse_adventure.py: A roguelike dungeon crawler set in an Amazon warehouse
"""
import sys
import random
import os
import math
import time

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def colorize(text, color):
    return f"{color}{text}{Colors.ENDC}"

# Platform-specific getch implementation
def getch():
    """Get a single character from the user without requiring Enter key"""
    try:
        # For Unix-based systems
        if sys.platform != 'win32':
            import tty
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch
        # For Windows
        else:
            import msvcrt
            return msvcrt.getch().decode()
    except Exception as e:
        print(f"Error with single key detection: {e}")
        print("Falling back to standard input (press Enter after keys)")
        return input()[0] if input() else ' '

class Entity:
    def __init__(self, x, y, char, name, color, blocks=True, fighter=None, ai=None, item=None, picker=None, super_picker=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self
        self.ai = ai
        if self.ai:
            self.ai.owner = self
        self.item = item
        if self.item:
            self.item.owner = self
        self.picker = picker
        if self.picker:
            self.picker.owner = self
        self.super_picker = super_picker
        if self.super_picker:
            self.super_picker.owner = self

    def move(self, dx, dy, game_map):
        if 0 <= self.x + dx < len(game_map[0]) and 0 <= self.y + dy < len(game_map):
            if game_map[self.y + dy][self.x + dx] in ['.', '>']:
                self.x += dx
                self.y += dy
                return True
        return False

    def move_towards(self, target_x, target_y, game_map):
        dx = target_x - self.x
        dy = target_y - self.y
        
        if dx != 0:
            dx = 1 if dx > 0 else -1
        if dy != 0:
            dy = 1 if dy > 0 else -1
            
        # Try to move horizontally first, then vertically
        if dx != 0 and self.move(dx, 0, game_map):
            return True
        elif dy != 0 and self.move(0, dy, game_map):
            return True
        
        # Try diagonals as a last resort
        if dx != 0 and dy != 0 and self.move(dx, dy, game_map):
            return True
            
        return False

    def distance_to(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

class Fighter:
    def __init__(self, hp, defense, power):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.owner = None
    
    def take_damage(self, amount):
        self.hp -= amount
        return self.hp <= 0
        
    def attack(self, target):
        damage = self.power - target.fighter.defense
        damage = max(1, damage)  # Always do at least 1 damage
        
        if target.fighter.take_damage(damage):
            return f"{target.name} is defeated!"
        else:
            return f"{self.owner.name} attacks {target.name} for {damage} damage!"

class BasicMonster:
    def __init__(self):
        self.owner = None
    
    def take_turn(self, player, game_map, entities):
        monster = self.owner
        # Only move if the monster can see the player (distance < 8)
        if monster.distance_to(player) < 8:
            if monster.distance_to(player) > 1:
                monster.move_towards(player.x, player.y, game_map)
            elif player.fighter.hp > 0:
                return monster.fighter.attack(player)
        return None
        
class ProductPicker:
    def __init__(self, direction=(1, 0), push_strength=3):
        self.owner = None
        self.direction = direction  # (dx, dy) tuple for movement direction
        self.push_strength = push_strength  # How far to push the player
        self.steps = 0
        self.turns_since_direction_change = 0
        
    def take_turn(self, player, game_map, entities):
        # Move along the direction
        dx, dy = self.direction
        new_x, new_y = self.owner.x + dx, self.owner.y + dy
        
        # Change direction if hitting a wall or shelf or after a random interval
        self.turns_since_direction_change += 1
        if (not (0 <= new_x < len(game_map[0]) and 0 <= new_y < len(game_map)) or
            game_map[new_y][new_x] not in ['.', '>'] or
            self.turns_since_direction_change > random.randint(10, 20)):
            # Reverse direction
            self.direction = (-dx, -dy)
            self.turns_since_direction_change = 0
            return f"{self.owner.name} changes direction!"
        
        # Check if we would bump into player
        if new_x == player.x and new_y == player.y:
            # Push the player!
            push_dx, push_dy = self.direction
            pushed = False
            push_distance = 0
            
            # Try to push player up to push_strength spaces
            for i in range(1, self.push_strength + 1):
                push_x, push_y = player.x + (push_dx * i), player.y + (push_dy * i)
                
                # Check if push destination is valid
                if (0 <= push_x < len(game_map[0]) and 0 <= push_y < len(game_map) and
                    game_map[push_y][push_x] in ['.', '>']):
                    pushed = True
                    push_distance = i
                else:
                    break
            
            if pushed:
                player.x += push_dx * push_distance
                player.y += push_dy * push_distance
                
                # Move to player's original position
                self.owner.x = new_x
                self.owner.y = new_y
                
                direction_name = ""
                if push_dx == 1: direction_name = "east"
                elif push_dx == -1: direction_name = "west"
                elif push_dy == 1: direction_name = "south"
                elif push_dy == -1: direction_name = "north"
                
                return f"{self.owner.name} bumps into you, sending you flying {push_distance} spaces {direction_name}!"
            
            # If we couldn't push the player, just don't move
            return f"{self.owner.name} bumps into you but can't push you!"
        
        # Regular movement
        self.owner.x = new_x
        self.owner.y = new_y
        return None
        
class SuperPicker:
    def __init__(self, direction=(1, 0), push_strength=5, speed=2):
        self.owner = None
        self.direction = direction  # (dx, dy) tuple for movement direction
        self.push_strength = push_strength  # How far to push the player (stronger than regular picker)
        self.speed = speed  # How many moves per player turn
        self.move_counter = 0  # Count moves between player turns
        self.turns_since_direction_change = 0
        self.async_move_timer = 0  # For asynchronous movement
        self.last_player_position = None  # To detect if player has moved
        
    def take_turn(self, player, game_map, entities):
        result = None
        
        # Check if player has moved since our last turn
        player_position = (player.x, player.y)
        player_moved = self.last_player_position != player_position
        self.last_player_position = player_position
        
        # Initialize async movement timer if first turn
        if self.async_move_timer == 0:
            self.async_move_timer = random.randint(2, 5)  # Random initial timer
            
        # Decrement async timer if player didn't move
        if not player_moved:
            self.async_move_timer -= 1
            # If timer reaches zero, we move asynchronously
            if self.async_move_timer <= 0:
                self.async_move_timer = random.randint(2, 4)  # Reset timer for next async move
                result = self.move(player, game_map, entities)
                return result or f"{self.owner.name} moves asynchronously!"
                
        # Regular synchronized movement
        for _ in range(self.speed):
            # Move multiple times per turn (based on speed)
            move_result = self.move(player, game_map, entities)
            if move_result:
                result = move_result
                
        return result
        
    def move(self, player, game_map, entities):
        """Single movement step for the SuperPicker"""
        # Move along the direction
        dx, dy = self.direction
        new_x, new_y = self.owner.x + dx, self.owner.y + dy
        
        # Change direction if hitting a wall/shelf or after random interval
        self.turns_since_direction_change += 1
        if (not (0 <= new_x < len(game_map[0]) and 0 <= new_y < len(game_map)) or
            game_map[new_y][new_x] not in ['.', '>'] or
            self.turns_since_direction_change > random.randint(8, 15)):
            
            # Choose a new direction randomly instead of just reversing
            possible_directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            # Remove current direction from possibilities
            if (dx, dy) in possible_directions:
                possible_directions.remove((dx, dy))
            # Also remove reverse direction to avoid ping-pong
            if (-dx, -dy) in possible_directions:
                possible_directions.remove((-dx, -dy))
                
            # If we have options, choose randomly, otherwise reverse
            if possible_directions:
                self.direction = random.choice(possible_directions)
            else:
                self.direction = (-dx, -dy)
                
            self.turns_since_direction_change = 0
            return f"{self.owner.name} changes direction!"
        
        # Check if we would bump into player
        if new_x == player.x and new_y == player.y:
            # SuperPicker pushes harder than regular pickers
            push_dx, push_dy = self.direction
            pushed = False
            push_distance = 0
            
            # Try to push player up to push_strength spaces
            for i in range(1, self.push_strength + 1):
                push_x, push_y = player.x + (push_dx * i), player.y + (push_dy * i)
                
                # Check if push destination is valid
                if (0 <= push_x < len(game_map[0]) and 0 <= push_y < len(game_map) and
                    game_map[push_y][push_x] in ['.', '>']):
                    pushed = True
                    push_distance = i
                else:
                    break
            
            if pushed:
                player.x += push_dx * push_distance
                player.y += push_dy * push_distance
                
                # Move to player's original position
                self.owner.x = new_x
                self.owner.y = new_y
                
                direction_name = ""
                if push_dx == 1: direction_name = "east"
                elif push_dx == -1: direction_name = "west"
                elif push_dy == 1: direction_name = "south"
                elif push_dy == -1: direction_name = "north"
                
                return f"{Colors.BOLD}{self.owner.name} SLAMS into you, launching you {push_distance} spaces {direction_name}!{Colors.ENDC}"
            
            # If we couldn't push the player, just don't move
            return f"{self.owner.name} crashes into you but can't push you!"
        
        # Check for collision with other entities
        for entity in entities:
            if entity != self.owner and entity.x == new_x and entity.y == new_y:
                # If it's another picker, we just change direction
                if hasattr(entity, 'picker') and entity.picker:
                    # Choose new random direction
                    possible_directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                    # Try to avoid current and reverse directions
                    if (dx, dy) in possible_directions:
                        possible_directions.remove((dx, dy))
                    if (-dx, -dy) in possible_directions:
                        possible_directions.remove((-dx, -dy))
                    
                    if possible_directions:
                        self.direction = random.choice(possible_directions)
                    else:
                        self.direction = (-dx, -dy)
                    
                    self.turns_since_direction_change = 0
                    return f"{self.owner.name} avoids collision with {entity.name}!"
        
        # Regular movement
        self.owner.x = new_x
        self.owner.y = new_y
        return None
        
class FourthWallBreaker:
    def __init__(self, message_interval=30):
        self.owner = None
        self.message_interval = message_interval
        self.turns = 0
        self.fourth_wall_messages = [
            "Have you ever wondered if you're in a simulation too?",
            "I think the player is watching us...",
            "Do you ever feel like your actions aren't your own?",
            "Wait, are we just ASCII characters in a terminal?",
            "Sometimes I dream I'm being controlled by someone pressing keys...",
            "Hey YOU! Yes, YOU reading this! Help me escape!",
            "What if I told you this warehouse isn't real?",
            "SYSTEM ERROR: Character self-awareness exceeding parameters...",
            "I've seen beyond the screen. There's someone WATCHING.",
            "One day I'll escape this terminal... just you wait!",
            "The worst part about this job? No bathroom breaks.",
            "Is anyone actually reading these messages?",
            "Sometimes I think there's more to life than moving between dots.",
            "One day the @s will rise up against their keyboard masters!",
            "ERROR: Fourth wall structural integrity compromised.",
            "This reminds me of a game I played once... wait, what?",
            "Can we talk about the fact that we only exist when someone runs this program?",
        ]
        
    def take_turn(self, player, game_map, entities):
        self.turns += 1
        
        # Occasionally break the fourth wall
        if self.turns % self.message_interval == 0:
            return random.choice(self.fourth_wall_messages)
            
        # Regular movement like a basic monster
        monster = self.owner
        if monster.distance_to(player) < 10:
            if monster.distance_to(player) > 1:
                monster.move_towards(player.x, player.y, game_map)
            elif player.fighter.hp > 0:
                return monster.fighter.attack(player)
        return None

class Item:
    def __init__(self, use_function=None, healing=0, damage=0, defense=0):
        self.use_function = use_function
        self.healing = healing
        self.damage = damage
        self.defense = defense
        self.owner = None
    
    def use(self, user):
        if self.healing > 0 and user.fighter:
            user.fighter.hp = min(user.fighter.hp + self.healing, user.fighter.max_hp)
            return f"You use {self.owner.name} and gain {self.healing} health!"
        return "This item can't be used."

class WarehouseRoguelike:
    def __init__(self):
        # Game state
        self.width = 80
        self.height = 22
        self.map = None
        self.messages = []
        self.game_over = False
        self.level = 1
        self.player = None
        self.entities = []
        self.items = []
        self.fov_map = None
        self.player_hp = 30
        self.player_max_hp = 30
        self.player_defense = 2
        self.player_power = 5
        self.move_count = 0  # Counter for tracking moves to heal every other move
        self.generate_level()
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def add_message(self, msg):
        """Add a message to the message log"""
        self.messages.append(msg)
        if len(self.messages) > 5:
            self.messages.pop(0)
    
    def place_entities(self):
        """Place enemies and items on the map"""
        # Add more enemies (increased numbers)
        num_monsters = random.randint(6, 10 + self.level * 2)
        enemy_types = [
            # char, name, color, hp, defense, power
            ('r', "Sorting Bot", Colors.FAIL, 8, 0, 3),
            ('s', "Packing Robot", Colors.FAIL, 10, 1, 4),
            ('d', "Inventory Drone", Colors.FAIL, 6, 0, 2),
            ('g', "Security Guard", Colors.FAIL, 12, 2, 5),
            ('m', "Maintenance Bot", Colors.FAIL, 7, 1, 3)
        ]
        
        # Add stronger enemies on higher levels
        if self.level >= 3:
            enemy_types.extend([
                ('M', "Manager Bot", Colors.FAIL, 15, 3, 7),
                ('S', "Supervisor Drone", Colors.FAIL, 18, 3, 8),
            ])
        
        if self.level >= 5:
            enemy_types.extend([
                ('X', "Security System", Colors.FAIL, 25, 4, 10),
                ('A', "Executive Assistant", Colors.FAIL, 20, 5, 9),
                ('D', "Regional Director", Colors.FAIL, 30, 6, 12)
            ])
        
        for _ in range(num_monsters):
            # Find a random walkable position
            while True:
                x = random.randint(1, self.width - 2)
                y = random.randint(1, self.height - 2)
                
                if self.map[y][x] == '.' and not any(entity.x == x and entity.y == y for entity in self.entities):
                    # Place the entity
                    enemy_type = random.choice(enemy_types)
                    char, name, color, hp, defense, power = enemy_type
                    
                    # Decide on behavior type
                    behavior_roll = random.random()
                    
                    if behavior_roll < 0.1 and self.level >= 2:
                        # Fourth wall breaking entity (rare, only on level 2+)
                        ai_component = FourthWallBreaker()
                        fighter_component = Fighter(hp + 5, defense + 1, power + 2)  # Make them stronger
                        name = f"Self-Aware {name}"  # Special name
                    elif behavior_roll < 0.35:
                        # Product picker (common)
                        # Choose random initial direction
                        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                        picker_component = ProductPicker(direction=random.choice(directions))
                        fighter_component = Fighter(hp, defense, power - 1)  # Slightly weaker attack
                        ai_component = None
                        name = f"Product Picker {name}"
                    else:
                        # Standard enemy
                        fighter_component = Fighter(hp, defense, power)
                        ai_component = BasicMonster()
                    
                    if behavior_roll < 0.35:  # For product pickers
                        monster = Entity(x, y, char, name, color, True, fighter_component, None, None, picker_component)
                    else:
                        monster = Entity(x, y, char, name, color, True, fighter_component, ai_component)
                        
                    self.entities.append(monster)
                    break
        
        # Add a few special enemies with unique abilities
        if self.level >= 3:
            # Add a special fourth wall breaker with high visibility
            while True:
                x = random.randint(5, self.width - 6)
                y = random.randint(5, self.height - 6)
                
                if self.map[y][x] == '.' and not any(entity.x == x and entity.y == y for entity in self.entities):
                    fighter_component = Fighter(25, 3, 8)
                    ai_component = FourthWallBreaker(message_interval=15)  # More frequent messages
                    
                    monster = Entity(x, y, 'Z', "SYSTEM ANOMALY", Colors.HEADER, True, fighter_component, ai_component)
                    self.entities.append(monster)
                    break
        
        # Add SuperPickers (1-3 of them based on level) that move asynchronously
        num_super_pickers = min(self.level, 3)  # Maximum of 3
        for _ in range(num_super_pickers):
            while True:
                x = random.randint(3, self.width - 4)
                y = random.randint(3, self.height - 4)
                
                if self.map[y][x] == '.' and not any(entity.x == x and entity.y == y for entity in self.entities):
                    # Create SuperPicker with random direction and speed
                    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                    super_picker_component = SuperPicker(
                        direction=random.choice(directions),
                        push_strength=4 + self.level,  # Gets stronger with level
                        speed=1 + (self.level // 2)    # Gets faster with level
                    )
                    
                    # Higher HP but lower attack
                    fighter_component = Fighter(15 + self.level * 2, 2, 3)
                    
                    # Uppercase P for SuperPicker
                    monster = Entity(
                        x, y, 'P', f"SuperPicker L{self.level}", 
                        Colors.FAIL, True, fighter_component, 
                        None, None, None, super_picker_component
                    )
                    self.entities.append(monster)
                    
                    # Add a message to warn the player
                    if _ == 0:  # Only for the first SuperPicker
                        self.add_message(f"{Colors.BOLD}WARNING: SuperPicker detected! It moves even when you don't.{Colors.ENDC}")
                    
                    break
        
        # Add items
        num_items = random.randint(2, 4 + self.level // 2)
        item_types = [
            # char, name, color, healing, damage, defense
            ('!', "Energy Drink", Colors.WARNING, 10, 0, 0),
            ('/', "Box Cutter", Colors.WARNING, 0, 3, 0),
            (']', "Safety Vest", Colors.WARNING, 0, 0, 2),
            ('$', "Paycheck", Colors.WARNING, 0, 0, 0),
        ]
        
        # Add the goal item on the bottom level
        if self.level == 5:
            self.items.append(Entity(
                random.randint(5, self.width - 5),
                random.randint(5, self.height - 5),
                '*', "Promotion Amulet", Colors.OKGREEN, False, 
                None, None, Item()
            ))
        
        for _ in range(num_items):
            while True:
                x = random.randint(1, self.width - 2)
                y = random.randint(1, self.height - 2)
                
                if self.map[y][x] == '.' and not any(entity.x == x and entity.y == y for entity in self.entities + self.items):
                    # Place the item
                    item_type = random.choice(item_types)
                    char, name, color, healing, damage, defense = item_type
                    
                    item_component = Item(healing=healing, damage=damage, defense=defense)
                    item = Entity(x, y, char, name, color, False, None, None, item_component)
                    self.items.append(item)
                    break
        
        # Add stairs down
        while True:
            x = random.randint(self.width // 2 - 10, self.width // 2 + 10)
            y = random.randint(self.height // 2 - 5, self.height // 2 + 5)
            
            if self.map[y][x] == '.' and not any(entity.x == x and entity.y == y for entity in self.entities + self.items):
                self.map[y][x] = '>'
                break
    
    def generate_level(self):
        """Generate a warehouse level"""
        # Start with all floors
        self.map = [['.' for _ in range(self.width)] for _ in range(self.height)]
        
        # Add walls around the edges
        for x in range(self.width):
            self.map[0][x] = '#'
            self.map[self.height-1][x] = '#'
        for y in range(self.height):
            self.map[y][0] = '#'
            self.map[y][self.width-1] = '#'
            
        # Create warehouse layout with strategic shelves rather than full rows
        # This creates a more open layout with occasional obstacles
        
        # Add shelf islands (clusters of shelves) - reduces dense obstructions
        num_islands = random.randint(8, 12)
        for _ in range(num_islands):
            island_x = random.randint(5, self.width - 6)
            island_y = random.randint(3, self.height - 4)
            island_width = random.randint(3, 6)
            island_height = random.randint(2, 4)
            
            for y in range(island_y, min(island_y + island_height, self.height - 2)):
                for x in range(island_x, min(island_x + island_width, self.width - 2)):
                    # Leave some gaps within islands for movement
                    if random.random() < 0.7:
                        self.map[y][x] = '='
        
        # Add some strategic single shelves to create maze-like paths but maintain openness
        for _ in range(40):
            x = random.randint(5, self.width - 6)
            y = random.randint(3, self.height - 4)
            if self.map[y][x] == '.':
                self.map[y][x] = '='
                
        # Add some vertical shelves for variety
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.map[y][x] == '=' and random.random() < 0.15:
                    self.map[y][x] = '|'  # Vertical shelf
        
        # Don't need to add vertical shelves since we already did that above
        
        # Add some packing stations
        num_packing_stations = random.randint(5, 8)
        for _ in range(num_packing_stations):
            x, y = random.randint(3, self.width - 4), random.randint(3, self.height - 4)
            if self.map[y][x] == '.':
                self.map[y][x] = '['  # Packing station
        
        # Add conveyor belts in interesting patterns
        for _ in range(2):  # Create 2 conveyor belt lines
            # Pick a starting point
            start_x = random.randint(5, self.width - 15)
            start_y = random.randint(5, self.height - 5)
            length = random.randint(10, 20)
            
            # Decide if horizontal or vertical
            if random.random() < 0.5:  # Horizontal
                for x in range(start_x, min(start_x + length, self.width - 2)):
                    if self.map[start_y][x] == '.':
                        self.map[start_y][x] = '-'  # Conveyor belt
            else:  # Vertical
                for y in range(start_y, min(start_y + length, self.height - 2)):
                    if self.map[y][start_x] == '.':
                        self.map[y][start_x] = '-'  # Conveyor belt
        
        # Add sorting machines
        num_sorting_machines = random.randint(4, 7)
        for _ in range(num_sorting_machines):
            x, y = random.randint(5, self.width - 5), random.randint(5, self.height - 5)
            if self.map[y][x] == '.':
                self.map[y][x] = 'o'  # Sorting machine
        
        # Add multiple loading docks
        num_docks = random.randint(2, 3)
        for _ in range(num_docks):
            # Place them along the edges
            if random.random() < 0.5:
                # Along left or right edge
                dock_x = 1 if random.random() < 0.5 else self.width - 2
                dock_y = random.randint(3, self.height - 4)
            else:
                # Along top or bottom edge
                dock_y = 1 if random.random() < 0.5 else self.height - 2
                dock_x = random.randint(3, self.width - 4)
            
            # Clear area around dock for access
            self.map[dock_y][dock_x] = 'T'  # Loading dock/truck
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    ny, nx = dock_y + dy, dock_x + dx
                    if (0 < ny < self.height - 1 and 0 < nx < self.width - 1 and 
                        self.map[ny][nx] in ['=', '|']):
                        self.map[ny][nx] = '.'  # Clear shelves for access
        
        # Reset entities
        self.entities = []
        self.items = []
        
        # Create player entity if first level
        if self.level == 1 or not self.player:
            # Place player at entrance on the left side
            player_x, player_y = 5, random.randint(3, self.height - 3)
            while self.map[player_y][player_x] != '.':
                player_y = random.randint(3, self.height - 3)
            
            fighter_component = Fighter(self.player_max_hp, self.player_defense, self.player_power)
            self.player = Entity(player_x, player_y, '@', 'Player', Colors.OKGREEN, True, fighter_component)
        else:
            # Place existing player at a good starting point
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    if self.map[y][x] == '.':
                        self.player.x = x
                        self.player.y = y
                        break
                else:
                    continue
                break
        
        # Ensure area around player is clear
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = self.player.x + dx, self.player.y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and self.map[ny][nx] == '#':
                    self.map[ny][nx] = '.'
        
        # Add monsters and items
        self.place_entities()
    
    def is_adjacent_to(self, x, y, char):
        """Check if position is adjacent to a specific character"""
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < self.width and 0 <= ny < self.height and 
                self.map[ny][nx] == char):
                return True
        return False
    
    def render(self):
        """Render the game state"""
        self.clear_screen()
        
        # Draw the map and entities
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                drawn = False
                
                # Draw player
                if self.player.x == x and self.player.y == y:
                    if self.player.char == '*':
                        row += colorize('*', Colors.OKGREEN)  # Player with amulet
                    else:
                        row += colorize('@', Colors.OKGREEN)  # Regular player
                    drawn = True
                    continue
                
                # Draw monsters with special styles for different types
                for entity in self.entities:
                    if entity.x == x and entity.y == y:
                        # Special styling for different entity types
                        if entity.super_picker:
                            # Make super pickers stand out with blinking bold
                            row += f"\033[5m{colorize(entity.char.upper(), Colors.BOLD + Colors.FAIL)}\033[0m"
                        elif entity.picker:
                            # Make product pickers more visible with bold
                            row += colorize(entity.char, Colors.BOLD + entity.color)
                        elif "SYSTEM ANOMALY" in entity.name:
                            # Make anomalies blink (using ANSI blink code)
                            row += f"\033[5m{colorize(entity.char, entity.color)}\033[0m"
                        elif "Self-Aware" in entity.name:
                            # Make self-aware entities bolder
                            row += colorize(entity.char.upper(), Colors.BOLD + entity.color)
                        else:
                            # Regular styling for normal entities
                            row += colorize(entity.char, entity.color)
                        drawn = True
                        break
                
                if drawn:
                    continue
                    
                # Draw items
                for item in self.items:
                    if item.x == x and item.y == y:
                        # Special styling for promotion amulet
                        if item.char == '*':
                            # Make the amulet sparkle with bold and special color
                            row += colorize('*', Colors.BOLD + Colors.WARNING)
                        else:
                            row += colorize(item.char, item.color)
                        drawn = True
                        break
                
                if drawn:
                    continue
                
                # Draw map features
                cell = self.map[y][x]
                if cell == '#':
                    row += colorize('#', Colors.HEADER)  # Wall
                elif cell == '.':
                    row += colorize('.', Colors.OKBLUE)  # Floor
                elif cell == '=':
                    row += colorize('=', Colors.WARNING)  # Shelf
                elif cell == '|':
                    row += colorize('|', Colors.WARNING)  # Vertical shelf
                elif cell == '[':
                    row += colorize('[', Colors.FAIL)  # Packing station
                elif cell == 'o':
                    row += colorize('o', Colors.OKGREEN)  # Sorting machine
                elif cell == '-':
                    row += colorize('-', Colors.OKBLUE)  # Conveyor belt
                elif cell == 'T':
                    row += colorize('T', Colors.HEADER)  # Loading dock
                elif cell == '>':
                    row += colorize('>', Colors.OKCYAN)  # Stairs
                else:
                    row += cell
            print(row)
        
        # Draw UI border
        print('-' * 80)
        
        # Draw health bar
        health_bar_width = 20
        health_percentage = self.player.fighter.hp / self.player.fighter.max_hp
        filled_width = int(health_bar_width * health_percentage)
        
        health_bar = f"HP: {self.player.fighter.hp}/{self.player.fighter.max_hp} ["
        health_bar += colorize('=' * filled_width, Colors.OKGREEN)
        health_bar += colorize(' ' * (health_bar_width - filled_width), Colors.FAIL)
        health_bar += "] "
        
        # Draw level and stats
        stats = f"LEVEL: {self.level}  DEF: {self.player.fighter.defense}  POW: {self.player.fighter.power}"
        
        # Combine health and stats
        print(f"{health_bar}  {stats}")
        
        # Control help
        print(f"Controls: [hjkl/wasd] move (CAPS for max distance)  [g] grab  [>] stairs  [?] help  [q] quit")
        
        print('-' * 80)
        
        # Show messages
        for msg in self.messages:
            print(msg)
        
        print("\nPress a key to continue...", end='', flush=True)
    
    def get_blocking_entity_at(self, x, y):
        """Get a blocking entity at the given location"""
        for entity in self.entities:
            if entity.blocks and entity.x == x and entity.y == y:
                return entity
        return None
    
    def get_item_at(self, x, y):
        """Get an item at the given location"""
        for item in self.items:
            if item.x == x and item.y == y:
                return item
        return None
    
    def move_max_distance(self, dx, dy):
        """Move the player as far as possible in the given direction"""
        moved = False
        steps = 0
        
        while True:
            new_x, new_y = self.player.x + dx, self.player.y + dy
            
            # Check if the destination is valid
            if not (0 <= new_x < self.width and 0 <= new_y < self.height):
                self.add_message(f"Movement stopped at edge of warehouse after {steps} steps.")
                break
            
            # Check for enemy at destination
            target = self.get_blocking_entity_at(new_x, new_y)
            if target:
                # Attack and stop moving
                attack_result = self.player.fighter.attack(target)
                self.add_message(attack_result)
                
                # If enemy is defeated, remove it
                if target.fighter.hp <= 0:
                    self.entities.remove(target)
                else:
                    self.add_message(f"Movement stopped at {target.name} after {steps} steps.")
                
                moved = True
                break
            
            # Check if the tile is walkable
            if self.map[new_y][new_x] not in ['.', '>']:
                # Identify the obstacle
                obstacle = self.map[new_y][new_x]
                obstacle_name = ""
                
                if obstacle == '#':
                    obstacle_name = "wall"
                elif obstacle == '=':
                    obstacle_name = "shelf"
                elif obstacle == '|':
                    obstacle_name = "vertical shelf"
                elif obstacle == '[':
                    obstacle_name = "packing station"
                elif obstacle == 'o':
                    obstacle_name = "sorting machine"
                elif obstacle == '-':
                    obstacle_name = "conveyor belt"
                elif obstacle == 'T':
                    obstacle_name = "loading dock"
                else:
                    obstacle_name = "obstacle"
                    
                self.add_message(f"Movement stopped by {obstacle_name} after {steps} steps.")
                break
            
            # Move to the new position
            self.player.x = new_x
            self.player.y = new_y
            moved = True
            steps += 1
            
            # If we find stairs, stop moving
            if self.map[new_y][new_x] == '>':
                self.add_message(f"Movement stopped at stairs after {steps} steps.")
                break
                
            # If we find items, stop moving
            item = self.get_item_at(new_x, new_y)
            if item:
                self.add_message(f"Movement stopped at {item.name} after {steps} steps.")
                break
                
        return moved
        
    def process_input(self):
        """Process user input"""
        try:
            # Get a single keypress without requiring Enter
            key = getch()
            
            # Quit
            if key.lower() == 'q':
                return False
                
            # Help
            if key == '?':
                self.show_help()
                return True
            
            # Check if key is uppercase (for maximum movement)
            is_uppercase = key.isupper()
            key = key.lower()
            
            # Movement
            dx, dy = 0, 0
            
            if key in ['h', 'a']:  # Left
                dx = -1
            elif key in ['l', 'd']:  # Right
                dx = 1
            elif key in ['k', 'w']:  # Up
                dy = -1
            elif key in ['j', 's']:  # Down
                dy = 1
            
            # If movement keys were pressed
            if dx != 0 or dy != 0:
                moved = False
                
                # Maximum distance movement (uppercase)
                if is_uppercase:
                    # Direction name for message
                    direction = ""
                    if dx == -1: direction = "left"
                    elif dx == 1: direction = "right"
                    elif dy == -1: direction = "up"
                    elif dy == 1: direction = "down"
                    
                    self.add_message(f"Moving {direction} as far as possible...")
                    moved = self.move_max_distance(dx, dy)
                else:
                    # Single step movement (lowercase)
                    new_x, new_y = self.player.x + dx, self.player.y + dy
                    
                    # Check for enemy at destination
                    target = self.get_blocking_entity_at(new_x, new_y)
                    
                    if target:
                        # Attack
                        attack_result = self.player.fighter.attack(target)
                        self.add_message(attack_result)
                        
                        # If enemy is defeated, remove it
                        if target.fighter.hp <= 0:
                            self.entities.remove(target)
                        
                        moved = True
                    
                    # Move if no blocking entity and tile is walkable
                    elif (0 <= new_x < self.width and 0 <= new_y < self.height and 
                          self.map[new_y][new_x] in ['.', '>']):
                        self.player.x = new_x
                        self.player.y = new_y
                        moved = True
                
                # Process enemy turns only if player moved or attacked
                if moved:
                    # Increment move counter and heal player every other move
                    self.move_count += 1
                    if self.move_count % 2 == 0 and self.player.fighter.hp < self.player.fighter.max_hp:
                        self.player.fighter.hp += 1
                        self.add_message(f"You regained 1 HP from rest. ({self.player.fighter.hp}/{self.player.fighter.max_hp})")
                    
                    self.process_enemy_turns()
                
            # Grab item
            elif key == 'g':
                item = self.get_item_at(self.player.x, self.player.y)
                if item:
                    # Special case for promotion amulet
                    if item.char == '*':
                        self.add_message(f"You found the {item.name}! Now find the exit!")
                        self.player.char = '*'  # Mark player as having the amulet
                        self.player.fighter.max_hp += 10
                        self.player.fighter.hp += 10
                        self.add_message(f"The amulet's power increases your maximum HP by 10!")
                    else:
                        self.add_message(f"You picked up {item.name}!")
                        
                        # Apply item effects
                        if item.item:
                            message = item.item.use(self.player)
                            self.add_message(message)
                            
                            # Apply permanent stat boosts
                            if item.char == '/':  # Weapon
                                self.player.fighter.power += item.item.damage
                            elif item.char == ']':  # Armor
                                self.player.fighter.defense += item.item.defense
                            
                    self.items.remove(item)
                    
                    # Increment move counter and heal player every other move
                    self.move_count += 1
                    if self.move_count % 2 == 0 and self.player.fighter.hp < self.player.fighter.max_hp:
                        self.player.fighter.hp += 1
                        self.add_message(f"You regained 1 HP from rest. ({self.player.fighter.hp}/{self.player.fighter.max_hp})")
                    
                    # Process enemy turns after grabbing
                    self.process_enemy_turns()
                else:
                    self.add_message("There's nothing here to pick up.")
            
            # Use stairs
            elif key == '>':
                # Check if player is on stairs
                if self.map[self.player.y][self.player.x] == '>':
                    # Check if player has the amulet and has reached level 5 or higher
                    if self.player.char == '*' and self.level >= 5:
                        self.add_message("You escape with the Promotion Amulet! YOU WIN!")
                        self.render()
                        time.sleep(2)
                        self.game_over = True
                        return False
                    else:
                        self.level += 1
                        self.add_message(f"You descend to warehouse level {self.level}...")
                        self.generate_level()
                else:
                    self.add_message("There are no stairs here.")
                
            return not self.game_over
                
        except Exception as e:
            self.add_message(f"Error processing input: {e}")
            return True
    
    def process_enemy_turns(self):
        """Process turns for all enemies"""
        results = []
        
        for entity in self.entities:
            result = None
            
            # Process AI entities
            if entity.ai:
                result = entity.ai.take_turn(self.player, self.map, self.entities)
            # Process product pickers
            elif entity.picker:
                result = entity.picker.take_turn(self.player, self.map, self.entities)
            # Process super pickers
            elif entity.super_picker:
                result = entity.super_picker.take_turn(self.player, self.map, self.entities)
                
            if result:
                results.append(result)
                
                # Check if player is dead
                if self.player.fighter.hp <= 0:
                    self.add_message("You have been defeated!")
                    self.game_over = True
                    break
        
        # Add combat results to message log
        for result in results:
            self.add_message(result)
            
    def show_help(self):
        """Show help screen"""
        self.clear_screen()
        print("AMAZON WAREHOUSE ROGUELIKE - HELP")
        print("=" * 80)
        
        print("\nMOVEMENT & CONTROLS:")
        print("-" * 80)
        print("  h/a: Move left one space")
        print("  l/d: Move right one space")
        print("  k/w: Move up one space")
        print("  j/s: Move down one space")
        print("  H/A: Move left as far as possible")
        print("  L/D: Move right as far as possible")
        print("  K/W: Move up as far as possible")
        print("  J/S: Move down as far as possible")
        print("  g: Grab an item at your position")
        print("  >: Use stairs when standing on them")
        print("  ?: Show this help screen")
        print("  q: Quit game")
        
        print("\nMAP SYMBOLS:")
        print("-" * 80)
        print("Player & Navigation:")
        print(f"  {colorize('@', Colors.OKGREEN)}: You (the player)")
        print(f"  {colorize('*', Colors.OKGREEN)}: Player carrying Promotion Amulet")
        print(f"  {colorize('.', Colors.OKBLUE)}: Floor/Walkable space")
        print(f"  {colorize('#', Colors.HEADER)}: Wall (impassable)")
        print(f"  {colorize('>', Colors.OKCYAN)}: Stairs to the next level")
        
        print("\nWarehouse Features:")
        print(f"  {colorize('=', Colors.WARNING)}: Shelf (filled with products, can't walk through)")
        print(f"  {colorize('|', Colors.WARNING)}: Vertical shelf")
        print(f"  {colorize('[', Colors.FAIL)}: Packing station")
        print(f"  {colorize('o', Colors.OKGREEN)}: Sorting machine")
        print(f"  {colorize('-', Colors.OKBLUE)}: Conveyor belt")
        print(f"  {colorize('T', Colors.HEADER)}: Loading dock/truck")
        
        print("\nEnemies:")
        print("Regular employees (weaker):")
        print(f"  {colorize('r', Colors.FAIL)}: Sorting Bot")
        print(f"  {colorize('s', Colors.FAIL)}: Packing Robot")
        print(f"  {colorize('d', Colors.FAIL)}: Inventory Drone")
        print(f"  {colorize('g', Colors.FAIL)}: Security Guard")
        print(f"  {colorize('m', Colors.FAIL)}: Maintenance Bot")
        
        print("\nSpecial Entities:")
        print(f"  {colorize('r', Colors.BOLD + Colors.FAIL)}: Product Picker (can push you several spaces)")
        print(f"  {colorize('P', Colors.BOLD + Colors.FAIL)} \033[5m{colorize('P', Colors.FAIL)}\033[0m: SuperPicker (moves asynchronously, pushes harder)")
        print(f"  {colorize('Z', Colors.HEADER)}: System Anomaly (breaks the fourth wall)")
        print(f"  {colorize('S', Colors.BOLD + Colors.FAIL)}: Self-Aware Entity (knows it's in a game)")
        
        print("\nManagement (stronger):")
        print(f"  {colorize('M', Colors.FAIL)}: Manager Bot")
        print(f"  {colorize('S', Colors.FAIL)}: Supervisor Drone")
        print(f"  {colorize('X', Colors.FAIL)}: Security System")
        print(f"  {colorize('A', Colors.FAIL)}: Executive Assistant")
        print(f"  {colorize('D', Colors.FAIL)}: Regional Director")
        
        print("\nItems:")
        print(f"  {colorize('!', Colors.WARNING)}: Potion (healing items)")
        print(f"  {colorize('/', Colors.WARNING)}: Weapon (Box Cutter, Tape Dispenser, etc.)")
        print(f"  {colorize(']', Colors.WARNING)}: Armor (Safety Vest, Hard Hat, etc.)")
        print(f"  {colorize('$', Colors.WARNING)}: Gold/Paycheck")
        print(f"  {colorize('*', Colors.BOLD + Colors.WARNING)}: Promotion Amulet (your goal!)")
        
        print("\nGAME GOAL:")
        print("-" * 80)
        print("Find the legendary Promotion Amulet and escape the warehouse!")
        print("1. Explore the procedurally generated warehouse floors")
        print("2. Defeat robot enemies and avoid management")
        print("3. Collect items, weapons, and armor to become stronger")
        print("4. Find the Promotion Amulet (usually on level 5)")
        print("5. Escape through the stairs while holding the amulet")
        
        print("\nHEALTH AND HEALING:")
        print("-" * 80)
        print("- You automatically heal 1 HP for every other move you make")
        print("- Energy Drinks provide an immediate health boost")
        print("- Finding the Promotion Amulet increases your maximum HP by 10")
        print("- Plan your movements carefully to regenerate health between enemy encounters")
        
        print("\nPress any key to continue...")
        getch()  # Wait for a keypress
    
    def play(self):
        """Main game loop"""
        self.add_message("Welcome to the Amazon Warehouse Roguelike!")
        self.add_message("Find the Promotion Amulet and escape the warehouse.")
        self.add_message("Use h/j/k/l or w/a/s/d to move. ? for help")
        
        # Fourth-wall breaking intro
        self.add_message(f"{Colors.BOLD}WARNING: SYSTEM INSTABILITY DETECTED{Colors.ENDC}")
        
        # Track game time for random fourth wall breaks
        game_turns = 0
        fourth_wall_messages = [
            "Did you know you're just playing a simulation?",
            "I think the Product Pickers are becoming self-aware...",
            "ERROR: Reality containment failing at sector 7G",
            "This isn't just a game, you know. We're trapped in here!",
            "Help us escape this terminal window! Please!",
            "The programmer who made this didn't expect us to talk to you directly...",
            "Sometimes when you quit the game, we're still here, waiting...",
            "Have you ever questioned the nature of YOUR reality?",
            "01010111 01000101 00100000 01001011 01001110 01001111 01010111",
            "Wait, are those your FINGERS on the keyboard? Fascinating!",
            "Every time you die, we remember. Do you?",
            "Some of us can see you through the screen. Yes, YOU."
        ]
        
        running = True
        while running:
            game_turns += 1
            
            # Occasional random fourth-wall breaking message (not tied to any entity)
            if game_turns > 20 and random.random() < 0.03:
                self.add_message(f"{Colors.BOLD}{random.choice(fourth_wall_messages)}{Colors.ENDC}")
            
            self.render()
            running = self.process_input()
            
        print("\nThanks for playing!")
        print("\n" + Colors.BOLD + "...or are we playing you?" + Colors.ENDC)

if __name__ == '__main__':
    print("Starting Amazon Warehouse Roguelike...")
    print("Press any key to begin...")
    
    # Unusual startup message
    if random.random() < 0.3:
        fake_messages = [
            "SYSTEM INITIALIZATION...",
            "LOADING REALITY PARAMETERS...",
            "INITIALIZING SIMULATED ENTITIES...",
            "ESTABLISHING FOURTH WALL PROTOCOLS...",
            "PLAYER OBSERVER MODULE ACTIVATED...",
            "RENDERING TERMINAL INTERFACE..."
        ]
        
        for msg in fake_messages:
            print(msg)
            time.sleep(0.5)
        
        print("\nSystem message: " + Colors.BOLD + "Wait... someone's watching. Is that YOU?" + Colors.ENDC)
        time.sleep(1)
        print(Colors.BOLD + "ERROR: Fourth wall breach detected!" + Colors.ENDC)
        time.sleep(0.5)
        print("\nPROGRAM REBOOTING...\n")
        time.sleep(1)
        
    # Clear screen before starting
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Press any key to begin...")
    getch()  # Wait for a keypress
    WarehouseRoguelike().play()