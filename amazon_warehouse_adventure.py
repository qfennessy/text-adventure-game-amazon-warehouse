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
    def __init__(self, x, y, char, name, color, blocks=True, fighter=None, ai=None, item=None):
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
        # Only move if the monster can see the player (distance < 6)
        if monster.distance_to(player) < 6:
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
        # Add some enemies (more on higher levels)
        num_monsters = random.randint(3, 5 + self.level)
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
                    
                    fighter_component = Fighter(hp, defense, power)
                    ai_component = BasicMonster()
                    
                    monster = Entity(x, y, char, name, color, True, fighter_component, ai_component)
                    self.entities.append(monster)
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
        # Start with all walls
        self.map = [['#' for _ in range(self.width)] for _ in range(self.height)]
        
        # Create warehouse layout (long rows of shelves)
        # Horizontal aisles (every 4 rows with 2-tile width)
        for y in range(3, self.height - 3, 4):
            for x in range(1, self.width - 1):
                self.map[y][x] = '.'
                self.map[y+1][x] = '.'  # Make aisles 2 tiles wide
                
        # Vertical aisles (wider spacing and 2-tile width)
        for x in range(5, self.width - 5, 15):
            for y in range(1, self.height - 1):
                self.map[y][x] = '.'
                self.map[y][x+1] = '.'  # Make aisles 2 tiles wide
                
        # Create long rows of storage shelves
        for y in range(1, self.height - 1):
            if y % 4 not in [0, 1]:  # Not a horizontal aisle row (now 2 tiles wide)
                for x in range(1, self.width - 1):
                    if not (x % 15 in [5, 6]):  # Not a vertical aisle (now 2 tiles wide)
                        if self.map[y][x] == '#' and self.is_adjacent_to(x, y, '.'):
                            # Create long shelves
                            self.map[y][x] = '='
        
        # Add some variety with vertical shelves
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.map[y][x] == '=' and random.random() < 0.1:
                    self.map[y][x] = '|'  # Vertical shelf
                
        # Add some packing stations near aisles
        for y in range(2, self.height - 2):
            for x in range(2, self.width - 2):
                if self.map[y][x] == '.' and random.random() < 0.03:
                    self.map[y][x] = '['  # Packing station
        
        # Add conveyor belts along some aisles
        for y in range(3, self.height - 3, 6):
            for x in range(10, self.width - 10):
                if self.map[y][x] == '.' and random.random() < 0.4:
                    self.map[y][x] = '-'  # Conveyor belt
        
        # Add a few sorting machines
        for _ in range(3):
            x, y = random.randint(5, self.width - 5), random.randint(5, self.height - 5)
            if self.map[y][x] == '.':
                self.map[y][x] = 'o'  # Sorting machine
        
        # Add a loading dock
        dock_x, dock_y = random.randint(self.width - 10, self.width - 3), random.randint(3, self.height - 3)
        if dock_x > 0 and dock_y > 0:
            self.map[dock_y][dock_x] = 'T'  # Loading dock/truck
        
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
                    row += colorize('@', Colors.OKGREEN)
                    drawn = True
                    continue
                
                # Draw monsters
                for entity in self.entities:
                    if entity.x == x and entity.y == y:
                        row += colorize(entity.char, entity.color)
                        drawn = True
                        break
                
                if drawn:
                    continue
                    
                # Draw items
                for item in self.items:
                    if item.x == x and item.y == y:
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
            if entity.ai:
                result = entity.ai.take_turn(self.player, self.map, self.entities)
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
        print(f"  {colorize('*', Colors.WARNING)}: Promotion Amulet (your goal!)")
        
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
        
        running = True
        while running:
            self.render()
            running = self.process_input()
            
        print("\nThanks for playing!")

if __name__ == '__main__':
    print("Starting Amazon Warehouse Roguelike...")
    print("Press any key to begin...")
    getch()  # Wait for a keypress
    WarehouseRoguelike().play()