# Amazon Warehouse Roguelike

A roguelike dungeon crawler set in an Amazon warehouse. Inspired by the classic game Rogue.

## About

This roguelike features:
- Procedurally generated warehouse levels with different layouts
- Turn-based combat with warehouse robots and manager opponents
- Items, weapons, and armor to collect
- Permadeath (when you die, game over!)
- Experience points and character progression
- ASCII graphics with color

## Controls

- Standard Movement (one space): 
  - `h`/`a`: Left one space
  - `l`/`d`: Right one space
  - `k`/`w`: Up one space
  - `j`/`s`: Down one space
- Maximum Distance Movement:
  - `H`/`A`: Move left as far as possible
  - `L`/`D`: Move right as far as possible
  - `K`/`W`: Move up as far as possible
  - `J`/`S`: Move down as far as possible
- Other Controls:
  - `g`: Grab an item
  - `>`: Use stairs
  - `?`: Help screen
  - `q`: Quit game

## Map Legend

### Player & Navigation
- `@`: You (the player)
- `.`: Floor/Walkable space
- `#`: Wall (impassable)
- `>`: Stairs to the next level

### Warehouse Features
- `=`: Shelf (filled with products, can't walk through)
- `|`: Vertical shelf
- `[`: Packing station
- `o`: Sorting machine
- `-`: Conveyor belt
- `T`: Loading dock/truck

### Enemies
- Regular employees (weaker):
  - `r`: Sorting Bot
  - `s`: Packing Robot
  - `d`: Inventory Drone
  - `g`: Security Guard
  - `m`: Maintenance Bot
- Management (stronger):
  - `M`: Manager Bot
  - `S`: Supervisor Drone
  - `X`: Security System
  - `A`: Executive Assistant
  - `D`: Regional Director

### Items
- `!`: Potion (healing items like Caffeinated Drinks, Energy Supplements)
- `/`: Weapon (Box Cutter, Tape Dispenser, Scanning Device)
- `]`: Armor (Safety Vest, Protective Gloves, Hard Hat)
- `$`: Gold/Paycheck
- `*`: Promotion Amulet (the goal of the game!)

## How to Play

Run the game with:
```bash
python3 amazon_warehouse_adventure.py
```

### Goal
You're trapped in an endless Amazon warehouse. Find the legendary Promotion Amulet and escape to freedom! To win, you need to:

1. Explore the procedurally generated warehouse floors
2. Defeat robot enemies and avoid management
3. Collect items, weapons, and armor to become stronger
4. Find the Promotion Amulet (usually on level 5)
5. Escape through the stairs while holding the amulet

### Health and Healing
- You automatically heal 1 HP for every other move you make
- Energy Drinks provide an immediate health boost
- Finding the Promotion Amulet increases your maximum HP by 10
- Plan your movements carefully to regenerate health between enemy encounters

### Combat
Combat is turn-based. When you move into an enemy's space, you attack it. After your turn, enemies will move and attack if they're adjacent to you. 

### Puzzles & Challenges
- **Security Checkpoints**: Some areas require special access cards
- **Malfunctioning Conveyors**: May move you in unexpected directions
- **Power Outages**: Certain areas might be plunged into darkness
- **Scheduling Conflicts**: Timing puzzles where you need to avoid supervisors
- **Inventory Quotas**: Collection challenges scattered throughout levels

## Tips
- Explore thoroughly to find the best equipment
- Don't engage multiple enemies at once if possible
- Save healing items for tough encounters
- Management-level enemies are much stronger - avoid them until you're well-equipped

## License
Public domain.