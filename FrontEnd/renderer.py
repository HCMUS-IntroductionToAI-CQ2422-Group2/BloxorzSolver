import pygame
import math
from FrontEnd.wood import draw_wood
from time import monotonic

from BackEnd.objects.bridges import Bridge
from BackEnd.objects.switchs import HeavySwitch, SoftSwitch, SplitSwitch
from BackEnd.objects.tiles import EmptyCell, FragileTile, Goal

BG = "#0c1424"
PANEL = "#271f20"
TEXT = "#eaf1fb"
MUTED = "#c3aaa0"
ACCENT = "#dba66b"


class Renderer:
    def __init__(self):
        self.fonts = {size: pygame.font.SysFont("Segoe UI", size) for size in (14, 16, 18, 22, 32)}

    def text(self, surface, value, pos, size=16, color=TEXT):
        surface.blit(self.fonts[size].render(str(value), True, color), pos)

    def background(self, surface):
        w,h = surface.get_size()
        if not hasattr(self, '_background') or self._background.get_size() != (w,h):
            # A cached sunset canyon keeps animation frames inexpensive.
            image = pygame.Surface((w,h))
            for y in range(h):
                t=y/h
                color=(int(138*(1-t)+26*t),int(49*(1-t)+17*t),int(30*(1-t)+25*t))
                pygame.draw.line(image,color,(0,y),(w,y))
            glow=pygame.Surface((w,h),pygame.SRCALPHA)
            for radius in range(230,30,-3):
                pygame.draw.circle(glow,(255,151,67,2),(int(w*.67),int(h*.18)),radius)
            image.blit(glow,(0,0))
            pygame.draw.circle(image,'#d78b51',(int(w*.67),int(h*.18)),46)
            for layer,color in enumerate(('#813d30','#592f2b','#352328','#211c24')):
                base=h*(.48+layer*.14)
                points=[(0,h),(0,base)]
                for x in range(0,w+65,65):
                    ridge=math.sin(x*.008+layer*2)*55+math.sin(x*.021+layer)*22
                    points.append((x,base-ridge))
                points.append((w,h))
                pygame.draw.polygon(image,color,points)
            for index in range(45):
                x=(index*179+47)%w; y=(index*83+151)%h
                pygame.draw.circle(image,'#aa6844',(x,y),1)
            self._background=image
        surface.blit(self._background,(0,0))

    def board(self, surface, board, state, area, animation=None):
        positions = {p for tile in board.tile + board.bridge for p in tile.get_positions()}
        us = [x-y for x,y in positions]
        vs = [x+y for x,y in positions]
        scale = min(36, (area.width-100)/(max(us)-min(us)+2), (area.height-110)/((max(vs)-min(vs)+2)*.5))
        ox = area.centerx - (min(us)+max(us)+0)*scale/2
        oy = area.centery - (min(vs)+max(vs)+2)*scale/4 + 45
        def point(x,y,z=0):
            return (ox+(x-y)*scale, oy+(x+y)*scale*.5-z*scale)
        def prism(x,y,w,d,z,height,wood=False,color="#a5b6af"):
            base = [point(x,y,z),point(x+w,y,z),point(x+w,y+d,z),point(x,y+d,z)]
            top = [point(x,y,z+height),point(x+w,y,z+height),point(x+w,y+d,z+height),point(x,y+d,z+height)]
            pygame.draw.polygon(surface, "#6f3d25" if wood else "#435a59", [base[1],base[2],top[2],top[1]])
            pygame.draw.polygon(surface, "#9e6236" if wood else "#607775", [base[2],base[3],top[3],top[2]])
            pygame.draw.polygon(surface, "#dfac68" if wood else color, top)
            pygame.draw.lines(surface, "#f3ce90" if wood else "#c0cec0", True, top, 1)
            if wood:
                for i in range(1,7):
                    t=i/7
                    pygame.draw.line(surface, "#be874e", point(x+.09,y+d*t,z+height+.01), point(x+w-.09,y+d*t,z+height+.01), 1)
                    pygame.draw.line(surface, "#b77b45", point(x+w*t,y+d,z+.08), point(x+w*t,y+d,z+height-.06), 1)
                for edge in ((1,2),(2,3)):
                    pygame.draw.line(surface, "#e1ad6b", top[edge[0]], top[edge[1]], 2)
        bridge_state = animation["before"] if animation and monotonic() - animation["start"] < .28 else state
        for x,y in sorted(positions,key=lambda p:sum(p)):
            tile=board.get_tile((x,y))
            if isinstance(tile,Bridge) and not tile.is_open(bridge_state):
                continue
            if isinstance(tile,EmptyCell):
                continue
            color = "#b3c2b2"
            if isinstance(tile,FragileTile): color="#de9b63"
            if isinstance(tile,Bridge):
                color="#886446"
            if isinstance(tile,(SoftSwitch,HeavySwitch,SplitSwitch)): color="#73716a"
            prism(x+.035,y+.035,.93,.93,-.23,.23,color=color)
            center=point(x+.5,y+.5,.015)
            if isinstance(tile,Goal):
                pygame.draw.polygon(surface,"#091c24",[point(x+.035,y+.035,.01),point(x+.965,y+.035,.01),point(x+.965,y+.965,.01),point(x+.035,y+.965,.01)])
            elif isinstance(tile,Bridge) and not tile.is_open(bridge_state):
                pygame.draw.line(surface,"#d28383",point(x+.2,y+.2,.02),point(x+.8,y+.8,.02),2)
            elif isinstance(tile,(SoftSwitch,HeavySwitch,SplitSwitch)):
                label="O" if isinstance(tile,SoftSwitch) else "X" if isinstance(tile,HeavySwitch) else "( )"
                glyph=self.fonts[16].render(label,True,"#282724")
                surface.blit(glyph,glyph.get_rect(center=center))
        draw_wood(surface, state, point, scale, animation)

    def legend(self, surface, x, y):
        items = [("#8799b2", "Floor"), ("#eeaa65", "Fragile"),
                 ("#b7a3eb", "O / X / ( ) switches"), (ACCENT, "Open bridge"),
                 ("#e18394", "Closed bridge")]
        for color, label in items:
            pygame.draw.rect(surface, color, (x, y + 4, 12, 12), border_radius=3)
            self.text(surface, label, (x + 19, y), 14, MUTED)
            x += self.fonts[14].size(label)[0] + 39
