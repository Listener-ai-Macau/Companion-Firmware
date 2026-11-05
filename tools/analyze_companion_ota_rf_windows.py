"""Close an exact OTA's RF window ledger without a fitted host/RF clock.

This is an offline analysis of an independently authenticated, byte-complete
image. It emits timing/count metadata only, never keys or packet plaintext.
RF and HCI partitions are alternative views, not additive measurements.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from companion_rf_clock import ReceiverClock


def require(condition, message):
    if not condition:
        raise ValueError(message)


def analyze(capture, ledger_path, proof_prefix=''):
    require(all(c.isalnum() or c in '-_' for c in proof_prefix), 'Invalid proof prefix')
    proof = json.loads((capture / (proof_prefix+'current-bond-independent-rf-proof.json')).read_text())
    meta = json.loads((capture / (proof_prefix+'rf-transport-metadata.json')).read_text())
    hci = json.loads(ledger_path.read_text())
    source_sha = hashlib.sha256((capture / 'packets-private.jsonl').read_bytes()).hexdigest()
    require(source_sha == proof['sourcePacketsSha256'] == meta['sourceSha256'],
            'RF source identity differs from authenticated proof')
    clock = ReceiverClock.read(capture / 'packets-private.jsonl')
    proof, meta = clock.normalize(proof), clock.normalize(meta)
    require(hci['packageSha256'] == proof['imageSha256']
            and hci['hciFileBytesIndependentlyMatched']
            and hci['durableWindowLedger']['complete'], 'HCI image/window proof incomplete')
    epochs = [e for e in proof['epochs'] if e['fullImageRfCoverageQualified']]
    require(len(epochs) == 1, 'Select an unambiguous byte-complete image epoch')
    epoch = epochs[0]
    require(epoch['reconstructedSha256'] == proof['imageSha256'], 'RF image SHA differs')
    aa = epoch['aa']
    chunks = sorted((c for c in meta['canonicalImageChunks'] if c['aa'] == aa),
                    key=lambda c: c['offset'])
    require(len(chunks) == proof['expectedCanonicalImageChunks'], 'Chunk count differs')
    cursor = 0
    for chunk in chunks:
        require(chunk['offset'] == cursor and chunk['bytes'] > 0,
                'Image has a duplicate, gap or overlapping chunk')
        cursor += chunk['bytes']
    require(cursor == proof['imageBytes'], 'Image byte coverage incomplete')
    # The image epoch is 2M only after its authenticated PHY instant. Restrict
    # analysis to a capture with that update before the first file DATA.
    require(any(c['opcode'] == '0x18' and c.get('c2p') == c.get('p2c') == 2
                and c['deviceUs'] < chunks[0]['firstUs']
                for c in epoch['authenticatedControls']), 'No preceding authenticated 2M update')
    require(not any(c['opcode'] == '0x18' and c['deviceUs'] >= chunks[0]['firstUs']
                    and c['deviceUs'] <= chunks[-1]['lastUs']
                    for c in epoch['authenticatedControls']), 'PHY changes inside image ROI')
    packets = {(p['direction'], p['us']): p for p in meta['micVerifiedPackets']
               if p['aa'] == aa}

    def packet_end(direction, timestamp):
        packet = packets[(direction, timestamp)]
        return timestamp + (11 + packet['bytes']) * 4  # LE2M, includes MIC in bytes

    statuses = sorted((s for s in meta['authenticatedStatus']
                       if s['aa'] == aa and s['requestFirstUs'] >= chunks[0]['firstUs']),
                      key=lambda s: s['requestFirstUs'])
    by_offset = {c['offset']: i for i, c in enumerate(chunks)}
    rows, cursor, used_statuses = [], 0, set()
    partition = collections.Counter()
    for window in hci['windows']:
        end_offset = window['endOffset']
        require(cursor < end_offset <= proof['imageBytes'], 'Invalid HCI window cursor')
        stop = by_offset[end_offset] if end_offset < proof['imageBytes'] else len(chunks)
        cs = chunks[by_offset[cursor]:stop]
        require(len(cs) == window['dataPackets'] and sum(c['bytes'] for c in cs) == window['bytes'],
                'HCI/RF window contents differ')
        first = cs[0]['firstUs']
        data_end = packet_end(1, cs[-1]['lastUs'])
        require(all(first <= c['firstUs'] <= c['lastUs'] <= cs[-1]['lastUs'] for c in cs),
                'Window DATA timestamp order differs from offset order')
        next_data = chunks[stop]['firstUs'] if stop < len(chunks) else float('inf')
        reads = [s for s in statuses if s['requestFirstUs'] >= data_end
                 and packet_end(0, s['responseLastUs']) < next_data]
        full = next((i for i, s in enumerate(reads) if s['accepted'] == end_offset
                     and s['expected'] == proof['imageBytes'] and s['error'] == 0), None)
        require(full is not None, 'Missing exact durable RF window completion; no inference allowed')
        reads = reads[:full + 1]
        last = packet_end(0, reads[-1]['responseLastUs'])
        parts = dict(dataSpanUs=data_end - first,
                     dataEndToFirstObservedReadUs=reads[0]['requestFirstUs'] - data_end,
                     observedReadRoundtripsUs=sum(packet_end(0, s['responseLastUs'])
                                                  - s['requestFirstUs'] for s in reads),
                     betweenObservedReadsUs=sum(b['requestFirstUs'] - packet_end(0, a['responseLastUs'])
                                                for a, b in zip(reads, reads[1:])))
        require(all(v >= 0 for v in parts.values()), 'Overlapping RF ledger categories')
        require(sum(parts.values()) == last - first, 'RF window ledger does not close')
        if rows:
            gap = first - rows[-1]['fullStatusEndUs']
            require(gap >= 0, 'Overlapping durable windows')
            partition['betweenWindowsUs'] += gap
        partition.update(parts)
        for s in reads:
            require(s['requestFirstUs'] not in used_statuses, 'Read counted in multiple windows')
            used_statuses.add(s['requestFirstUs'])
        rows.append(dict(startOffset=cursor, endOffset=end_offset, newBytes=window['bytes'],
                         chunks=len(cs), firstDataUs=first, lastDataEndUs=data_end,
                         fullStatusEndUs=last, observedReads=len(reads),
                         firstObservedReadAccepted=reads[0]['accepted'],
                         firstObservedReadBehindBytes=end_offset - reads[0]['accepted'], **parts))
        cursor = end_offset
    require(cursor == proof['imageBytes'], 'HCI windows do not cover whole image')
    wall = rows[-1]['fullStatusEndUs'] - rows[0]['firstDataUs']
    require(sum(partition.values()) == wall, 'Whole RF window ledger does not close')
    exact_host_end = hci['durableWindowLedger']['windows'][-1]['exactStatusTime']
    host_read_count = sum(s['readRequestTime'] is not None
                          and hci['windows'][0]['dataFirstTime'] <= s['readRequestTime']
                          and s['time'] <= exact_host_end
                          for s in hci['statusReceipts'])
    return dict(schema='companion.ota.rf_window_ledger.v1', accessAddress=aa, receiverClock=clock.summary,
                sourcePacketsSha256=source_sha, packageSha256=proof['imageSha256'],
                hciLedgerSha256=hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                imageBytes=proof['imageBytes'], imageChunks=len(chunks), windows=len(rows),
                qualification='BYTE_COMPLETE_RF_WINDOWS_CLOSED_CONTROL_COVERAGE_NOT_LOSSLESS',
                firstDataToFullDurableStatusSeconds=wall / 1e6,
                partitionSeconds={k.removesuffix('Us'): v / 1e6 for k, v in partition.items()},
                residualSeconds=(wall - sum(partition.values())) / 1e6,
                observedRfReads=len(used_statuses), hciReads=host_read_count,
                hciVsRfReadCountDifference=host_read_count - len(used_statuses),
                firstObservedReadBehindWindows=sum(r['firstObservedReadBehindBytes'] > 0 for r in rows),
                finalDataEndToFullStatusSeconds=sum(r['fullStatusEndUs'] - r['lastDataEndUs']
                                                    for r in rows) / 1e6,
                hciDataSpanSeconds=sum(w['dataSpanMs'] for w in hci['windows']) / 1000,
                hciFullWallSeconds=hci['hciFirstDataToFullStatusSeconds'], rows=rows,
                limits=[
                    'RF and HCI clocks are not fitted or subtracted; the two ledgers are alternative boundaries of the same transfer.',
                    'DATA spans include inter-packet gaps, scheduling and any observed repeats; they are not pure airtime or CPU cost.',
                    'A gap between observed reads can contain an unobserved read. Missing control coverage is not manufactured.',
                    'HCI write timestamps precede physical transmission; some HCI status-read wait includes queued DATA still being transmitted.',
                    'Every exact durable window completion is observed, but that does not imply every ACK/control PDU was captured.',
                    'Status is intentionally published only when the device queue is empty. An older accepted value does not measure individual NOR program completion or prove Flash is the bottleneck.',
                    'RF timestamps use receiver PPI END minus airtime, with uncalibrated pipeline uncertainty.'
                ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--hci-ledger', type=Path, required=True)
    parser.add_argument('--proof-prefix', default='')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.capture, args.hci_ledger, args.proof_prefix)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'limits')}))
