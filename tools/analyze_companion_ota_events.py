"""Analyze observed OTA events using CONNECT, authenticated instants and CSA#2.

All observed ROI channels must match the reconstructed event schedule. This
qualifies observed event grouping, not lossless capture of every radio packet.
Empty ACKs have independent CRC checks but no encryption MIC. No key or packet
plaintext is exported. This tool never accesses live hardware.
"""
import argparse
import bisect
import collections
import hashlib
import json
import statistics
from pathlib import Path
from analyze_wba_air_nvm import wire_crc
from analyze_companion_ota_rf_windows import require
from companion_rf_clock import ReceiverClock

SPEC = 'https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html'
SAMPLE = 'https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/sample-data.html'


def channel2(event, channel_map, access_address):
    identifier = (access_address >> 16) ^ (access_address & 65535)
    value = (event & 65535) ^ identifier
    for _ in range(3):
        value = (int(f'{value & 255:08b}'[::-1], 2)
                 | (int(f'{value >> 8:08b}'[::-1], 2) << 8))
        value = (17 * value + identifier) & 65535
    value ^= identifier
    unmapped = value % 37
    used = [i for i in range(37) if (channel_map >> i) & 1]
    require(len(used) >= 2, 'Invalid channel map')
    return unmapped if unmapped in used else used[(len(used) * value) >> 16]


def summarize(rows):
    if not rows:
        return dict(events=0)
    return dict(events=len(rows), medianObservedSpanUs=statistics.median(r['observedSpanUs'] for r in rows),
                medianCentralPackets=statistics.median(r['centralPackets'] for r in rows),
                lastCentralMd1=sum(r['lastCentralMd'] for r in rows),
                lastCentralMd1WithObservedEmptyAck=sum(r['lastCentralMd'] and r['lastCentralAckObserved'] for r in rows),
                lastImageFragmentMd1WithObservedEmptyAck=sum(r['lastCentralIsImageFragment'] and r['lastCentralMd']
                                                             and r['lastCentralAckObserved'] for r in rows),
                completedImageBytes=sum(r['completedImageBytes'] for r in rows),
                medianUniqueCentralPlaintextLlBytes=statistics.median(r['uniqueCentralLlBytes'] for r in rows))


