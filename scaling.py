"""
FILE: game/scaling.py
Centralized difficulty scaling formulas
Balanced so every level is hard but beatable with skill + upgrades
"""

import math

class ScalingFormulas:
    """Centralized difficulty scaling"""

    @staticmethod
    def boss_hp(level: int, base_hp: float = 300.0) -> float:
        """Boss HP scaling - polynomial early, tempered exponential late.

        Levels 1-10:  gentle linear ramp (350 → 900)
        Levels 11-30: moderate growth via 1.12^level
        Levels 31+:   slower growth via 1.08^level to stay beatable
        """
        if level <= 10:
            return base_hp + level * 60
        elif level <= 30:
            base_at_10 = base_hp + 10 * 60  # 900
            return base_at_10 * (1.12 ** (level - 10))
        else:
            base_at_10 = base_hp + 10 * 60
            base_at_30 = base_at_10 * (1.12 ** 20)  # ~8,673
            return base_at_30 * (1.08 ** (level - 30))

    @staticmethod
    def boss_damage(level: int, base_damage: float = 35.0) -> float:
        """Boss damage scaling - meaningful growth so hits always matter.

        Levels 1-5:  flat base damage (easy intro)
        Levels 6-15: gentle ramp via sqrt
        Levels 16+:  steady log growth, higher cap
        """
        if level <= 5:
            return base_damage
        elif level <= 15:
            return base_damage * (1 + (level - 5) * 0.06)
        else:
            # Continues growing but diminishing
            mid_mult = 1 + 10 * 0.06  # 1.6 at level 15
            return min(base_damage * 5, base_damage * mid_mult * (1 + math.log(level - 14) * 0.25))

    @staticmethod
    def boss_fire_delay(level: int, base_delay: float = 2.5, min_delay: float = 0.25) -> float:
        """Boss attack speed - smooth decay to floor.

        Levels 1-5:  constant (learning phase)
        Levels 6-15: gradual speedup
        Levels 16+:  approaches min_delay asymptotically
        """
        if level <= 5:
            return base_delay
        elif level <= 15:
            # Linear interpolation toward faster
            t = (level - 5) / 10.0
            return base_delay * (1 - t * 0.4)  # 60% of base at level 15
        else:
            fast_base = base_delay * 0.6
            return max(min_delay, fast_base * math.exp(-0.04 * (level - 15)))

    @staticmethod
    def player_damage_bonus(level: int) -> float:
        """Player damage bonus from level - grows enough to keep pace with boss HP.

        Ensures late-game isn't purely upgrade-dependent.
        """
        if level <= 5:
            return 0
        elif level <= 15:
            return (level - 5) * 2  # +2 per level, 0-20
        else:
            # Accelerating bonus to keep pace with boss HP growth
            base_bonus = 20  # from levels 6-15
            return base_bonus + 8 * math.log(level - 14) + (level - 15) * 0.5

    @staticmethod
    def projectile_speed(level: int, base_speed: float = 400.0) -> float:
        """Projectile speed increases with level - slightly more aggressive."""
        if level <= 5:
            return base_speed
        elif level <= 20:
            return base_speed * (1 + (level - 5) * 0.015)  # +1.5% per level
        else:
            speed_at_20 = base_speed * (1 + 15 * 0.015)  # 1.225x
            return speed_at_20 * (1 + math.log(level - 19) * 0.08)

    @staticmethod
    def wave_count(level: int) -> int:
        """Number of projectiles in wave attacks - grows meaningfully."""
        if level <= 10:
            return 8
        elif level <= 30:
            return min(20, 8 + (level - 10) // 2)
        else:
            return min(28, 18 + (level - 30) // 3)

    @staticmethod
    def coin_reward(level: int) -> int:
        """Calculate coin reward for completing a level."""
        is_super = level % 10 == 0
        base_reward = 30 * level

        if is_super:
            base_reward *= 3

        if level > 20:
            base_reward = int(base_reward * (1 + math.log(level / 20) * 0.5))

        return base_reward
