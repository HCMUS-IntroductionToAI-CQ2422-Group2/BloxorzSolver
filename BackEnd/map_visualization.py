"""Export top-down map diagrams with tile legends and switch connections.

Run from the project root: python -m BackEnd.map_visualization
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle

from BackEnd.init_map import MAPS_PATH, init_map
from BackEnd.objects.bridges import Bridge
from BackEnd.objects.switchs import HeavySwitch, SplitSwitch, Switch
from BackEnd.objects.tiles import FragileTile, Goal


DEFAULT_OUTPUT_DIR = MAPS_PATH.parent / 'images'
GRID_SIZE = 17
COLORS = {
    'empty': '#f1f5f9', 'floor': '#cbd5e1', 'fragile': '#fed7aa',
    'goal': '#bbf7d0', 'start': '#172554', 'soft': '#bae6fd',
    'heavy': '#fecdd3', 'split': '#ddd6fe',
    'bridge_open': '#99f6e4', 'bridge_closed': '#fff1f2',
}


def visualize_map(map_name: str, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Save one initialized board as a PNG and return its path."""
    board = init_map(map_name)
    with MAPS_PATH.open(encoding='utf-8') as file:
        maps = json.load(file)
    map_id = next(key for key, data in maps.items() if key == map_name or data['name'] == map_name)
    data = maps[map_id]
    switch_labels = {switch.switch_id: f'S{index}' for index, switch in enumerate(board.switch, 1)}
    bridge_labels = {bridge.bridge_id: f'B{index}' for index, bridge in enumerate(board.bridge, 1)}
    destinations = {
        position for switch in board.switch if isinstance(switch, SplitSwitch)
        for position in switch.teleport_positions
    }

    fig = plt.figure(figsize=(14, 9.5), facecolor='white')
    ax = fig.add_axes((0.045, 0.09, 0.60, 0.79))
    panel = fig.add_axes((0.69, 0.07, 0.29, 0.83))
    panel.set_axis_off()
    fig.text(0.05, 0.95, f"{map_id.upper()}  /  {data['name']}",
             fontsize=23, weight='bold', color='#172554')
    fig.text(0.05, 0.915, 'TOP VIEW  |  Initial board state  |  Coordinates: (x, y)',
             fontsize=11, color='#475569')

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            tile = board.get_tile((x, y))
            color, label, hatch = COLORS['empty'], '', None
            edge = '#dbe3ec'
            if tile is not None:
                color = COLORS['floor']
            if isinstance(tile, FragileTile):
                color, hatch = COLORS['fragile'], '//'
            elif isinstance(tile, Goal):
                color, label = COLORS['goal'], 'G'
            elif isinstance(tile, Bridge):
                color = COLORS['bridge_open' if tile.initial_open else 'bridge_closed']
                label = bridge_labels[tile.bridge_id]
                edge = '#0f766e' if tile.initial_open else '#e11d48'
                hatch = None if tile.initial_open else 'xx'
            elif isinstance(tile, Switch):
                kind = 'split' if isinstance(tile, SplitSwitch) else (
                    'heavy' if isinstance(tile, HeavySwitch) else 'soft'
                )
                color = COLORS[kind]
                symbol = {'soft': 'O', 'heavy': 'X', 'split': 'T'}[kind]
                label = f"{switch_labels[tile.switch_id]}\n{symbol}"

            ax.add_patch(Rectangle((x-0.5, y-0.5), 1, 1, facecolor=color,
                                   edgecolor=edge, linewidth=0.7, hatch=hatch))
            if (x, y) in destinations:
                ax.add_patch(Rectangle((x-0.40, y-0.40), 0.8, 0.8, fill=False,
                                       edgecolor='#7c3aed', linewidth=1.8, linestyle=':'))
                ax.text(x-0.32, y-0.30, 'TP', fontsize=5.5, weight='bold', color='#6d28d9')
            if isinstance(tile, Goal):
                ax.add_patch(Circle((x, y), 0.29, facecolor='#166534', edgecolor='none'))
            if label:
                ax.text(x, y+0.02, label, ha='center', va='center', fontsize=8,
                        weight='bold', color='white' if isinstance(tile, Goal) else '#172554')

    for x, y in board.block.positions:
        ax.add_patch(Rectangle((x-0.42, y-0.42), 0.84, 0.84,
                               facecolor=COLORS['start'], edgecolor='white', linewidth=1.2))
        ax.text(x, y, 'START', ha='center', va='center', fontsize=6.5,
                weight='bold', color='white')

    ax.set(xlim=(-0.5, GRID_SIZE-0.5), ylim=(GRID_SIZE-0.5, -0.5), aspect='equal')
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.xaxis.tick_top()
    ax.tick_params(length=0, labelsize=8, pad=5)
    ax.set_xlabel('x  →', loc='right', color='#64748b', fontsize=10)
    ax.xaxis.set_label_position('top')
    ax.set_ylabel('y', loc='top', rotation=0, labelpad=12, color='#64748b', fontsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)

    legend = [
        Patch(facecolor=COLORS['floor'], label='Floor'),
        Patch(facecolor=COLORS['fragile'], hatch='//', label='Fragile tile'),
        Patch(facecolor=COLORS['goal'], label='G: Goal'),
        Patch(facecolor=COLORS['start'], label='START: Block start'),
        Patch(facecolor=COLORS['soft'], label='O: Soft switch'),
        Patch(facecolor=COLORS['heavy'], label='X: Heavy switch'),
        Patch(facecolor=COLORS['split'], label='T: Split switch'),
        Patch(facecolor=COLORS['bridge_open'], label='Bridge: initially open'),
        Patch(facecolor=COLORS['bridge_closed'], hatch='xx', label='Bridge: initially closed'),
        Patch(facecolor='none', edgecolor='#7c3aed', linestyle=':', label='TP: Teleport destination'),
        Patch(facecolor=COLORS['empty'], label='Empty space'),
    ]
    panel.legend(handles=legend, loc='upper left', bbox_to_anchor=(0, 1), frameon=False,
                 title='MAP LEGEND', fontsize=9, title_fontsize=11, labelspacing=0.6)

    lines = ['BRIDGES']
    for bridge in board.bridge:
        label = bridge_labels[bridge.bridge_id]
        status = 'OPEN' if bridge.initial_open else 'CLOSED'
        lines.append(f'{label}: ({bridge.x}, {bridge.y}), {bridge.w}x{bridge.h}  |  {status}')
    if not board.bridge:
        lines.append('None')
    lines.extend(('', 'SWITCH CONNECTIONS'))
    for switch in board.switch:
        kind = 'Split' if isinstance(switch, SplitSwitch) else (
            'Heavy' if isinstance(switch, HeavySwitch) else 'Soft'
        )
        lines.append(f'{switch_labels[switch.switch_id]}: {kind} at ({switch.x}, {switch.y})')
        for effect in switch.effects:
            mode = effect.effect_mode.value
            if mode == 'set':
                mode = 'open' if effect.target_open else 'close'
            lines.append(f'    {bridge_labels[effect.bridge_id]}: {mode}')
        if isinstance(switch, SplitSwitch):
            first, second = switch.teleport_positions
            lines.append(f'    TP: {first} and {second}')
    if not board.switch:
        lines.append('None')
    panel.text(0.025, 0.60, '\n'.join(lines), transform=panel.transAxes,
               va='top', fontsize=9, linespacing=1.55, color='#334155')

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'{map_id}.png'
    fig.savefig(output_path, dpi=140, facecolor='white')
    plt.close(fig)
    return output_path


def visualize_all_maps(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Export one PNG for every map in maps.json."""
    with MAPS_PATH.open(encoding='utf-8') as file:
        maps = json.load(file)
    return [visualize_map(map_name, output_dir) for map_name in maps]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps', nargs='*', help='Map keys or names; omit to export all maps.')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = ([visualize_map(name, args.output_dir) for name in args.maps]
             if args.maps else visualize_all_maps(args.output_dir))
    for path in paths:
        print(path)
