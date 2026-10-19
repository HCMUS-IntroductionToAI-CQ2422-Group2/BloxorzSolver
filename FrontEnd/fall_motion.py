"""Visual loss poses derived from the engine's attempted landing and support."""
import math

from BackEnd.objects.blocks import GameState
from BackEnd.objects.tiles import FragileTile


def prepare_fall(rules, before, action):
    # The engine rejects unsupported states; retain one only for presentation.
    block = rules._roll(before.block, action)
    landing = GameState(block, before.open_bridges)
    if rules.is_valid(landing):
        pressed = (block.positions[block.active_cube],) if block.is_split() else block.positions
        landing = rules._apply_switches(landing, pressed)
    block = landing.block
    supported = []
    broken = []
    for position in block.positions:
        tile = rules.board.get_tile(position)
        if tile is not None and tile.can_support(block, landing):
            supported.append(position)
        elif isinstance(tile, FragileTile):
            broken.append(position)
    edge = None
    if not block.is_split() and len(supported) == 1 and len(block.positions) == 2:
        support = supported[0]
        void = next(p for p in block.positions if p not in supported)
        axis = 0 if support[0] != void[0] else 1
        sign = 1 if void[axis] > support[axis] else -1
        edge = (axis, sign, support[axis] + (1 if sign > 0 else 0))
    return {"state": landing, "supported": supported, "broken": broken, "edge": edge}


def fall_vertex(vertex, plan, elapsed):
    """Tip about the last supporting edge, then detach outside that edge.

    Before detachment every point still over the supporting half-plane is at
    or above z=0. A completely unsupported block drops through its footprint.
    """
    x, y, z = vertex
    seconds = max(0, elapsed)
    if plan['edge'] is None:
        return x, y, z - 15 * seconds * seconds
    axis, sign, pivot = plan['edge']
    tip_time = .36
    t = min(1, seconds / tip_time)
    angle = t * t * math.pi / 2
    q = (x if axis == 0 else y) - pivot
    horizontal = pivot + q * math.cos(angle) + sign * z * math.sin(angle)
    z = -sign * q * math.sin(angle) + z * math.cos(angle)
    free = max(0, seconds - tip_time)
    horizontal += sign * 1.5 * free
    z -= 2.5 * free + 15 * free * free
    return (horizontal, y, z) if axis == 0 else (x, horizontal, z)
