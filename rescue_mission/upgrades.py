import random
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class UpgradeBuff:
    key: str
    title: str
    description: str
    stat_delta: Dict[str, Any]
    icon_name: str = "generic"

ALL_BUFFS = [
    UpgradeBuff("max_health_up", "Tăng Máu Tối Đa", "+30 Máu tối đa", {"max_health": 30}),
    UpgradeBuff("speed_up", "Tốc Độ Nhanh Nhẹn", "+0.5 Tốc độ di chuyển", {"move_speed": 0.5}),
    UpgradeBuff("damage_up", "Sát Thương Mạnh", "+5 Sát thương đạn", {"bullet_damage": 5}),
    UpgradeBuff("fire_rate_up", "Bắn Liên Tục", "-1 Delay giữa 2 viên đạn", {"fire_interval": -1}),
    UpgradeBuff("bullet_speed_up", "Đạn Siêu Tốc", "+2.5 Tốc độ bay của đạn", {"bullet_speed": 2.5}),
    UpgradeBuff("dash_cd_down", "Lướt Nhanh", "-0.15s Hồi chiêu Lướt", {"dash_cooldown": -0.15}),
    UpgradeBuff("energy_regen_up", "Hồi Năng Lượng", "+6 Năng lượng Q mỗi giây", {"energy_regen": 6}),
]

def pick_three_buffs(already_keys: List[str]) -> List[UpgradeBuff]:
    available = [b for b in ALL_BUFFS if b.key not in already_keys]
    if len(available) >= 3:
        return random.sample(available, 3)
    return available

def apply_buffs_to_stats(base_stats, buffs: List[UpgradeBuff], config_module) -> Any:
    changes = {}
    for buff in buffs:
        for stat, delta in buff.stat_delta.items():
            if hasattr(base_stats, stat):
                changes[stat] = changes.get(stat, 0) + delta
    
    new_kwargs = {}
    for field in base_stats.__dataclass_fields__:
        val = getattr(base_stats, field)
        if field in changes:
            val += changes[field]
            
        # Ensure fire_interval doesn't go below 1
        if field == "fire_interval" and val < 1:
            val = 1
            
        new_kwargs[field] = val
        
    return type(base_stats)(**new_kwargs)
