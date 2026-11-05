"""Native-size facial acting and sparse accents for deliberate pet replies."""
from functools import lru_cache
from pathlib import Path
import hashlib
import math

STYLES={
    'tap_local_curious_up':(-4,0,-1,'sparkle','期待地歪头'),
    'tap_local_curious_left':(4,-1,0,'','换一边看你'),
    'tap_local_warm_center':(2,0,0,'sparkle','亲近地迎接'),
    'tap_local_warm_up':(0,0,-1,'heart','舒服地眯眼'),
    'tap_local_warm_down':(4,2,0,'heart','轻轻蹭一下'),
    'tap_local_warm_left':(-2,-1,0,'heart','柔和地侧看浅笑'),
    'tap_local_playful_right':(4,0,0,'sparkle','右眼俏皮眨眼'),
    'tap_local_playful_left':(-4,0,0,'sparkle','左眼俏皮眨眼'),
    'tap_local_playful_center':(-2,0,0,'','留一个俏皮笑'),
    'tap_local_delighted_center':(2,0,0,'sparkle','笑弯眼与星光'),
    'tap_local_delighted_up':(-3,0,-1,'','惊喜地抬眉'),
    'tap_local_bashful_down':(-4,0,1,'heart','害羞地躲一下'),
    'tap_local_bashful_left':(4,-1,0,'','再偷偷看一眼'),
    'tap_local_sleepy_center':(-3,0,0,'','困倦的小哈欠'),
}

class PetPerformance:
    def __init__(self,root,ornaments,refinement=None):
        if ornaments is None:raise ValueError('Pet acting needs the registered charm layer')
        self.root=Path(root);self.ornaments=ornaments;self.refinement=refinement

    @staticmethod
    @lru_cache(maxsize=None)
    def transform(face,angle,dx,dy):
        # Rigid native-scale rotation, inverse nearest-neighbor rasterization.
        # Eyes/highlights/brows/nose/cheeks stay together; no face resizing or
        # sparse forward-map holes inside the black eyes.
        sine=math.sin(math.radians(angle));cosine=math.cos(math.radians(angle))
        ink=set()
        for y in range(36,173):
            for x in range(18,183):
                px=x-100-dx;py=y-114-dy
                source=(round(cosine*px+sine*py+100),round(-sine*px+cosine*py+114))
                if source in face:ink.add((x,y))
        return frozenset(ink)

    def frame(self,face,family,state,phase='peak'):
        from wba_emotion_ornaments import place
        angle,dx,dy,accent,_=STYLES[state]
        if self.refinement:
            angle=angle/2
            if phase=='arrive':angle/=2;dx=dy=0
            elif phase=='release':angle/=3;dx=dy=0
            return self.transform(frozenset(face),angle,dx,dy)|self.refinement.ornament(family)
        ink=self.transform(frozenset(face),angle,dx,dy)|self.ornaments.frame(family,2)
        if accent=='heart':ink |= place(self.ornaments.heart,39,58)
        elif accent=='sparkle':ink |= place(self.ornaments.sparkle,39,57)
        if any(not (0<=x<200 and 16<=y<174) for x,y in ink):
            raise ValueError('Acting leaves the reserved pet area: '+state)
        return ink

    def evidence(self):
        return {'acting':('rigid native-scale lean of at most two degrees; smaller arrive/release offsets' if self.refinement else
                'rigid native-scale lean of at most four degrees; registered facial proportions retained'),
            'accents':('one compact family ornament; no mirrored reply ornaments' if self.refinement else
                'one native heart or sparkle at the opposite upper corner only during a deliberate reply'),
            'styles':{state:row[4] for state,row in STYLES.items()},
            'idle':'original clean native face; reply accents disappear on visible settle',
            'sourceSha256':{Path(__file__).relative_to(self.root).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}}
