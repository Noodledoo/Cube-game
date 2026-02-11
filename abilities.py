"""
FILE: game/abilities.py
Ability system with stacking and temple
"""

import pygame
import random
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Ability:
    """Single ability definition"""
    name: str
    description: str
    rarity: str  # common, rare, legendary, cursed
    cooldown: float
    key: int  # pygame key code or None
    stacks: int = 0
    max_stacks: int = 5
    
    def get_cooldown(self) -> float:
        """Cooldown decreases with stacks"""
        if self.cooldown == 0:
            return 0
        return max(1.0, self.cooldown * (0.85 ** self.stacks))
    
    def can_use(self, last_used: float, current_time: float) -> bool:
        """Check if ability is ready"""
        if self.cooldown == 0:
            return False  # Passive ability
        return current_time - last_used >= self.get_cooldown()

class AbilityManager:
    """Manages ability registry and temple"""
    
    RARITY_WEIGHTS = {
        "common": 70,
        "rare": 25,
        "legendary": 4,
        "cursed": 1
    }
    
    RARITY_COLORS = {
        "common": (180, 180, 180),
        "rare": (80, 160, 255),
        "legendary": (255, 180, 60),
        "cursed": (200, 50, 200)
    }
    
    def __init__(self):
        self.registry: Dict[str, Ability] = {}
        self.player_abilities: Dict[str, Ability] = {}
        self.last_used: Dict[str, float] = {}
        self.temple_choices: List[Ability] = []
        self.rolls_this_session: int = 0
        self.current_pick_used: bool = False  # Track if current pick used free roll
        
    def register_ability(self, ability: Ability):
        """Add ability to registry"""
        self.registry[ability.name] = ability
    
    def roll_temple_choices(self, count: int = 3) -> List[Ability]:
        """Generate random ability choices"""
        weighted_pool = []
        for ability in self.registry.values():
            weight = self.RARITY_WEIGHTS.get(ability.rarity, 1)
            weighted_pool.extend([ability] * weight)
        
        self.temple_choices = random.choices(weighted_pool, k=count)
        return self.temple_choices
    
    def get_roll_cost(self) -> int:
        """Calculate roll cost - first roll free, then 100 per roll"""
        if not self.current_pick_used:
            return 0
        return 100 * (self.rolls_this_session + 1)
    
    def increment_roll_count(self):
        """Increment roll counter and mark pick as used"""
        if not self.current_pick_used:
            self.current_pick_used = True
        else:
            self.rolls_this_session += 1
    
    def select_ability(self, ability: Ability):
        """Player selects an ability"""
        if ability.name in self.player_abilities:
            if self.player_abilities[ability.name].stacks < ability.max_stacks:
                self.player_abilities[ability.name].stacks += 1
        else:
            new_ability = Ability(
                name=ability.name,
                description=ability.description,
                rarity=ability.rarity,
                cooldown=ability.cooldown,
                key=ability.key,
                stacks=1,
                max_stacks=ability.max_stacks
            )
            self.player_abilities[ability.name] = new_ability
            self.last_used[ability.name] = -999.0
        
        # Reset for next pick
        self.rolls_this_session = 0
        self.current_pick_used = False
    
    def reset_temple_session(self):
        """Reset temple session when leaving without selecting"""
        self.rolls_this_session = 0
        self.current_pick_used = False
    
    def get_ability_stacks(self, ability_name: str) -> int:
        """Get stack count for an ability"""
        if ability_name in self.player_abilities:
            return self.player_abilities[ability_name].stacks
        return 0
    
    def can_use_ability(self, ability_name: str, current_time: float) -> bool:
        """Check if ability is ready to use"""
        if ability_name not in self.player_abilities:
            return False
        
        ability = self.player_abilities[ability_name]
        if ability.key is None:  # Passive
            return False
        
        return ability.can_use(self.last_used.get(ability_name, -999), current_time)
    
    def use_ability(self, ability_name: str, current_time: float):
        """Mark ability as used"""
        self.last_used[ability_name] = current_time
