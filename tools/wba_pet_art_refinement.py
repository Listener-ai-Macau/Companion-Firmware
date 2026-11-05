"""Code-native eye acting and quieter decoration over retained facial masks."""
from pathlib import Path
import hashlib,math

def bounds(points):
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)

def compact(points,width,height):
    l,t,r,b=bounds(points);sw=r-l+1;sh=b-t+1
    return frozenset((x,y) for y in range(height) for x in range(width)
        if (l+x*sw//width,t+y*sh//height) in points)

def stroke(points,width=2.6):
    ink=set();radius=width/2
    for px,py in points:
        for y in range(math.floor(py-radius),math.ceil(py+radius)+1):
            for x in range(math.floor(px-radius),math.ceil(px+radius)+1):
                if (x-px)**2+(y-py)**2<=radius**2:ink.add((x,y))
    return ink

class PetArtRefinement:
    def __init__(self,root,ornaments):
        from wba_emotion_ornaments import contour
        self.root=Path(root);self.ornaments=ornaments
        self.heart=contour(compact(ornaments.read('charm_heart'),18,17),2)

    @staticmethod
    def eyelids(eyes,closed_mask,phase):
        result=set()
        for left,bit in ((True,1),(False,2)):
            eye={p for p in eyes if (p[0]<100)==left}
            l,t,r,b=bounds(eye);height=b-t+1;cx=(l+r)/2;cy=(t+b)/2
            if closed_mask&bit and phase=='peak':
                # A single rounded smile arc. Brows retract while an eye is
                # shut, so the pose does not become four parallel dashes.
                width=(r-l+1)*0.72;baseline=cy+2
                curve=[]
                for n in range(81):
                    u=n/80;curve.append((cx-width/2+u*width,baseline-5.5*4*u*(1-u)))
                result |= stroke(curve)
            else:
                # The eyelid covers the upper eye. Do not vertically squash
                # its highlights into a pancake-shaped pupil.
                opening=(0.68 if phase=='arrive' else 0.84) if closed_mask&bit else 1.0
                if phase=='peek':opening=0.84
                for y in range(t,b+1):
                    for x in range(l,r+1):
                        u=(x-l)/max(1,r-l)
                        lid=t+height*(1-opening)-2*4*u*(1-u)
                        if y>=lid and (x,y) in eye:result.add((x,y))
        return result

    @staticmethod
    def brows(brows,closed_mask,phase):
        result=set()
        for left,bit in ((True,1),(False,2)):
            part={p for p in brows if (p[0]<100)==left}
            if not part:continue
            if closed_mask&bit and phase=='peak':continue
            l,t,r,b=bounds(part);height=b-t+1;target=2 if closed_mask&bit else height
            result |= {(x,t+round((y-t)*max(1,target-1)/max(1,height-1))+3) for x,y in part}
        return result

    def face(self,fixed,eyes,brows,mouth,closed_mask,state,phase='peak'):
        eye_phase='peek' if state in ('tap_local_bashful_left','tap_local_warm_left') and phase=='peak' else phase
        return set(fixed)|self.eyelids(eyes,closed_mask,eye_phase)|self.brows(brows,closed_mask,phase)|set(mouth)

    def ornament(self,family,stage=1):
        from wba_emotion_ornaments import place
        lift={0:1,1:0,2:-2,3:0,4:1}[stage]
        if family in ('warm','bashful'):return place(self.heart,154,54+lift)
        return self.ornaments.frame(family,stage)

    def evidence(self):
        return {'face':'native calm eye/nose/cheek anchors; family brows and mouth align to the same nose',
            'closedEyes':'rounded smile arcs, brows retract over closed eyes; native highlights retained in intermediate masks',
            'peek':'upper eyelids softly cover both eyes; native highlight size retained',
            'ornaments':'one 18 by 17 two-pixel native-contour heart; no mirrored hearts',
            'motion':'arrive, peak, release lid masks; native eye dimensions and highlights retained',
            'sourceSha256':{Path(__file__).relative_to(self.root).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}}
