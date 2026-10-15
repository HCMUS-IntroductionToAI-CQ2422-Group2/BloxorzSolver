from BackEnd.logic.board import Board
from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.objects.sharing import Move, Position
from BackEnd.objects.switchs import EffectMode, SplitSwitch, Switch
from BackEnd.objects.tiles import Goal


class GameRules:
    """Calculate actions without changing the board or the input state."""

    def __init__(self, board: Board) -> None:
        self.board = board
        for switch in board.switch:
            for effect in switch.effects:
                if board.get_bridge(effect.bridge_id) is None:
                    raise ValueError(f"Switch {switch.switch_id}: unknown bridge {effect.bridge_id}")
            if isinstance(switch, SplitSwitch):
                if len(switch.teleport_positions) != 2:
                    raise ValueError("Split switches require two teleport positions")
                first, second = switch.teleport_positions
                if abs(first[0] - second[0]) + abs(first[1] - second[1]) <= 1:
                    raise ValueError("Teleport positions must be distinct and non-adjacent")
                if any(board.get_tile(position) is None for position in switch.teleport_positions):
                    raise ValueError("Teleport positions must be on the board")

    def apply_action(self, state: GameState, action: Move) -> GameState | None:
        """Return the next state, or None when an action is illegal."""
        if not isinstance(action, Move):
            raise TypeError("action must be a Move enum member")
        if not self.is_valid(state):
            return None
        if action == Move.SWITCH:
            return self._switch_cube(state) if state.block.is_split() else None

        block = self._roll(state.block, action)
        landed = (block.positions[block.active_cube],) if block.is_split() else block.positions
        result = GameState(block, state.open_bridges)
        if not self.is_valid(result):
            return None
        result = self._apply_switches(result, landed)
        if not self.is_valid(result):
            return None
        if state.block.is_split():
            result = self._merge_block(result)
        return result

    def get_valid_actions(self, state: GameState) -> list[Move]:
        """Return all legal actions for the given state."""
        return [action for action in Move if self.apply_action(state, action) is not None]

    def is_valid(self, state: GameState) -> bool:
        """Check block geometry and support under every occupied position."""
        block = state.block
        positions = block.positions
        if block.is_standing():
            if len(positions) != 1:
                return False
        else:
            if len(positions) != 2 or positions[0] == positions[1]:
                return False
            (x, y), second = positions
            if block.orientation == Orientation.HORIZONTAL:
                if second != (x + 1, y):
                    return False
            elif block.orientation == Orientation.VERTICAL:
                if second != (x, y + 1):
                    return False
            elif not block.is_split():
                return False

        if any(self.board.get_bridge(bridge_id) is None for bridge_id in state.open_bridges):
            return False
        for position in positions:
            tile = self.board.get_tile(position)
            if tile is None or not tile.can_support(block, state):
                return False
        return True

    def is_goal(self, state: GameState) -> bool:
        """A valid intact block must stand on a goal tile to win."""
        return (
            self.is_valid(state)
            and state.block.is_standing()
            and isinstance(self.board.get_tile(state.block.positions[0]), Goal)
        )

    def _roll(self, block: BlockState, direction: Move) -> BlockState:
        """Calculate movement without checking tiles or triggering switches."""
        dx, dy = {
            Move.UP: (0, -1), Move.DOWN: (0, 1),
            Move.LEFT: (-1, 0), Move.RIGHT: (1, 0),
        }[direction]
        if block.is_split():
            positions = list(block.positions)
            x, y = positions[block.active_cube]
            positions[block.active_cube] = (x + dx, y + dy)
            return BlockState.split(tuple(positions), block.active_cube)

        x, y = block.positions[0]
        if block.is_standing():
            return BlockState(
                ((x + dx, y + dy), (x + 2 * dx, y + 2 * dy)),
                Orientation.HORIZONTAL if dx else Orientation.VERTICAL,
            )
        if block.orientation == Orientation.HORIZONTAL and dx:
            return BlockState(((x + (2 if dx > 0 else -1), y),), Orientation.STANDING)
        if block.orientation == Orientation.VERTICAL and dy:
            return BlockState(((x, y + (2 if dy > 0 else -1)),), Orientation.STANDING)
        return BlockState(
            tuple((x + dx, y + dy) for x, y in block.positions), block.orientation,
        )

    def _switch_cube(self, state: GameState) -> GameState:
        """Select the other cube without triggering switches or merging."""
        block = BlockState.split(state.block.positions, 1 - state.block.active_cube)
        return GameState(block, state.open_bridges)

    def _apply_switches(self, state: GameState, landed: tuple[Position, ...]) -> GameState:
        """Select switches before effects, then apply them in switch-ID order."""
        switches = []
        for position in set(landed):
            tile = self.board.get_tile(position)
            if isinstance(tile, Switch) and tile.is_activated(state.block):
                switches.append(tile)
        for switch in sorted(switches, key=lambda switch: switch.switch_id):
            state = self._update_bridges(state, switch)
            if isinstance(switch, SplitSwitch):
                state = self._split_block(state, switch)
        return state

    def _update_bridges(self, state: GameState, switch: Switch) -> GameState:
        """Apply TOGGLE and SET effects to a new bridge-state set."""
        opened = set(state.open_bridges)
        for effect in switch.effects:
            if effect.effect_mode == EffectMode.TOGGLE:
                opened.symmetric_difference_update((effect.bridge_id,))
            elif effect.target_open:
                opened.add(effect.bridge_id)
            else:
                opened.discard(effect.bridge_id)
        return GameState(state.block, frozenset(opened))

    def _split_block(self, state: GameState, switch: SplitSwitch) -> GameState:
        """Teleport cubes and select cube zero after position normalization."""
        block = BlockState.split(tuple(sorted(switch.teleport_positions)))
        return GameState(block, state.open_bridges)

    def _merge_block(self, state: GameState) -> GameState:
        """Merge adjacent cubes, preserving the current bridge state."""
        if not state.block.is_split():
            return state
        (x1, y1), (x2, y2) = state.block.positions
        if abs(x1 - x2) + abs(y1 - y2) != 1:
            return state
        orientation = Orientation.HORIZONTAL if y1 == y2 else Orientation.VERTICAL
        block = BlockState(state.block.positions, orientation)
        return GameState(block, state.open_bridges)
