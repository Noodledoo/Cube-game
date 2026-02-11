"""
FILE: game/scaling.py
Centralized difficulty scaling formulas
"""

import math

class ScalingFormulas:
    """Centralized difficulty scaling"""
    
    @staticmethod
    def boss_hp(level: int, base_hp: float = 300.0) -> float:
        """Boss HP scaling - aggressive growth"""
        if level <= 10:
            return base_hp + level * 50
        return base_hp * (1.15 ** level)
    
    @staticmethod
    def boss_damage(level: int, base_damage: float = 35.0) -> float:
        """Boss damage scaling - steady growth"""
        if level <= 10:
            return base_damage
        multiplier = 1 + math.log(level + 1) * 0.1
        return min(200, int(base_damage * multiplier))
    
    @staticmethod
    def boss_fire_delay(level: int, base_delay: float = 2.5, min_delay: float = 0.25) -> float:
        """Boss attack speed - has floor"""
        if level <= 10:
            return base_delay
        return max(min_delay, base_delay * math.exp(-0.03 * (level - 10)))
    
    @staticmethod
    def player_damage_bonus(level: int) -> float:
        """Player damage bonus from level"""
        if level <= 10:
            return 0
        return 5 * math.log(level + 1)
    
    @staticmethod
    def projectile_speed(level: int, base_speed: float = 400.0) -> float:
        """Projectile speed increases with level"""
        if level <= 5:
            return base_speed
        return base_speed * (1 + math.log(level - 4) * 0.1)
    
    @staticmethod
    def wave_count(level: int) -> int:
        """Number of projectiles in wave attacks"""
        if level <= 10:
            return 8
        return min(16, int(8 + math.log(level + 1) * 2))
    
    @staticmethod
    def coin_reward(level: int) -> int:
        """Calculate coin reward for completing a level"""
        is_super = level % 10 == 0
        base_reward = 30 * level
        
        if is_super:
            base_reward *= 3
        
        if level > 20:
            base_reward = int(base_reward * (1 + math.log(level / 20) * 0.5))
        
        return base_reward
