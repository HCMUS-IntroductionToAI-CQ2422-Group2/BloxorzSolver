import json
from pathlib import Path

TARGETS = {'map01': 7, 'map02': 17, 'map03': 21, 'map04': 28, 'map05': 33, 'map06': 35, 'map07': 44, 'map08': 11, 'map09': 25, 'map10': 58, 'map11': 47, 'map12': 65, 'map13': 46, 'map14': 67, 'map15': 60, 'map16': 29, 'map17': 106, 'map18': 85, 'map19': 67, 'map20': 58,
           'map21': 7, 'map22': 11, 'map23': 7, 'map24': 18, 'map25': 15, 'map26': 13, 'map27': 28, 'map28': 27, 'map29': 24, 'map30': 19, 'map31': 22, 'map32': 40, 'map33': 29, 'map34': 48, 'map35': 42}


def stars_for(level, moves):
    target = TARGETS[level]
    return 3 if moves <= target else 2 if moves <= target * 1.5 else 1


class Progress:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).resolve().parents[1] / '.save' / 'progress.json'
        self.records = {}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                self.records = {k: v for k,v in data.items() if k in TARGETS and isinstance(v,dict)
                                and type(v.get('stars')) is int and 1 <= v['stars'] <= 3
                                and type(v.get('moves')) is int and v['moves'] >= 0}
        except (OSError, ValueError):
            pass

    def unlocked(self, level):
        return all(f'map{i:02}' in self.records for i in range(1,int(level[3:])))

    def complete(self, level, moves):
        stars = stars_for(level, moves)
        old = self.records.get(level)
        if old is None or moves < old['moves']:
            self.records[level] = {'stars': stars, 'moves': moves}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.records, indent=2), encoding='utf-8')
        temporary.replace(self.path)
        return stars
