"""GATT auto-record: START → wait → STOP → print list. Uses Companion UUID table."""
import asyncio, struct, json, pathlib, sys
from bleak import BleakClient, BleakScanner

def load_uuids(repo: pathlib.Path):
    table = json.loads((repo / "docs/ble_uuid_table.json").read_text(encoding="utf-8"))
    return {c["name"]: c["uuid"] for s in table["services"] for c in s.get("characteristics", [])}

def pack_ctrl(cmd, rid, max_s, profile_id=0):
    return struct.pack("<BBBBIH", 1, cmd, profile_id, 0, rid, max_s)

def parse_list(payload: bytes):
    schema, count, entry_bytes = struct.unpack_from("<BBH", payload)
    entries, off, fmt = [], 4, "<IIIBBBBI8sI"
    esz = struct.calcsize(fmt)
    for _ in range(count):
        v = struct.unpack_from(fmt, payload, off)
        entries.append({"id": v[0], "dur_ms": v[2], "codec": v[3], "len": v[7]})
        off += esz
    return {"count": count, "entries": entries}

async def notify_write(client, uuid, payload, timeout=10.0):
    q = asyncio.Queue()
    await client.start_notify(uuid, lambda h, d: q.put_nowait(bytes(d)))
    await asyncio.sleep(0.2)
    await client.write_gatt_char(uuid, payload, response=True)
    try:
        raw = await asyncio.wait_for(q.get(), timeout=timeout)
        print("echo", raw.hex())
        return True
    except Exception as e:
        print("echo_timeout", e)
        return False
    finally:
        try:
            await client.stop_notify(uuid)
        except Exception:
            pass

async def main():
    repo = pathlib.Path(__file__).resolve().parents[1]
    uuids = load_uuids(repo)
    list_only = len(sys.argv) > 1 and sys.argv[1] == "--list-only"
    max_s = int(sys.argv[1]) if len(sys.argv) > 1 and not list_only else 5
    wait_s = float(sys.argv[2]) if len(sys.argv) > 2 else max_s + 2.0
    # Product recordings must use the live board microphone.  Profile 0 is a
    # retired synthetic fixture and production firmware correctly rejects it;
    # defaulting to it made an otherwise valid regression look like a broken
    # double-tap/recording path.
    profile_id = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    found = await BleakScanner.discover(timeout=8.0)
    dev = next((d for d in found if d.name and "companion" in d.name.lower()), None)
    if not dev:
        print("NO_DEVICE"); return 2
    print("device", dev.address)
    # Windows keeps the characteristic handle table across firmware updates.
    # A stale 0x3002 handle makes the first recording-list read close the
    # WinRT object even though the board remains healthy.  Product acceptance
    # clients already bypass that cache and pair before the first read; keep
    # this small screen/recording trigger on the same connection contract.
    client_kwargs = {
        "timeout": 20.0,
        "winrt": {"use_cached_services": False},
    }
    async with BleakClient(dev, **client_kwargs) as client:
        await asyncio.sleep(2.0)
        if hasattr(client, "pair"):
            try:
                await client.pair()
            except Exception as exc:
                # ATTR_PERMISSION_NONE allows an unpaired bench link; pairing
                # failure is diagnostic, not permission to skip the real read.
                print("pair_skip", repr(exc))
        listing0 = parse_list(bytes(await client.read_gatt_char(uuids["recording_list"])))
        print("LIST0", json.dumps(listing0))
        if list_only:
            return 0
        await notify_write(client, uuids["recording_control"], pack_ctrl(1, 5001, max_s, profile_id))
        # START acknowledgement only means the request entered the board's
        # asynchronous storage/erase queue.  Start the requested visible
        # recording interval after a new codec=3 entry exposes its first
        # durable prefix; otherwise a full-ring erase can consume the whole
        # wait and STOP a sub-second capture.
        before_ids = {entry["id"] for entry in listing0["entries"]}
        activation_deadline = asyncio.get_running_loop().time() + 180.0
        active = None
        while asyncio.get_running_loop().time() < activation_deadline:
            current = parse_list(bytes(await client.read_gatt_char(uuids["recording_list"])))
            active = next((entry for entry in current["entries"]
                           if entry["id"] not in before_ids
                           and entry["codec"] == 3
                           and entry["len"] > 0), None)
            if active:
                break
            await asyncio.sleep(0.5)
        if not active:
            print("ACTIVATION_TIMEOUT")
            await notify_write(client, uuids["recording_control"],
                               pack_ctrl(2, 5002, 0, profile_id))
            return 4
        print("ACTIVE", json.dumps(active))
        print(f"wait {wait_s}s...")
        await asyncio.sleep(wait_s)
        await notify_write(client, uuids["recording_control"], pack_ctrl(2, 5002, 0, profile_id))
        await asyncio.sleep(1.0)
        listing = parse_list(bytes(await client.read_gatt_char(uuids["recording_list"])))
        print("LIST1", json.dumps(listing))
        before = {
            (e.get("id"), e.get("dur_ms"), e.get("codec"), e.get("len"))
            for e in listing0["entries"]
        }
        changed = [
            e for e in listing["entries"]
            if (e.get("id"), e.get("dur_ms"), e.get("codec"), e.get("len"))
            not in before
        ]
        e = changed[0] if changed else {}
        ok = bool(changed) and e.get("dur_ms", 0) > 0 and e.get("len", 0) not in (0, 7327)
        print("AUTO_RECORD", ok, e, "changed_entries", len(changed))
        return 0 if ok else 3

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
