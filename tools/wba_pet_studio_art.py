"""Native 1bpp implementation of the imagegen-directed facial line language.

The generated sheet is a visual reference, never cropped or downsampled into
firmware. Original eye dimensions, enclosed white highlights, nose and cheek
masks anchor the character; explicit curves author the brows and mouth.
"""
from functools import lru_cache
from pathlib import Path
import hashlib,math
from wba_pet_art_refinement import PetArtRefinement,bounds,stroke


def curve(points,width=3.0):
    """A rounded quadratic or cubic Bezier, rasterized directly at 200px."""
    samples=[];degree=len(points)-1
    for step in range(81):
        t=step/80
        weights=[math.comb(degree,i)*t**i*(1-t)**(degree-i) for i in range(degree+1)]
        samples.append(tuple(sum(weights[i]*points[i][axis] for i in range(degree+1)) for axis in (0,1)))
    return stroke(samples,width)


@lru_cache(maxsize=32)
def enclosed_highlights(eye):
    l,t,r,b=bounds(eye);white={(x,y) for x in range(l,r+1) for y in range(t,b+1) if (x,y) not in eye}
    exterior={p for p in white if p[0] in (l,r) or p[1] in (t,b)};stack=list(exterior)
    while stack:
        x,y=stack.pop()
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
            p=x+dx,y+dy
            if p in white and p not in exterior:exterior.add(p);stack.append(p)
    return frozenset(white-exterior)


def highlight_groups(points):
    todo=set(points);groups=[]
    while todo:
        seed=todo.pop();part={seed};stack=[seed]
        while stack:
            x,y=stack.pop()
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                p=x+dx,y+dy
                if p in todo:todo.remove(p);part.add(p);stack.append(p)
        groups.append(frozenset(part))
    return tuple(sorted(groups,key=len,reverse=True))


@lru_cache(maxsize=32)
def rounded_eye(eye):
    """Round the outer silhouette while retaining enclosed native highlights."""
    l,t,r,b=bounds(eye);highlights=enclosed_highlights(eye);cx=(l+r)/2;cy=(t+b)/2
    rx=(r-l+1)/2;ry=(b-t+1)/2
    return frozenset((x,y) for y in range(t,b+1) for x in range(l,r+1)
        if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1 and (x,y) not in highlights)


