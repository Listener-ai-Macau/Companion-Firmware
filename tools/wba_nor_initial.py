"""Offline preparation for legacy32 -> compact24-nor wired migration.

No serial, probe, erase, programming, reset, cloud, or private signing key.
Supplied readbacks are evidence of bytes, never proof of fresh acquisition or
permission to operate a board. The installer must repeat these exact checks on
live reads under its single lease, before its first mutation. Pairing payloads
stay opaque and in memory; reports contain only digests, never key bytes.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from provision_wba_v11 import validate_identity
from wba_air_nvm import bank as snvma_bank
from wba_flash_geometry import for_mcu, from_receipt

TRUST_SHA256 = '3cf111a3787d31d4cc597dbff5dd6f200ccebc350a53494d8b5a7053ec920085'
HOST_BYTES, IDENTITY_BYTES = 2032, 48
BOND_BYTES, BOND_HEADER, SYSTEM_BYTES = 4096, 40, 131072
COMMITTED = 0x00000002314D424E
LEGACY = for_mcu('STM32WBA55CEU6', 'legacy32')
TARGET = for_mcu('STM32WBA55CEU6', 'compact24-nor')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def exact(root: Path, name: str, size: int | None = None) -> bytes:
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), 'Input escapes its supplied directory')
    data = path.read_bytes()
    require(size is None or len(data) == size, 'Incomplete input: ' + name)
    return data


def identity_valid(data: bytes) -> bool:
    # The pinned application owns this representation. No decoding of the
    # proprietary host database, no inferred offsets for peer/root keys.
    return (len(data) == IDENTITY_BYTES and data[:4] == b'CBI1' and
            data[41] & 0xC0 == 0xC0)


def inspect_internal_nvm(internal: bytes) -> tuple[dict, bytes]:
    require(len(internal) == LEGACY.flash_bytes, 'Exact CE internal image required')
    nvm = internal[LEGACY.nvm_offset:]
    rows, valid = [], []
    for index in range(2):
        try:
            row, buffers = snvma_bank(nvm, index)
        except ValueError:
            row, buffers = dict(index=index, valid=False, malformed=True), None
        rows.append(row)
        if buffers is not None:
            valid.append((row, buffers))
    require(bool(valid), 'No CRC-qualified internal SNVMA bank')
    selected = valid[0]
    for candidate in valid[1:]:
        a, b = selected[0]['counter'], candidate[0]['counter']
        # Match pinned SDK GetNewestBank, including its asymmetric wrap rule.
        # Do not silently substitute a preferred counter algorithm.
        if a == b:
            require(selected[1] == candidate[1], 'Conflicting equal-counter SNVMA banks')
        if a < b and b - a != 0xFF:
            selected = candidate
    row, buffers = selected
    require([len(x) for x in buffers] == [HOST_BYTES, IDENTITY_BYTES, 8, 0],
            'Migration bridge buffer registration or COMMITTED marker is absent')
    require(int.from_bytes(buffers[2], 'little') == COMMITTED,
            'Internal migration marker is not COMMITTED')
    require(identity_valid(buffers[1]), 'Invalid internal device identity')
    return dict(selectedBank=row['index'], banks=rows, nvmSha256=sha(nvm),
                marker='COMMITTED', identitySha256=sha(buffers[1]),
                historicalHostSha256=sha(buffers[0])), buffers[1]


def inspect_external_bonds(system: bytes, uid: bytes) -> tuple[dict, bytes]:
    require(len(system) == SYSTEM_BYTES and len(uid) == 12, 'Incomplete system/UID readback')
    rows, valid = [], []
    for index, at in enumerate((0xC000, 0xD000)):
        page = system[at:at + BOND_BYTES]
        row = dict(index=index, relativeOffset=at, sha256=sha(page), valid=False,
                   blank=page == b'\xff' * BOND_BYTES)
        h = page[:BOND_HEADER]
        magic, schema, generation, count, crc = struct.unpack_from('<5I', h)
        header_ok = (magic == 0x31444E42 and
                     struct.unpack_from('<I', h, 32)[0] == zlib.crc32(h[4:32]))
        if header_ok:
            require(schema == 1 and count == HOST_BYTES + IDENTITY_BYTES and h[20:32] == uid,
                    'Recognizable external bond page has foreign UID/schema/size')
            payload = page[BOND_HEADER:BOND_HEADER + count]
            if zlib.crc32(payload) == crc and identity_valid(payload[HOST_BYTES:]):
                row.update(valid=True, generation=generation, payloadSha256=sha(payload))
                valid.append((row, h, payload))
        rows.append(row)
    require(bool(valid), 'No complete UID/CRC-qualified external bond copy')
    selected = valid[0]
    for candidate in valid[1:]:
        delta = (candidate[0]['generation'] - selected[0]['generation']) & 0xFFFFFFFF
        require(delta != 0x80000000, 'Ambiguous external bond generations')
        if delta == 0:
            require(candidate[1:] == selected[1:], 'Conflicting equal-generation external copies')
        elif delta < 0x80000000:
            selected = candidate
    row, _, payload = selected
    return dict(selectedBank=row['index'], generation=row['generation'], banks=rows,
                currentPayloadSha256=sha(payload), currentHostSha256=sha(payload[:HOST_BYTES]),
                identitySha256=sha(payload[HOST_BYTES:])), payload[HOST_BYTES:]


def inspect_provisioning_seal(system: bytes, uid: bytes, *, migrated: bool = False) -> dict:
    require(len(system) == SYSTEM_BYTES and len(uid) == 12, 'Incomplete provisioning seal input')
    page = system[0xE000:0xF000]
    h = page[:48]
    magic, version, count, origin = struct.unpack_from('<4I', h)
    require((magic, version, count) == (0x31535042, 1, HOST_BYTES + IDENTITY_BYTES) and
            origin in (1, 2) and h[16:28] == uid and
            struct.unpack_from('<I', h, 28)[0] == zlib.crc32(h[4:28]) and
            struct.unpack_from('<I', h, 32)[0] == 0xFFFFFFFC and h[36:] == b'\xff' * 12 and
            page[48:] == b'\xff' * (4096 - 48), 'No exact UID-bound COMPLETE provisioning seal')
    require(not migrated or origin == 2, 'Existing-device migration seal origin differs')
    return dict(relativeOffset=0xE000, origin='MIGRATED' if origin == 2 else 'NEW',
                state='COMPLETE', pageSha256=sha(page), cryptographicAuthentication=False)


def inspect_pairing(internal: bytes, system: bytes, uid: bytes) -> dict:
    require(len(uid) == 12 and uid not in (bytes(12), b'\xff' * 12), 'Invalid explicit target UID')
    seal = inspect_provisioning_seal(system, uid, migrated=True)
    old, identity = inspect_internal_nvm(internal)
    current, external_identity = inspect_external_bonds(system, uid)
    require(identity == external_identity, 'External identity differs from committed internal authority')
    # After COMMITTED, the bridge writes current host changes externally only.
    # Requiring equality with historical internal host bytes would reject a
    # legitimate later pairing. Identity equality + durable authority + current
    # selected external image are the relevant transition checks.
    return dict(result='PAIRING_BYTES_QUALIFIED_FOR_LIVE_MIGRATION_PREFLIGHT',
                internal=old, external=current, provisioningSeal=seal, uid=uid.hex(),
                historicalHostEqualityRequired=False, keyMaterialExported=False,
                cryptographicAtRestSecurityQualified=False, liveAcquisitionProven=False)


def verify_cup(file: bytes, public_xy: bytes, geometry, expected_trust_sha256: str = TRUST_SHA256) -> dict:
    require(len(file) >= 184 and len(public_xy) == 64, 'Incomplete CUP/public key')
    require(sha(public_xy) == expected_trust_sha256, 'Unexpected product trust anchor')
    prefix = file[:76]
    values = struct.unpack('<4sBBHIIIIIII32sBBHI', prefix)
    magic, component, target, fmt, family, board, version, low, high, count, crc, digest, alg, r0, r1, key_id = values
    body = file[144:]
    require((magic, component, target, fmt, family, board, low, high, alg, r0, r1) ==
            (b'WUM1', 1, 1, 3, 0x41425743, geometry.board_target, 0, 0, 1, 0, 0),
            'Signed CUP target, format, or bounds differ')
    require(key_id != 0, 'Unconfigured signing key id')
    require(count == len(body) and crc == zlib.crc32(body) and digest == hashlib.sha256(body).digest(),
            'Signed CUP payload hash/CRC/length mismatch')
    require(struct.unpack_from('<I', file, 140)[0] == zlib.crc32(file[:140]), 'CUP header CRC mismatch')
    key = ec.EllipticCurvePublicNumbers(int.from_bytes(public_xy[:32], 'big'),
                                      int.from_bytes(public_xy[32:], 'big'), ec.SECP256R1()).public_key()
    key.verify(encode_dss_signature(int.from_bytes(file[76:108], 'big'),
                                  int.from_bytes(file[108:140], 'big')), prefix, ec.ECDSA(hashes.SHA256()))
    tag, schema, descriptor_bytes, fw, ui, app_n, ui_n, static, address = struct.unpack_from('<4sHH6I', body)
    require((tag, schema, descriptor_bytes, fw, address) == (b'CUP3', 3, 32, version, geometry.app_address),
            'CUP descriptor/version/address mismatch')
    require(8 <= app_n <= geometry.app_bytes and ui_n == static and static % 4096 == 0 and
            static >= 905216 and len(body) == 32 + app_n + ui_n, 'Invalid CUP component extents')
    return dict(firmware=fw, ui=ui, appBytes=app_n, uiBytes=ui_n, staticBytes=static,
                appAddress=address, keyId=key_id, packageSha256=sha(file))


@dataclass(repr=False)
class TargetImages:
    report: dict
    internal: bytes
    ui: bytes
    current_sector: bytes
    cup: bytes


def verify_build_inputs(app: dict, boot: dict, source: Path, repo: Path, commit: str,
                        resource_directory: Path, generated_directory: Path | None = None) -> dict:
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'Exact source commit required')
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', commit], cwd=repo)
    blobs = {}
    for entry in tree.split(b'\0'):
        if entry:
            header, name = entry.split(b'\t', 1)
            blobs[name.decode()] = header.split()[2].decode()
    counts = dict(app=0, boot=0)
    for role, mapping in (('app', app['source_sha256']), ('boot', boot['sources'])):
        for name, wanted in mapping.items():
            name = name.replace('\\', '/')
            if name.startswith('_external-build-output/'):
                leaf = name.split('/', 1)[1]
                resource_inputs = {'companion_wba_resource_contract.h', 'profile.json', 'ui-partition.bin'}
                generated_inputs = {'power-profile.json', 'wba_board_power_profile.h', 'wba_update_trust_anchor.h'}
                require(leaf in resource_inputs | generated_inputs, 'Unexpected external build input')
                # Same recorded namespace as the actual producer: generated
                # power/trust inputs stay beside App output; UI source files
                # may stay beside the explicitly selected immutable resource bank.
                if generated_directory is not None and (generated_directory / leaf).is_file():
                    data = exact(generated_directory, leaf)
                else:
                    require(leaf in resource_inputs, 'Missing generated App input: ' + leaf)
                    data = exact(resource_directory, leaf)
            elif Path(name).is_absolute():
                # Boot SDK/generated inputs remain at the exact recorded path.
                data = Path(name).read_bytes()
            else:
                data = exact(source, name)
                git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                require(blobs.get(name) == git_blob, 'Build input differs from immutable source: ' + name)
                counts[role] += 1
            require(sha(data) == wanted, 'Build input digest mismatch: ' + name)
    return dict(commit=commit, boundInternalInputs=counts, allRecordedInputDigestsVerified=True)


def inspect_target(package: Path, app_directory: Path, boot_directory: Path,
                   public_xy: bytes, source: Path, repo: Path, commit: str,
                   resource_directory: Path) -> TargetImages:
    manifest = load(package / 'ota_manifest.json')
    require(manifest.get('schema') == 'companion.wba.simple-ota.v3' and manifest.get('dev_only') is True,
            'This migration path is restricted to explicit DEV simple CUP')
    require(from_receipt(manifest) == TARGET, 'Package is not the canonical compact24-nor target')
    file = exact(package, 'companion-update.cup')
    report = verify_cup(file, public_xy, TARGET)
    require(manifest['sha256'] == sha(file) and manifest['bytes'] == len(file), 'Package manifest differs')
    require(manifest['board_target'] == TARGET.board_target and manifest['hardware_revision'] == TARGET.hardware_revision,
            'Manifest layout identity differs')
    require(manifest['public_key_sha256'] == TRUST_SHA256 and manifest['key_id'] == report['keyId'], 'Manifest trust differs')
    for mk, rk in (('firmware_version','firmware'), ('resource_version','ui'), ('firmware_bytes','appBytes'),
                   ('resource_bytes','uiBytes'), ('static_bytes','staticBytes'), ('app_address','appAddress')):
        require(manifest[mk] == report[rk], 'Manifest descriptor mismatch: ' + mk)
    app, boot = load(app_directory / 'result.json'), load(boot_directory / 'result.json')
    require(from_receipt(app) == TARGET and from_receipt(boot) == TARGET, 'App/Boot layouts differ')
    require(app.get('result') == 'COMPILED_BUILD_ONLY' and not app.get('error') and boot.get('result') == 'PASS',
            'Successful exact App/Boot builds required')
    persistence = app.get('ble_bond_persistence', {})
    require(persistence.get('backend') == 'EXTERNAL_NOR_ONLY', 'NOR-only App required')
    seal = persistence.get('provisioning_seal', {})
    require(seal.get('relative_offset') == 0xE000 and seal.get('bytes') == 4096 and
            seal.get('header_bytes') == 48 and seal.get('never_runtime_erased') is True,
            'Exact permanent provisioning seal contract required')
    # The explicit DEV first-board profile can also install over a migrated
    # COMPLETE seal; make_plan requires the current migrated seal before ANY
    # mutation. A completed seal never grants another identity generation.
    require(boot.get('system_pair_protocol') == app.get('ota_protocol') == 'companion_simple_ota_v3' and
            boot.get('requires_initial_signed_package_header') is True, 'Boot protocol differs')
    require(app['firmware_version'] == boot['firmware_version'] == report['firmware'] and
            boot['installed_image_size'] == report['appBytes'], 'App/Boot version or initial size differs')
    require(boot['capacity_bytes'] == TARGET.boot_bytes and all(
            b.get('sram_inspection', {}).get('writableSectionAddressesValid') is True for b in (app, boot)),
            'Invalid Boot capacity or physical SRAM section coverage')
    require(app['update_trust_anchor']['enabled'] is True and
            app['update_trust_anchor']['public_key_sha256'] == boot['public_key_sha256'] == TRUST_SHA256 and
            app['update_trust_anchor']['key_id'] == boot['key_id'] == report['keyId'], 'Build trust differs')
    image, ui = file[176:176 + report['appBytes']], file[176 + report['appBytes']:]
    resident = exact(boot_directory, 'companion_wba55_v11_boot.bin')
    require(image == exact(app_directory, 'companion-v11-board-bringup.bin') and
            sha(image) == app['bin_sha256'] and sha(resident) == boot['bin_sha256'] and
            8 <= len(resident) <= TARGET.boot_bytes, 'App/Boot binary differs from build or signed file')
    profile, nor = app['ui_resource_profile'], app['flash_geometry']
    require(nor == boot['flash_geometry'] and nor['staticBytes'] == nor['dynamicBase'] == len(ui) and
            nor['systemBytes'] == SYSTEM_BYTES and nor['recordingCatalog'] == len(ui) + 0x10000 and
            profile['generation'] == report['ui'] and profile['uiPartitionBytes'] == len(ui) and
            profile['uiPartitionSha256'].lower() == sha(ui), 'App/Boot/UI external geometry mismatch')
    internal = (resident.ljust(TARGET.boot_bytes, b'\xff') + image).ljust(TARGET.flash_bytes, b'\xff')
    for offset, size in ((0, len(resident)), (TARGET.boot_bytes, len(image))):
        sp, reset = struct.unpack_from('<II', internal, offset)
        require(TARGET.valid_stack_pointer(sp) and reset & 1 and
                TARGET.flash_base + offset <= (reset & ~1) < TARGET.flash_base + offset + size,
                'Invalid Boot/App vector')
    binding = verify_build_inputs(app, boot, source, repo, commit, resource_directory, app_directory)
    current = bytearray(192)
    current[:5] = b'SCU3\x03'
    struct.pack_into('<H', current, 6, 192)
    current[12:188] = file[:176]
    struct.pack_into('<I', current, 188, zlib.crc32(current[:188]))
    report.update(layout=TARGET.receipt(), appSha256=sha(image), bootSha256=sha(resident), uiSha256=sha(ui),
                  internalTargetSha256=sha(internal), sourceBinding=binding, installed=False)
    return TargetImages(report, internal, ui, bytes(current).ljust(4096, b'\xff'), file)


def inspect_current(internal: bytes, ui: bytes, system: bytes, public_xy: bytes) -> dict:
    matches = []
    for offset in (0x2000, 0x3000):
        page = system[offset:offset + 4096]
        if page[:5] != b'SCU3\x03' or struct.unpack_from('<H', page, 6)[0] != 192:
            continue
        if struct.unpack_from('<I', page, 188)[0] != zlib.crc32(page[:188]):
            continue
        header = page[12:188]
        try:
            app_n, ui_n, static, address = struct.unpack_from('<4I', header, 160)
            require(address == LEGACY.app_address and ui_n == static == len(ui) and 8 <= app_n <= LEGACY.app_bytes,
                    'Old signed descriptor differs')
            old = verify_cup(header + internal[LEGACY.boot_bytes:LEGACY.boot_bytes + app_n] + ui,
                             public_xy, LEGACY)
        except (ValueError, struct.error, InvalidSignature):
            continue
        matches.append((offset, old))
    require(bool(matches), 'Live old App/UI do not match an existing signed SCU3 current receipt')
    require(all(row[1] == matches[0][1] for row in matches), 'Conflicting matching signed current receipts')
    require(system[0x5000:0x6000] == b'\xff' * 4096, 'Pending OTA metadata is not erased')
    return dict(currentOffsets=[row[0] for row in matches], **matches[0][1])


def make_plan(images: TargetImages, internal: bytes, ui: bytes, system: bytes,
              uid: bytes, public_xy: bytes, factory_result: dict, loader: bytes) -> dict:
    require(len(internal) == TARGET.flash_bytes and len(system) == SYSTEM_BYTES, 'Incomplete before images')
    require(ui == images.ui, 'External resource relocation/growth is outside this internal-only migration')
    pairing = inspect_pairing(internal, system, uid)
    current = inspect_current(internal, ui, system, public_xy)
    require(images.report['firmware'] > current['firmware'], 'New firmware must increase from actual signed current')
    require(images.report['ui'] == current['ui'], 'Internal-only migration must preserve the current UI generation')
    static = len(ui)
    from wba_factory_writer import validate_writer
    validate_writer(factory_result, loader, static)
    page = TARGET.flash_page_bytes
    changed = [at for at in range(0, len(internal), page)
               if internal[at:at + page] != images.internal[at:at + page]]
    app_pages = [at for at in changed if TARGET.boot_bytes <= at < LEGACY.nvm_offset]
    nvm_pages = [at for at in changed if at >= LEGACY.nvm_offset]
    boot_pages = [at for at in changed if at < TARGET.boot_bytes]
    metadata = [static + at for at in (0x2000, 0x3000)
                if system[at:at + 4096] != images.current_sector]
    return dict(schema='companion.wba.nor-initial-plan.v1', result='OFFLINE_BYTES_QUALIFIED_NOT_INSTALL_AUTHORITY',
                uid=uid.hex(), previous=current, target=images.report, pairing=pairing,
                beforeInternalSha256=sha(internal), beforeSystemSha256=sha(system), beforeUiSha256=sha(ui),
                loaderSha256=sha(loader), protectedBondRange=[static + 0xC000, static + 0xF000],
                internalPageBytes=page, orderedOperations=[
                    dict(operation='WRITE_READBACK_APP_PAGES', pageOffsets=app_pages),
                    dict(operation='RECLAIM_INTERNAL_NVM_AFTER_RECHECKING_EXTERNAL_BONDS', pageOffsets=nvm_pages),
                    dict(operation='VERIFY_COMPLETE_NEW_APP_AND_UNCHANGED_UI_AND_EXTERNAL_BONDS'),
                    dict(operation='PUBLISH_READBACK_SIGNED_CURRENT', sectorOffsets=metadata),
                    dict(operation='WRITE_READBACK_BOOT_LAST', pageOffsets=boot_pages),
                    dict(operation='VERIFY_FULL_INTERNAL_SYSTEM_AND_PROTECTED_BONDS_BEFORE_RESET')],
                allowedNorSectorOffsets=metadata, norMassErase=False, uiWrites=False,
                plannedSettingsAndRecordingPreservation='Exact bytes outside the two signed current sectors',
                plannedInternalNvmReclaim=True, internalNvmReclaimed=False,
                actualPreservationVerified=False,
                requiresRetainedPrivateOriginalReadbacks=True,
                interruptedMigration='wired resume from retained original reads plus exact new signed package; no claim old Boot can start a partially relocated App',
                requiresLiveSameLeaseRevalidation=True, acquisitionProven=False,
                hardwareOperations=0, installed=False, physicalQualified=False)


def make_resume_plan(images: TargetImages, original_internal: bytes, original_ui: bytes,
                     original_system: bytes, current_internal: bytes, current_system: bytes,
                     uid: bytes, public_xy: bytes, factory_result: dict, loader: bytes) -> dict:
    """Qualify retained authority and interrupted bytes; never open recovery.

    A changed page must be the original page, exact target, or a partial
    program of the exact target after erasing that same page. Unrelated pages
    and every external byte outside the two SCU3 pages must remain exact.
    This permits preparing a bounded continuation, not inferring authorization
    to attach SWD when the normal application no longer replies.
    """
    plan = make_plan(images, original_internal, original_ui, original_system,
                     uid, public_xy, factory_result, loader)
    require(len(current_internal) == TARGET.flash_bytes and len(current_system) == SYSTEM_BYTES,
            'Complete interrupted internal/system reads required')
    remaining, partial = [], []
    for at in range(0, TARGET.flash_bytes, TARGET.flash_page_bytes):
        end = at + TARGET.flash_page_bytes
        before, after, live = original_internal[at:end], images.internal[at:end], current_internal[at:end]
        if before == after:
            require(live == before, 'An unplanned internal page changed')
        elif live != after:
            require(live == before or all((actual & wanted) == wanted for actual, wanted in zip(live, after)),
                    'Interrupted page contains bits outside the exact retained target')
            remaining.append(at)
            if live != before: partial.append(at)
    static = len(original_ui)
    allowed = set(plan['allowedNorSectorOffsets'])
    remaining_nor, partial_nor = [], []
    for at in range(0, SYSTEM_BYTES, 4096):
        before, live = original_system[at:at + 4096], current_system[at:at + 4096]
        if static + at not in allowed:
            require(live == before, 'Settings/recordings/pairing or unrelated metadata changed')
        elif live != images.current_sector:
            require(live == before or all((actual & wanted) == wanted
                                          for actual, wanted in zip(live, images.current_sector)),
                    'Interrupted current-record sector contains unrelated programmed bits')
            remaining_nor.append(static + at)
            if live != before: partial_nor.append(static + at)
    # Current external pairing must still equal the acquired complete pages;
    # it is not enough for another later pairing image to have a valid CRC.
    inspect_external_bonds(current_system, uid)
    inspect_provisioning_seal(current_system, uid, migrated=True)
    require(current_system[0xC000:0xF000] == original_system[0xC000:0xF000],
            'Current pairing differs from retained migration authority')
    for operation in plan['orderedOperations']:
        if 'pageOffsets' in operation:
            operation['pageOffsets'] = [at for at in operation['pageOffsets'] if at in remaining]
        if 'sectorOffsets' in operation:
            operation['sectorOffsets'] = remaining_nor
    plan.update(result='INTERRUPTED_BYTES_MATCH_RETAINED_AUTHORITY_OFFLINE_ONLY',
                currentInternalSha256=sha(current_internal), currentSystemSha256=sha(current_system),
                partialInternalPages=partial, partialCurrentSectors=partial_nor,
                remainingInternalPages=remaining, allowedNorSectorOffsets=remaining_nor,
                resumeSoftwarePlanPrepared=True, mayExecuteRecovery=False,
                normalUartBypassAuthorized=False,
                recoveryDependency='Normal application/physical access and explicit authorization must be resolved separately; this tool never bypasses the UART stop rule.')
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'app', 'boot', 'public-key', 'source-root', 'source-repo',
                 'resource-directory', 'readbacks', 'factory-result', 'loader', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--uid', required=True, help='Exact explicitly selected board UID, no wildcard/default')
    parser.add_argument('--interrupted-readbacks', type=Path,
                        help='Optional separately acquired current snapshot; prepares only a byte-bound offline resume plan')
    args = parser.parse_args()
    require(len(args.uid) == 24 and all(c in '0123456789abcdefABCDEF' for c in args.uid), 'Exact UID required')
    require(not args.output.exists(), 'Refuse to overwrite a prepared migration')
    xy = args.public_key.read_bytes()
    images = inspect_target(args.package, args.app, args.boot, xy, args.source_root, args.source_repo,
                            args.source_commit, args.resource_directory)
    rb = args.readbacks
    uid = exact(rb, 'uid.bin', 12)
    require(uid.hex() == args.uid.lower(), 'Readback UID is not the explicitly requested board')
    validate_identity(exact(rb, 'device-id.bin', 4), exact(rb, 'flash-size.bin', 2),
                      exact(rb, 'options.bin', 4), uid, TARGET)
    factory = load(args.factory_result)
    factory_binding = verify_build_inputs({'source_sha256': {}}, factory, args.source_root,
                                          args.source_repo, args.source_commit, args.resource_directory)
    original_internal = exact(rb, 'private-internal-before.bin', TARGET.flash_bytes)
    original_ui = exact(rb, 'before-ui.bin')
    original_system = exact(rb, 'private-metadata-before.bin', SYSTEM_BYTES)
    if args.interrupted_readbacks is not None:
        current = args.interrupted_readbacks
        require(exact(current, 'uid.bin', 12) == uid, 'Interrupted snapshot belongs to another board')
        validate_identity(exact(current, 'device-id.bin', 4), exact(current, 'flash-size.bin', 2),
                          exact(current, 'options.bin', 4), uid, TARGET)
        require(exact(current, 'before-ui.bin') == original_ui, 'Resource changed during interrupted migration')
        report = make_resume_plan(images, original_internal, original_ui, original_system,
                                  exact(current, 'private-internal-before.bin', TARGET.flash_bytes),
                                  exact(current, 'private-metadata-before.bin', SYSTEM_BYTES),
                                  uid, xy, factory, args.loader.read_bytes())
    else:
        report = make_plan(images, original_internal, original_ui, original_system,
                           uid, xy, factory, args.loader.read_bytes())
    report['factorySourceBinding'] = factory_binding
    args.output.mkdir(parents=True)
    (args.output / 'plan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / 'target-internal.bin').write_bytes(images.internal)
    (args.output / 'current-sector.bin').write_bytes(images.current_sector)
    # Never copy before images, external metadata, host cache or root keys into
    # a public candidate directory. The acquisition journal retains them private.
    print(json.dumps(dict(result=report['result'], uid=report['uid'],
                          targetSha256=images.report['internalTargetSha256'], hardwareOperations=0)))


if __name__ == '__main__':
    main()
