"""Board construction and object lookup using (x, y) coordinates."""

from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.objects.bridges import Bridge
from BackEnd.objects.sharing import Position
from BackEnd.objects.switchs import Switch
from BackEnd.objects.tiles import Tile


class Board:
    """Store board objects and the current game state."""

    def __init__(self) -> None:
        self.tile: list[Tile] = []
        self.block: BlockState | None = None
        self.switch: list[Switch] = []
        self.bridge: list[Bridge] = []
        self.game_state: GameState | None = None

    def add_tile(self, tile: Tile) -> None:
        """Add a tile and register switches or bridges in their own collections."""
        if isinstance(tile, Bridge):
            self.add_bridge(tile)
            return
        if isinstance(tile, Switch):
            self.switch.append(tile)
        self.tile.append(tile)

    def add_switch(self, switch: Switch) -> None:
        """Add a switch as both a tile and a switch."""
        self.add_tile(switch)

    def add_bridge(self, bridge: Bridge) -> None:
        """Add a bridge overlay."""
        self.bridge.append(bridge)

    def add_block(self, block: BlockState) -> None:
        """Set the controlled block, preserving bridge state if a game has started."""
        if self.game_state is not None:
            self.add_game_state(GameState(block, self.game_state.open_bridges))
        else:
            self.block = block

    def add_game_state(self, game_state: GameState) -> None:
        """Set the current state and keep the block attribute synchronized."""
        self.block = game_state.block
        self.game_state = game_state

    def get_tile(self, position: Position) -> Tile | None:
        """Return a bridge overlay or tile at (x, y), or None outside the board."""
        for bridge in self.bridge:
            if position in bridge.get_positions():
                return bridge
        for tile in self.tile:
            if position in tile.get_positions():
                return tile
        return None

    def get_switch(self, switch_id: str) -> Switch | None:
        """Find a switch by its ID."""
        for switch in self.switch:
            if switch.switch_id == switch_id:
                return switch
        return None

    def get_bridge(self, bridge_id: str) -> Bridge | None:
        """Find a bridge by its ID."""
        for bridge in self.bridge:
            if bridge.bridge_id == bridge_id:
                return bridge
        return None

    def initialize_game_state(self, start_position: Position | None = None) -> GameState:
        """Initialize a block and bridges after all board objects have been added.

        A start position creates a standing block. Otherwise, use add_block first.
        This method also resets bridges to their initial_open configuration.
        """
        block = self.block
        if start_position is not None:
            block = BlockState((start_position,), Orientation.STANDING)
        if block is None:
            raise ValueError("Add a block or provide a start position before initialization")

        game_state = GameState(
            block,
            frozenset(bridge.bridge_id for bridge in self.bridge if bridge.initial_open),
        )
        self.add_game_state(game_state)
        return game_state
