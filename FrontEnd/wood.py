import math
from time import monotonic
import pygame


def clip_floor(vertices):
    result = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if a[2] >= 0:
            result.append(a)
        if (a[2] >= 0) != (b[2] >= 0):
            t = a[2] / (a[2] - b[2])
            result.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
    return result


def draw_wood(surface, state, project, scale, animation):
    elapsed = monotonic() - animation['start'] if animation else 0
    rolling = animation is not None and elapsed < .28
    terminal = animation and animation['status'] in ('won', 'lost')
    fall = max(0, (elapsed - .28) / .82) if terminal else 0
    if terminal and fall >= 1:
        return
    block = animation['before'].block if rolling or (terminal and animation['status'] == 'lost') else state.block
    direction = animation['action'].value if animation else ''
    dx = {'left': -1, 'right': 1}.get(direction, 0)
    dy = {'up': -1, 'down': 1}.get(direction, 0)
    rotate = rolling or (terminal and animation['status'] == 'lost')
    t = min(1, elapsed / .28) if animation else 0
    angle = (t*t*(3-2*t)) * math.pi/2
    cubes = [(p[0],p[1],1,1,1,i) for i,p in enumerate(block.positions)] if block.is_split() else [
        (min(p[0] for p in block.positions), min(p[1] for p in block.positions),
         max(p[0] for p in block.positions)-min(p[0] for p in block.positions)+1,
         max(p[1] for p in block.positions)-min(p[1] for p in block.positions)+1,
         2 if block.is_standing() else 1,0)]
    for x,y,w,d,h,index in sorted(cubes, key=lambda c:c[0]+c[1]):
        moving = rotate and (not block.is_split() or index == block.active_cube)
        pivot = x+w if dx>0 else x if dx else y+d if dy>0 else y
        def transform(v):
            a,b,z=v
            if moving:
                sign=dx or dy
                q=(a if dx else b)-pivot
                horizontal=pivot+q*math.cos(angle)+sign*z*math.sin(angle)
                z=-sign*q*math.sin(angle)+z*math.cos(angle)
                if dx: a=horizontal
                else: b=horizontal
            if terminal: z-=5*fall*fall
            return (a,b,z)
        inset=.035
        vertices=[transform((a,b,z)) for z in (inset,h-inset)
                  for a,b in ((x+inset,y+inset),(x+w-inset,y+inset),
                              (x+w-inset,y+d-inset),(x+inset,y+d-inset))]
        shadow=pygame.Surface(surface.get_size(),pygame.SRCALPHA)
        ground=[project(v[0]+.13,v[1]+.13,0) for v in vertices]
        bounds=pygame.Rect(min(p[0] for p in ground),min(p[1] for p in ground),
                           max(p[0] for p in ground)-min(p[0] for p in ground),
                           max(p[1] for p in ground)-min(p[1] for p in ground))
        for spread,alpha in ((14,12),(8,20),(2,38)):
            pygame.draw.ellipse(shadow,(4,12,16,int(alpha*max(0,1-fall))),bounds.inflate(spread,spread))
        surface.blit(shadow,(0,0))
        faces=[(0,3,2,1),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5),(4,5,6,7)]
        visible=[]
        for face in faces:
            polygon=[vertices[i] for i in face]
            a,b,c=polygon[:3]
            u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
            normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            if sum(normal) <= 0: continue
            brightness=(normal[0]*.48+normal[1]*.72+normal[2]) / math.sqrt(sum(n*n for n in normal))
            color=tuple(int(c*(.55+.4*brightness)) for c in (157,100,57))
            visible.append((sum(sum(v) for v in polygon),polygon,color))
        for _,polygon,color in sorted(visible):
            clipped=clip_floor(polygon) if terminal and animation['status']=='won' else polygon
            if len(clipped)<3: continue
            pixels=[project(*v) for v in clipped]
            pygame.draw.polygon(surface,color,pixels)
            # Grain follows the actual rotating face rather than the screen axes.
            a,b,c,d=polygon
            for line in range(1,12):
                f=line/12
                points=[]
                for step in range(17):
                    t=step/16
                    grain=f+.009*math.sin(t*16+line*1.8)
                    v=tuple((a[i]*(1-t)+d[i]*t)*(1-grain)+(b[i]*(1-t)+c[i]*t)*grain for i in range(3))
                    if terminal and animation['status']=='won' and v[2]<0:
                        if len(points)>1: pygame.draw.lines(surface,tuple(max(0,c-24) for c in color),False,points,1)
                        points=[]
                    else: points.append(project(*v))
                if len(points)>1: pygame.draw.lines(surface,tuple(max(0,c-24) for c in color),False,points,1)
            pygame.draw.lines(surface,tuple(min(255,c+27) for c in color),True,pixels,1)
        if block.is_split() and index==block.active_cube and not terminal:
            pygame.draw.circle(surface,'#58dec0',project(x+.5,y+.5,1.2),3)