class PetStudioArt(PetArtRefinement):
    studio=True
    BROW_STROKE=4.2
    MOUTH_STROKE=3.5
    CLOSED_EYE_STROKE=4.6

    def __init__(self,root,ornaments):
        super().__init__(root,ornaments)
        # Author the charm at native resolution; two rounded lobes converge
        # into a quiet point with the same curve language as the face.
        self.heart=frozenset(
            curve(((9,4),(4,-1),(0,1),(1,7)),2.4)|
            curve(((1,7),(2,11),(6,14),(9,16)),2.4)|
            curve(((9,16),(12,13),(17,9),(17,5)),2.4)|
            curve(((17,5),(17,0),(11,-1),(9,4)),2.4))

    def configure(self,eyes,fixed):
        sources=tuple(frozenset(p for p in eyes if (p[0]<100)==left) for left in (True,False))
        self.eyes=tuple(rounded_eye(part) for part in sources)
        self.highlights=tuple(highlight_groups(enclosed_highlights(part)) for part in sources)
        self.eye_bodies=tuple(set(self.eyes[i])|set().union(*self.highlights[i]) for i in range(2))
        self.fixed=frozenset(fixed)

    @lru_cache(maxsize=512)
    def eye_parts(self,shift=(0,0),closed_mask=0,phase='peak',family='calm'):
        result=set()
        for index,eye in enumerate(self.eyes):
            bit=1<<index;l,t,r,b=bounds(eye);cx=(l+r)/2;cy=(t+b)/2
            if closed_mask&bit and phase=='peak':
                # One clear cheerful arch; no second eyebrow row above it.
                factor=.78 if family=='bashful' else .86 if family=='delighted' else .82
                rise={'warm':12,'bashful':9,'delighted':17,'playful':12,'sleepy':-8}.get(family,12)
                width=(r-l+1)*factor;baseline=cy+4
                glyph=curve(((cx-width/2,baseline),(cx,baseline-rise),(cx+width/2,baseline)),self.CLOSED_EYE_STROKE)
            else:
                # Brief, nearly open transition. Avoid a down-scooped lid that
                # reads as weary or displeased when held by an e-paper panel.
                closure=.48 if closed_mask&bit and phase=='arrive' else .32 if closed_mask&bit and phase=='release' else 0.0
                baseline=cy+4;glyph=set()
                for x,y in self.eye_bodies[index]:
                    u=(x-l)/max(1,r-l);arch=4*u*(1-u)
                    top=t+closure*(baseline-t)-closure*8*arch
                    bottom=b-closure*(b-baseline)+closure*3*arch
                    if top<=y<=bottom:glyph.add((x,y))
                if closure==0:glyph=set(eye)
                else:
                    # A truncated white highlight touches the erased lid and
                    # makes a broken silhouette. Move the original highlight
                    # intact within the aperture, retaining its native size.
                    for highlight in self.highlights[index]:
                        goal=round(closure*14) if len(highlight)>40 else 0
                        for dy in sorted(range(-4,13),key=lambda value:abs(value-goal)):
                            placed={(x,y+dy) for x,y in highlight}
                            if all((x+dx,y+oy) in glyph for x,y in placed for dx,oy in ((0,0),(-1,0),(1,0),(0,-1),(0,1))):
                                glyph.difference_update(placed);break
            result.update((x+shift[0],y+shift[1]) for x,y in glyph)
        return result

    @lru_cache(maxsize=512)
    def brow_parts(self,family,shift=(0,0),closed_mask=0,phase='peak'):
        result=set()
        # Centres stay registered to the original eyes. Family differences
        # use a few pixels of lift/tilt, with one shared rounded stroke weight.
        recipes={'calm':(0,0,0),'curious':(3,-6,1),'delighted':(-6,-6,0),
            'warm':(0,0,-1),'playful':(3,-5,1),'sleepy':(2,2,-1),
            'bashful':(1,1,-3),'thoughtful':(-4,4,1),'focused':(2,2,2),'alert':(-8,-8,0)}
        lifts=recipes[family]
        for index,eye in enumerate(self.eyes):
            if closed_mask&(1<<index) and phase=='peak':continue
            l,t,r,b=bounds(eye);cx=(l+r)/2+shift[0]/3;cy=t-14+lifts[index]+shift[1]/3
            width=21 if not closed_mask&(1<<index) else 15
            inner=lifts[2]*(1 if index==0 else -1)
            result |= curve(((cx-width/2,cy-inner),(cx,cy-5),(cx+width/2,cy+inner)),self.BROW_STROKE)
        return result

    @lru_cache(maxsize=64)
    def mouth_parts(self,family,mouth_family=None,state=''):
        family=mouth_family or family;cx=100.0;y=150.0
        if family in ('curious','alert') or state=='tap_local_sleepy_center':
            rx,ry=(3.5,3.5) if family=='curious' else (4,4.5)
            if state=='tap_local_sleepy_center':rx,ry=4.5,5.5
            return stroke([(cx+rx*math.cos(i*math.pi/40),y+ry*math.sin(i*math.pi/40)) for i in range(81)],3.1)
        if family in ('calm','sleepy'):
            return curve(((90,y-1),(91,y+5),(96,y+5),(100,y)),self.MOUTH_STROKE)|curve(((100,y),(104,y+5),(109,y+5),(110,y-1)),self.MOUTH_STROKE)
        if family in ('thoughtful','focused'):return curve(((92,y+1),(100,y+2),(108,y+1)),self.MOUTH_STROKE)
        if family=='playful':return curve(((91,y+2),(100,y+7),(110,y-3)),self.MOUTH_STROKE)
        if family=='delighted':return curve(((88,y-1),(100,y+14),(112,y-1)),self.MOUTH_STROKE)
        if family=='bashful':return curve(((91,y-1),(100,y+7),(109,y-1)),self.MOUTH_STROKE)
        return curve(((90,y-1),(100,y+9),(110,y-1)),self.MOUTH_STROKE)

    def parts(self,family,shift=(0,0),closed_mask=0,phase='peak',mouth_family=None,state=''):
        eyes=self.eye_parts(shift,closed_mask,phase,family)
        brows=self.brow_parts(family,shift,closed_mask,phase)
        mouth=self.mouth_parts(family,mouth_family,state)
        return eyes,brows,mouth

    def compose(self,family,source_eyes,shift=(0,0),ornament_stage=1):
        closed_mask=3 if family=='sleepy' else 0
        if family=='calm' and len(source_eyes)<450:closed_mask=3
        eyes,brows,mouth=self.parts(family,shift,closed_mask)
        return set(self.fixed)|eyes|brows|mouth|self.ornament(family,ornament_stage)

    def face(self,fixed,eyes,brows,mouth,closed_mask,state,phase='peak',mouth_family=None):
        family=state.split('_')[2] if state.startswith('tap_local_') else state.removeprefix('expression_')
        # Infer only the requested native gaze offset, keeping the common eye
        # centres; every family has the same nose/cheek and eye-body anchors.
        l,t,r,b=bounds(eyes);sl,st,sr,sb=bounds(set(self.eyes[0])|set(self.eyes[1]))
        shift=round((l+r-sl-sr)/2),round((t+b-st-sb)/2)
        eye,brow,mouth=self.parts(family,shift,closed_mask,phase,mouth_family,state)
        return set(self.fixed)|eye|brow|mouth

    def evidence(self):
        result=super().evidence()
        result.update({'face':'registered calm eye dimensions, enclosed white catchlights, nose and cheeks; common anchors for all studio families',
            'closedEyes':'one rounded 4.6px eyelid per eye, separate brows absent; family-specific cheerful arches and relaxed sleepy lids; upper/lower lids converge, intact native-size catchlights move within the aperture',
            'peek':'both original-size eyes open; no weary down-scooped partial lid',
            'lineLanguage':'rounded 4.2px brows, 3.5px compact mouths; restrained family lift/tilt; native 1bpp quantization',
            'strokeWidthsPx':{'brows':self.BROW_STROKE,'mouth':self.MOUTH_STROKE,'closedEyes':self.CLOSED_EYE_STROKE,'heartContour':2.4},
            'heart':'native cubic lobes and tapered point, 2.4px rounded contour',
            'visualReference':'docs/art/iterations/companion-pet-studio-v1/expression-concept-v2.png',
            'bitmapImport':'NONE; concepts guide independently authored native 1bpp curves',
            'sourceSha256':{**result['sourceSha256'],Path(__file__).relative_to(self.root).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}})
        for name in ('expression-concept-v2.png','imagegen-prompt.txt','imagegen-correction-prompt.txt'):
            path=self.root/'docs/art/iterations/companion-pet-studio-v1'/name
            result['sourceSha256'][path.relative_to(self.root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
        return result