def analyze(capture, proof_prefix=''):
    # The SIG's published all-37-channel example is independent of this capture.
    require([channel2(i, (1 << 37) - 1, 0x8e89bed6) for i in range(4)] == [25, 20, 6, 21],
            'CSA#2 implementation differs from SIG sample')
    require(all(c.isalnum() or c in '-_' for c in proof_prefix), 'Invalid proof prefix')
    proof = json.loads((capture / (proof_prefix+'current-bond-independent-rf-proof.json')).read_text())
    meta = json.loads((capture / (proof_prefix+'rf-transport-metadata.json')).read_text())
    source = capture / 'packets-private.jsonl'
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    require(sha == proof['sourcePacketsSha256'] == meta['sourceSha256'], 'RF proof identity differs')
    clock = ReceiverClock.read(source)
    proof, meta = clock.normalize(proof), clock.normalize(meta)
    epochs = [e for e in proof['epochs'] if e['fullImageRfCoverageQualified']]
    require(len(epochs) == 1, 'Image epoch ambiguous')
    epoch = epochs[0]
    require(epoch['reconstructedSha256'] == proof['imageSha256'], 'RF image identity differs')
    aa = epoch['aa']
    chunks = sorted((c for c in meta['canonicalImageChunks'] if c['aa'] == aa), key=lambda c: c['offset'])
    start, end = chunks[0]['firstUs'], chunks[-1]['lastUs']
    mic = {p['us']: p for p in meta['micVerifiedPackets'] if p['aa'] == aa}
    unique_central = sorted((p for p in mic.values() if p['direction'] == 1 and p['llid'] in (1, 2)
                             and not p['duplicateCounter']), key=lambda p: p['us'])
    central_times = [p['us'] for p in unique_central]
    file_keys, completions = set(), collections.Counter()
    for chunk in chunks:
        fragments = unique_central[bisect.bisect_left(central_times, chunk['firstUs']):
                                   bisect.bisect_right(central_times, chunk['lastUs'])]
        require([p['bytes'] - 4 for p in fragments] == chunk['llFragments'],
                'Cannot associate every image fragment with an authenticated counter')
        file_keys.update((p['session'], p['counter']) for p in fragments)
        completions[chunk['lastUs']] += chunk['bytes']
    connects, frames, rejected = [], [], 0
    for row in clock.rows:
        raw = bytes.fromhex(row['pdu'])
        if len(raw) != 2 + raw[1] or not row['crcValid']:
            continue
        if row['aa'] == '8e89bed6' and len(raw) == 36 and raw[0] & 15 == 5:
            if f'{int.from_bytes(raw[14:18], "little"):08x}' == aa and wire_crc(raw, 0x555555) == row['crc']:
                connects.append((row, raw))
        if row['aa'] == aa and row['deviceTimestampUs'] <= end:
            frames.append((row, raw))
    require(len(connects) == 1, 'CONNECT must be unique and CRC verified')
    connect, raw_connect = connects[0]
    require(raw_connect[0] & 32, 'Capture does not advertise CSA#2')
    require(bytes.fromhex(proof['target'].replace(':', ''))[::-1] == raw_connect[8:14],
            'CONNECT target differs')
    seed = int.from_bytes(raw_connect[18:21], 'big')
    valid = []
    for row, raw in frames:
        if wire_crc(raw, seed) != row['crc']:
            rejected += 1
            continue
        if row['deviceTimestampUs'] <= connect['deviceTimestampUs']:
            continue
        valid.append(dict(us=row['deviceTimestampUs'], endUs=row['deviceTimestampUs'] + (11 + raw[1]) * 4,
                          channel=row['channel'], hint=row['direction'], bytes=raw[1],
                          llid=raw[0] & 3, md=bool(raw[0] & 16), sn=(raw[0] >> 3) & 1,
                          nesn=(raw[0] >> 2) & 1, mic=mic.get(row['deviceTimestampUs'])))
    valid.sort(key=lambda r: r['us'])
    initial_interval = int.from_bytes(raw_connect[24:26], 'little') * 1250
    # CONNECT is LE1M. Its first transmit window starts after T_IFS-like
    # transmitWindowDelay=1.25ms plus WinOffset, not after the first seen PDU.
    earliest = (connect['deviceTimestampUs'] + (10 + raw_connect[1]) * 8 + 1250
                + int.from_bytes(raw_connect[22:24], 'little') * 1250)
    latest = earliest + raw_connect[21] * 1250
    first = next(r for r in valid if r['hint'] == 1)
    possible = [(n, first['us'] - n * initial_interval) for n in range(8)
                if earliest <= first['us'] - n * initial_interval <= latest]
    require(len(possible) == 1, 'Cannot uniquely infer initial event index in transmit window')
    first_index, initial_anchor = possible[0]
    schedule = [dict(event=0, anchorUs=initial_anchor, intervalUs=initial_interval)]
    updates = sorted((c for c in epoch['authenticatedControls'] if c['opcode'] == '0x0'),
                     key=lambda c: c['instant'])
    for update in updates:
        previous = schedule[-1]
        require(previous['event'] < update['instant'] < 65536, 'Unsupported counter wrap/update order')
        anchor = (previous['anchorUs'] + (update['instant'] - previous['event']) * previous['intervalUs']
                  + update['windowOffsetUnits'] * 1250)
        schedule.append(dict(event=update['instant'], anchorUs=anchor, intervalUs=update['intervalUnits'] * 1250))
    map_schedule = [(0, int.from_bytes(raw_connect[30:35], 'little'))]
    map_schedule += [(c['instant'], int.from_bytes(bytes.fromhex(c['channelMap']), 'little'))
                     for c in epoch['authenticatedControls'] if c['opcode'] == '0x1']
    map_schedule.sort()
    anchors = [s['anchorUs'] for s in schedule]
    map_events = [e for e, _ in map_schedule]
    groups = collections.defaultdict(list)
    mismatches = []
    validated = 0
    for row in valid:
        if not start <= row['us'] <= end:
            continue
        # 100us tolerance accommodates this short capture's observed drift.
        # Every resulting event assignment is independently channel checked.
        s = schedule[max(0, bisect.bisect_right(anchors, row['us'] + 100) - 1)]
        event = s['event'] + (row['us'] - s['anchorUs'] + 100) // s['intervalUs']
        channel_map = map_schedule[bisect.bisect_right(map_events, event) - 1][1]
        predicted = channel2(event, channel_map, int(aa, 16))
        if predicted != row['channel']:
            mismatches.append(dict(us=row['us'], event=event, observed=row['channel'], predicted=predicted))
        else:
            validated += 1
        groups[event].append(row)
    require(not mismatches, f'Event/channel model mismatch: {len(mismatches)} observed PDUs')
    rows = []
    event_keys = sorted(groups)
    for i, event in enumerate(event_keys):
        packets = groups[event]
        central = [r for r in packets if r['mic'] and r['mic']['direction'] == 1 and r['llid'] in (1, 2)]
        if not central:
            continue
        last = central[-1]
        replies = [r for r in packets if r['us'] > last['us']]
        ack = bool(replies and replies[0]['bytes'] == 0
                   and replies[0]['nesn'] == 1 - last['sn']
                   and abs(replies[0]['us'] - last['endUs'] - 150) <= 20)
        next_time = groups[event_keys[i + 1]][0]['us'] if i + 1 < len(event_keys) else None
        rows.append(dict(event=event, firstObservedUs=packets[0]['us'],
                         observedSpanUs=packets[-1]['endUs'] - packets[0]['us'],
                         centralPackets=len(central), lastCentralMd=last['md'],
                         lastCentralAckObserved=ack,
                         lastCentralIsImageFragment=(last['mic']['session'], last['mic']['counter']) in file_keys,
                         imagePackets=sum((r['mic']['session'], r['mic']['counter']) in file_keys for r in central),
                         completedImageBytes=sum(completions.get(r['us'], 0) for r in central
                                                 if not r['mic']['duplicateCounter']),
                         gapToNextObservedEventUs=next_time - packets[-1]['endUs'] if next_time else None,
                         uniqueCentralLlBytes=sum(r['bytes'] - 4 for r in central
                                                  if not r['mic']['duplicateCounter'])))
    short = [r for r in rows if r['observedSpanUs'] < 2500]
    long = [r for r in rows if r['observedSpanUs'] > 9000]
    file_rows = [r for r in rows if r['imagePackets']]
    short_file = [r for r in file_rows if r['observedSpanUs'] < 2500]
    long_file = [r for r in file_rows if r['observedSpanUs'] > 9000]
    require(sum(r['completedImageBytes'] for r in rows) == proof['imageBytes'], 'Event image byte coverage differs')
    short_pending_acked = [r for r in short if r['lastCentralMd'] and r['lastCentralAckObserved']
                           and r['gapToNextObservedEventUs'] is not None]
    quarters = []
    for i in range(4):
        lo, hi = start + (end - start) * i / 4, start + (end - start) * (i + 1) / 4
        subset = [r for r in rows if lo <= r['firstObservedUs'] < hi]
        quarters.append(dict(quarter=i + 1, **summarize(subset),
                             shortEvents=sum(r['observedSpanUs'] < 2500 for r in subset),
                             longEvents=sum(r['observedSpanUs'] > 9000 for r in subset)))
    return dict(schema='companion.ota.observed_events.v1', sourcePacketsSha256=sha, receiverClock=clock.summary,
                packageSha256=proof['imageSha256'], accessAddress=aa,
                qualification='OBSERVED_EVENTS_CHANNEL_VALIDATED_NOT_LOSSLESS_OR_UNIQUE_ROOT_CAUSE',
                initialAnchorUs=initial_anchor, firstObservedCentralEvent=first_index,
                intervalSchedule=schedule, rejectedCrcPackets=rejected,
                observedRoiPacketsChannelMatched=validated, channelMismatches=0,
                observedRoiEvents=len(groups), eventsWithCentralData=summarize(rows),
                shortEventsUnder2500us=summarize(short), longEventsOver9000us=summarize(long),
                eventsWithImageFragments=summarize(file_rows),
                shortImageEventsUnder2500us=summarize(short_file),
                longImageEventsOver9000us=summarize(long_file),
                uniqueImageLlFragments=len(file_keys),
                shortMd1AckedGapMedianUs=statistics.median(r['gapToNextObservedEventUs']
                                                         for r in short_pending_acked) if short_pending_acked else None,
                timeQuarters=quarters, rows=rows,
                references=[SPEC, SAMPLE],
                limits=[
                    'Only observed events are grouped. An absent PDU/event remains unobserved, not a proven empty event.',
                    'The reported first observed central event is inferred uniquely within the CRC-verified CONNECT transmit window; event 0 need not be captured.',
                    'CSA#2 and authenticated map/connection update instants verify every observed ROI channel; this does not measure antenna timestamp calibration.',
                    'An empty ACK has independent CRC/sequence/timing evidence but no MIC. Observing its transmission does not prove the central received it.',
                    'SN/NESN/MD header fields are CRC checked; BLE excludes these changing bits from MIC authentication.',
                    'MD=1 advertises more data; the central is permitted, not required, to continue. Early ending alone does not uniquely identify Windows scheduling, radio coexistence or peripheral receive behavior.',
                    'Central LL byte counts include protocol headers and exclude repeated authenticated counters; they are not application throughput.',
                    'Short/long thresholds describe observed spans, not configured controller event-length settings.',
                    'Raw receiver uint32 timestamps are unwrapped in recorded order for this bounded capture; backwards order or ambiguous periods reject analysis. Every resulting observed channel is checked.'
                ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--proof-prefix', default='')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.capture, args.proof_prefix)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'limits', 'references', 'timeQuarters')}))
