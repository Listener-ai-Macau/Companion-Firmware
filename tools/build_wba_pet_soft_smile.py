"""Import a reviewed generated mouth into retained delighted whole faces.

No procedural curves or runtime overlay: the bank still contains complete
authored frames. Other anatomy, families, reaction peaks, fonts, geometry and
the original CEMP are preserved. Input/output banks must be separate.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil, struct, zlib
from PIL import Image
from build_emote_asset_pack import decode_packbits
from build_wba_product_resources import fnv, xor_patch, life_states
from wba_resource_geometry import geometry

sha = lambda b: hashlib.sha256(b).hexdigest()


class Bank:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.profile = json.loads((self.directory/'profile.json').read_bytes())
        self.data = (self.directory/'ui-partition.bin').read_bytes()
        assert sha(self.data).upper() == self.profile['uiPartitionSha256'].upper()
        self.geo = geometry(len(self.data))
        self.root = self.data[self.geo['rootA']:self.geo['rootA']+128]
        assert zlib.crc32(self.root[:124]) == struct.unpack_from('<I', self.root, 124)[0]
        self.blob, self.blob_n = struct.unpack_from('<II', self.root, 16)
        self.count, size = struct.unpack_from('<HH', self.data, self.blob+8)
        assert size == 24
        self.entries = {}
        for i in range(self.count):
            at = self.blob+32+i*24
            row = struct.unpack_from('<IHHIIHHI', self.data, at)
            self.entries[row[0]] = (at, row)
        self.frame_table = struct.unpack_from('<I', self.data, 36)[0]
        self.payload = struct.unpack_from('<I', self.data, 48)[0]
        self.canonical = {}

    def base(self, index):
        if index not in self.canonical:
            offset, n = struct.unpack_from('<II', self.data, self.frame_table+index*20)
            self.canonical[index] = decode_packbits(self.data[self.payload+offset:self.payload+offset+n], 5000)
        return self.canonical[index]

    def frame(self, row):
        h, index, flags, crc, offset, n, duration, pcrc = row
        payload = self.data[offset:offset+n]
        assert not n or zlib.crc32(payload) == pcrc
        if flags == 2:
            raw = decode_packbits(payload, 5000)
        elif flags == 1:
            raw = payload
        else:
            assert flags in (0, 4), flags
            raw = bytearray(self.base(index))
            if flags:
                cursor = previous = 0
                while cursor < n:
                    start, length = struct.unpack_from('<HB', payload, cursor)
                    cursor += 3
                    assert length and start >= previous and start+length <= 5000 and cursor+length <= n
                    for j in range(length):
                        raw[start+j] ^= payload[cursor+j]
                    cursor += length
                    previous = start+length
                assert cursor == n
            raw = bytes(raw)
        assert len(raw) == 5000 and zlib.crc32(raw) == crc
        return raw


def mouth(image):
    # The input whole face has already been inspected. This isolated rectangle
    # is below the nose and between cheeks; no facial line is synthesized.
    points = {(x,y) for y in range(144,165) for x in range(83,118) if image.getpixel((x,y)) == 0}
    if not points:
        return None
    l,t,r,b = min(x for x,y in points), min(y for x,y in points), max(x for x,y in points), max(y for x,y in points)
    return points, (l,t,r,b)


def build(base, art, output):
    assert not output.exists() and base.resolve() != output.resolve()
    bank = Bank(base)
    assert bank.profile['generation'] == 84 and 'softSmile' not in bank.profile
    native = Image.open(art)
    assert native.size == (200,200) and set(native.convert('L').getdata()) <= {0,255}
    new_points, box = mouth(native)
    assert box[2]-box[0]+1 <= 24 and box[3]-box[1]+1 <= 8, box
    ref = bank.frame(bank.entries[fnv('expression_delighted_v0_0_hold')][1])
    old_points, old_box = mouth(Image.frombytes('1', (200,200), ref))
    assert 20 <= old_box[2]-old_box[0]+1 <= 30 and 6 <= old_box[3]-old_box[1]+1 <= 15
    # Import the actual thresholded generated pixels, keeping the native
    # authored centre/top anchor. Do not stretch or draw a replacement curve.
    dx = (old_box[0]+old_box[2]-box[0]-box[2])//2
    dy = old_box[1]-box[1]
    replacement = {(x+dx,y+dy) for x,y in new_points}
    # Store new XORs only in unreferenced metadata retired by the UI84 menu.
    header = (base/'companion_wba_customer_ui.h').read_text()
    value = lambda name: int(re.search(r'#define '+name+r' (\d+)u', header)[1])
    free_start = value('COMP_CUSTOMER_ATLAS_OFFSET')+value('COMP_CUSTOMER_ATLAS_BYTES')
    payload_start = min(row[4] for _,row in bank.entries.values() if row[2] and row[5])
    assert bank.blob+32+bank.count*24 <= free_start < payload_start
    image = bytearray(bank.data); payloads = {}; changed = {}; skipped = []
    names = life_states() | {'expression_delighted_v0_0_hold'}
    names |= {f'pointer_follow_delighted_gx{x}_gy{y}' for x in range(9) for y in range(9)}
    names |= {f'pet_motion_delighted_{zone}_{phase}' for zone in ('center','up','down','left','right')
              for phase in ('arrive','release')}
    for name in sorted(names):
        # Rest, gaze and existing daily/action entry/release frames. The
        # expressive tap_local peaks and all transition art remain original.
        if not name.startswith(('expression_delighted_', 'pointer_follow_delighted_',
                                'life_delighted_', 'pet_motion_delighted_')):
            continue
        item = bank.entries.get(fnv(name))
        if item is None:
            continue
        at,row = item
        raw = bank.frame(row); original = Image.frombytes('1',(200,200),raw)
        current = mouth(original)
        normalize = lambda points: {(x-min(a for a,b in points),y-min(b for a,b in points)) for x,y in points}
        if current is None or normalize(current[0]) != normalize(old_points):
            skipped.append(name)
            continue
        shift_x = current[1][0]-old_box[0]
        shift_y = current[1][1]-old_box[1]
        edited = original.copy()
        for x,y in current[0]:
            edited.putpixel((x,y),1)
        for x,y in replacement:
            edited.putpixel((x+shift_x,y+shift_y),0)
        target = edited.tobytes()
        assert all(a == b for y in range(200) for x in range(200)
                   if not (83 <= x < 118 and 144 <= y < 165)
                   for a,b in [(original.getpixel((x,y)),edited.getpixel((x,y)))])
        patch = xor_patch(bank.base(row[1]),target)
        if patch not in payloads:
            offset = free_start+sum(len(p) for p in payloads)
            assert offset+len(patch) <= payload_start, 'No safe static space; do not move recording boundary'
            payloads[patch] = offset
            image[offset:offset+len(patch)] = patch
        struct.pack_into('<IHHIIHHI',image,at,row[0],row[1],4,zlib.crc32(target),
                         payloads[patch],len(patch),row[6],zlib.crc32(patch))
        changed[name] = {'before':sha(raw),'after':sha(target),'mouthPixelsBefore':len(old_points),
                         'mouthPixelsAfter':len(replacement)}
    assert 'expression_delighted_v0_0_hold' in changed and len(changed) > 100
    root = bytearray(bank.root)
    identity = hashlib.sha256(b'companion.generated-soft-delighted-mouth.p210\0'+bytes(image)).digest()
    struct.pack_into('<I',root,24,zlib.crc32(image[bank.blob:bank.blob+bank.blob_n]))
    manifest_n = struct.unpack_from('<I',root,32)[0]
    struct.pack_into('<I',root,36,zlib.crc32(image[bank.blob:bank.blob+manifest_n]))
    root[44:76] = identity
    struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
    image[bank.geo['rootA']:bank.geo['rootA']+128] = root
    output.mkdir(parents=True)
    for p in base.glob('*.h'):
        shutil.copyfile(p,output/p.name)
    contract = output/'companion_wba_resource_contract.h'
    contract.write_text(contract.read_text().replace(bank.profile['resourceId'],identity.hex().upper()),encoding='utf8')
    (output/'ui-partition.bin').write_bytes(image)
    proof = {'result':'GENERATED_SHALLOW_SMILE_IMPORTED_INTO_RETAINED_DELIGHTED_FRAMES',
             'baseSha256':sha(bank.data),'sha256':sha(image),'generatedNativeArt':str(art),
             'generatedNativeSha256':sha(art.read_bytes()),'oldMouthBox':old_box,
             'generatedMouthBox':box,'changedStates':changed,'unchangedDifferentMouthStates':skipped,
             'newPayloadBytes':sum(len(p) for p in payloads),'newPayloadCount':len(payloads),
             'payloadRange':[free_start,free_start+sum(len(p) for p in payloads)],
             'cempByteIdentical':image[:bank.profile['cempBytes']] == bank.data[:bank.profile['cempBytes']],
             'onlyMouthPixelsChanged':True,'originalExpressivePeaksRetained':True,
             'staticOrDynamicBoundaryChanged':False,'newRuntimeRamBytes':0,'installed':False}
    profile = bank.profile
    profile.update(resourceId=identity.hex().upper(),uiPartitionSha256=sha(image).upper(),softSmile=proof)
    for name, info in changed.items():
        if name in profile.get('states', {}):
            profile['states'][name]['sha256'] = info['after'].upper()
    profile['sourceSha256'][Path(__file__).relative_to(Path(__file__).parents[1]).as_posix()] = sha(Path(__file__).read_bytes()).upper()
    (output/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (output/'soft-smile.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    check = Bank(output)
    changed_hashes = {fnv(n) for n in changed}
    for h,(at,row) in bank.entries.items():
        actual = check.frame(check.entries[h][1])
        if h in changed_hashes:
            assert actual != bank.frame(row)
        else:
            assert check.data[at:at+24] == bank.data[at:at+24] and actual == bank.frame(row)
    return {k:v for k,v in proof.items() if k != 'changedStates'} | {'changedStateCount':len(changed)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--art',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a = parser.parse_args()
    print(json.dumps(build(a.base.resolve(),a.art.resolve(),a.output.resolve()),ensure_ascii=False))
