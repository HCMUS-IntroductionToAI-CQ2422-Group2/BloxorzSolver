import math
from time import monotonic
import pygame
from FrontEnd.fall_motion import fall_vertex


def clip_floor(vertices, side=1):
    result = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if side*a[2] >= 0:
            result.append(a)
        if (side*a[2] >= 0) != (side*b[2] >= 0):
            t = a[2] / (a[2] - b[2])
            result.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
    return result


def draw_wood(surface, state, project, scale, animation, layer=None):
    elapsed = monotonic() - animation['start'] if animation else 0
    roll_seconds = min(.28, animation.get('duration', .28)) if animation else .28
    rolling = animation is not None and elapsed < roll_seconds
    terminal = animation and animation['status'] in ('won', 'lost')
    lost = bool(terminal and animation['status'] == 'lost')
    fall = max(0, (elapsed - roll_seconds) / .82) if terminal else 0
    if terminal and fall >= 1:
        return
    plan = animation.get('fall_plan') if animation else None
    block = animation['before'].block if rolling else plan['state'].block if lost and plan else state.block
    direction = animation['action'].value if animation else ''
    dx = {'left': -1, 'right': 1}.get(direction, 0)
    dy = {'up': -1, 'down': 1}.get(direction, 0)
    rotate = rolling
    t = min(1, elapsed / roll_seconds) if animation else 0
    angle = (t*t*(3-2*t)) * math.pi/2
    drop = 5 * fall * fall if terminal and not lost else 0
    fade = max(0, min(1, (fall - .75) / .25)) if lost else 0
    shrink = 1
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
            if lost and not rolling and plan:
                # A resting split cube must not fall with the unsupported cube.
                if not block.is_split() or (x, y) not in plan['supported']:
                    return fall_vertex((a,b,z), plan, elapsed - roll_seconds)
            if terminal and not lost: z-=drop
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
        shadow_fall = fall*1.7 if lost else fall
        for spread,alpha in ((14,12),(8,20),(2,38)):
            pygame.draw.ellipse(shadow,(4,12,16,int(alpha*max(0,1-shadow_fall))),bounds.inflate(spread,spread))
        if layer != "below":
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
        # Falling off the board shrinks toward the cube's own centre (a cheap "receding into
        # the distance" trick) instead of staying full-size until it abruptly disappears.
        center_pixel = project(x+w/2, y+d/2, h/2) if shrink != 1 else None
        def to_pixel(v):
            px, py = project(*v)
            if center_pixel is not None:
                px = center_pixel[0] + (px-center_pixel[0])*shrink
                py = center_pixel[1] + (py-center_pixel[1])*shrink
            return (px, py)
        target_surface = surface
        if lost and fade > 0:
            target_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for _,polygon,color in sorted(visible):
            clip_side = -1 if layer == 'below' else 1
            clipping = layer is not None or (terminal and animation['status']=='won')
            clipped = clip_floor(polygon, clip_side) if clipping else polygon
            if len(clipped)<3: continue
            pixels=[to_pixel(v) for v in clipped]
            pygame.draw.polygon(target_surface,color,pixels)
            # Grain follows the actual rotating face rather than the screen axes.
            a,b,c,d=polygon
            for line in range(1,12):
                f=line/12
                points=[]
                for step in range(17):
                    t=step/16
                    grain=f+.009*math.sin(t*16+line*1.8)
                    v=tuple((a[i]*(1-t)+d[i]*t)*(1-grain)+(b[i]*(1-t)+c[i]*t)*grain for i in range(3))
                    if clipping and clip_side*v[2]<0:
                        if len(points)>1: pygame.draw.lines(target_surface,tuple(max(0,c-24) for c in color),False,points,1)
                        points=[]
                    else: points.append(to_pixel(v))
                if len(points)>1: pygame.draw.lines(target_surface,tuple(max(0,c-24) for c in color),False,points,1)
            edge_color = tuple(min(255,c+27) for c in color)
            if clipping:
                # Only outline physical edges; the occlusion plane is not a cut
                # in the timber and must not draw a bright seam across its face.
                for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                    a_visible, b_visible = clip_side*a[2] >= 0, clip_side*b[2] >= 0
                    if not a_visible and not b_visible:
                        continue
                    if a_visible != b_visible:
                        t = a[2] / (a[2] - b[2])
                        crossing = tuple(a[i] + t*(b[i]-a[i]) for i in range(3))
                        if a_visible:
                            b = crossing
                        else:
                            a = crossing
                    pygame.draw.line(target_surface, edge_color, to_pixel(a), to_pixel(b), 1)
            else:
                pygame.draw.lines(target_surface, edge_color, True, pixels, 1)
        if target_surface is not surface:
            target_surface.set_alpha(int(255*(1-fade)))
            surface.blit(target_surface,(0,0))
        if block.is_split() and index==block.active_cube and not terminal:
            pygame.draw.circle(surface,'#58dec0',to_pixel((x+.5,y+.5,1.2)),3)
