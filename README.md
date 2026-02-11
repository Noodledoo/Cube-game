# Cube Boss Fight - Ultimate Edition

## Installation

```bash
pip install pygame
```

## Running the Game

### Single Player (Default)
```bash
python main.py
```

### Multiplayer - Host a Server
```bash
# Host a game server and play as a client
python main.py --host --multiplayer

# Host with 3 bots added automatically
python main.py --host --multiplayer --bots 3
```

### Multiplayer - Join a Server
```bash
# Join an existing server
python main.py --multiplayer --address 192.168.1.100 --port 5555
```

### Standalone Server (No GUI)
```bash
# Run a dedicated server
python -m network.server --port 5555 --bots 2
```

### Standalone Bot Testing
```bash
# Run a single bot client
python -m network.bot --host 127.0.0.1 --port 5555 --name TestBot

# Run multiple bots (stress test)
python -m network.bot --host 127.0.0.1 --port 5555 --count 4
```

## Admin Console Commands

Press ` (backtick) to open the admin console in-game.

### Bot Commands (Multiplayer Only)
- `addbot` - Add a bot player to the server
- `removebot <player_id>` - Remove a specific bot
- `botcount` - Show number of active bots
- `listbots` - List all active bot names

### Player Commands
- `healplayer [amount]` - Heal the player
- `killplayer` - Kill the player
- `makeplayerinvincible true/false` - Toggle invincibility
- `setplayerstat dmg/speed/firerate <value>` - Set player stats

### Economy Commands
- `givemoney <amount>` - Add coins
- `setmoney <amount>` - Set exact coin amount
- `makemerich` - Add 999999 coins

### Game Commands
- `setlevel <level>` - Jump to level
- `killboss` - Instantly defeat the boss
- `skiplevel` - Complete current level

### Debug Commands
- `showstats true/false` - Toggle debug stats overlay
- `framestep true/false` - Enable frame-by-frame mode
- `step` - Advance one frame (when in framestep mode)
- `timescale <0.1-5.0>` - Set game speed

## Project Structure

```
cube_boss_fight/
â”œâ”€â”€ main.py              # Game entry point
â”œâ”€â”€ core/                # Core systems
â”‚   â”œâ”€â”€ config.py        # Save/load, configuration
â”‚   â””â”€â”€ constants.py     # Game constants, enums
â”œâ”€â”€ game/                # Game logic
â”‚   â”œâ”€â”€ abilities.py     # Ability system
â”‚   â”œâ”€â”€ admin_console.py # Developer console
â”‚   â”œâ”€â”€ animations.py    # Visual effects
â”‚   â”œâ”€â”€ boss_ai.py       # Boss attack patterns
â”‚   â”œâ”€â”€ player.py        # Player controls
â”‚   â”œâ”€â”€ rendering.py     # 3D cube rendering
â”‚   â”œâ”€â”€ scaling.py       # Difficulty formulas
â”‚   â”œâ”€â”€ states.py        # State dataclasses
â”‚   â””â”€â”€ ui.py            # UI/menus
â””â”€â”€ network/             # Multiplayer
    â”œâ”€â”€ protocol.py      # Message types, serialization
    â”œâ”€â”€ client.py        # Network client
    â”œâ”€â”€ server.py        # Game server + bot AI
    â””â”€â”€ bot.py           # Standalone bot client
```

## Bug Fixes Applied

1. **Enemy Projectiles Visibility** - Boss projectiles now render on top with enhanced visuals
2. **Homing/Piercing Orbit Fix** - Bullets pass through boss correctly, no more orbiting
3. **Boss Laser Attack** - Laser now fires properly at all levels (1.5s cooldown early game)
4. **Spray Attack Chaining** - Added lockout period to prevent infinite spray loops
