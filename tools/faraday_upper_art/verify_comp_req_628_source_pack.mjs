#!/usr/bin/env node
/* Verify that the current browser page and STM32 frame pack are identical. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-628-status-bar/index.html";
const contractRel = ".cache/validation/comp-req-628-status-bar/epaper-source-contract.json";
const packRel = ".cache/validation/comp-req-628-status-bar/current-source-pack";
const sha = data => crypto.createHash("sha256").update(data).digest("hex").toUpperCase();
const textSha = data => sha(Buffer.from(data.toString("utf8").replaceAll("\r\n", "\n"), "utf8"));
const read = relative => fs.readFileSync(path.join(root, relative));
const load = relative => JSON.parse(read(relative));
const failures = [];
const checks = {};
const requireCheck = (name, value) => { checks[name] = Boolean(value); if (!value) failures.push(name); };

const page = read(pageRel);
const contract = load(contractRel);
const manifestRel = `${packRel}/source-pack-manifest.json`;
const manifest = load(manifestRel);
const manifestBytes = read(manifestRel);
const expectedPageSha = contract.browser_page?.sha256;
const actualPageSha = textSha(page);
requireCheck("contract_schema", contract.schema === "companion.comp_req_638.browser_epaper_source_contract.v1");
requireCheck("page_identity", actualPageSha === expectedPageSha && manifest.source?.page_sha256 === expectedPageSha);
requireCheck("pack_manifest_identity", sha(manifestBytes) === contract.source_pack?.manifest_sha256);
requireCheck("pack_pass", manifest.status === "PASS");
requireCheck("pack_format", manifest.format?.width === 200 && manifest.format?.height === 200
  && manifest.format?.stride_bytes === 25 && manifest.format?.frame_bytes === 5000
  && manifest.format?.cadence_ms === 480);
requireCheck("pack_invariants", manifest.invariants?.all_inputs_binary === true
  && manifest.invariants?.all_states_are_5000_bytes === true
  && manifest.invariants?.all_states_have_black_pixels === true);
requireCheck("pack_counts", manifest.states?.length === contract.source_pack?.state_count
  && manifest.invariants?.unique_frame_count === contract.source_pack?.unique_frame_count);

const frameBytes = read(`${packRel}/frames.bin`);
const cBytes = read(`${packRel}/comp_req_628_source_pack.c`);
const hBytes = read(`${packRel}/comp_req_628_source_pack.h`);
requireCheck("frames_hash", sha(frameBytes) === manifest.files?.frames?.sha256);
requireCheck("c_hash", sha(cBytes) === manifest.files?.c?.sha256);
requireCheck("h_hash", sha(hBytes) === manifest.files?.h?.sha256);
requireCheck("frames_size", frameBytes.length === manifest.invariants.unique_frame_count * 5000);
requireCheck("c_header_contract", cBytes.includes(Buffer.from("COMP_REQ_628_SOURCE_PACK_ENABLED"))
  && hBytes.includes(Buffer.from("COMP_REQ_628_FRAME_BYTES 5000")));
let compile = null;
try { compile = load(`${packRel}/compile/source-pack-compile.json`); } catch { compile = null; }
const objectPath = compile?.object?.path ? `${packRel}/compile/${compile.object.path}`.replace(`${packRel}/compile/../`, `${packRel}/`) : null;
let objectBytes = null;
try { objectBytes = objectPath ? fs.readFileSync(path.join(root, objectPath)) : null; } catch { objectBytes = null; }
let defaultOffBytes = null;
try { defaultOffBytes = fs.readFileSync(path.join(root, `${packRel}/compile/${compile?.default_off_object?.path || ""}`)); } catch { defaultOffBytes = null; }
requireCheck("arm_gcc_compile", compile?.status === "PASS_ARM_GCC_OBJECT"
  && compile?.source?.sha256 === manifest.files?.c?.sha256
  && compile?.header?.sha256 === manifest.files?.h?.sha256
  && objectBytes?.length === compile?.object?.bytes
  && objectBytes && sha(objectBytes) === compile?.object?.sha256
  && defaultOffBytes?.length === compile?.default_off_object?.bytes
  && defaultOffBytes && sha(defaultOffBytes) === compile?.default_off_object?.sha256
  && compile?.hardware_contact === 0 && compile?.physical_execute === false);
let cempManifest = null;
let cempVerification = null;
let cempBytes = null;
try {
  cempManifest = load(contract.external_cemp.manifest_path);
  cempVerification = load(contract.external_cemp.verification_path);
  cempBytes = read(contract.external_cemp.pack_path);
} catch { /* CEMP evidence is checked below as a single bound gate. */ }
requireCheck("external_cemp_bound", cempManifest?.source?.browser_page_sha256 === actualPageSha
  && cempManifest?.source?.source_pack_manifest_sha256 === sha(manifestBytes)
  && cempManifest?.profile?.width === 200
  && cempManifest?.profile?.height === 200
  && cempManifest?.encoding === "packbits"
  && cempManifest?.source?.state_count === contract.external_cemp.state_count
  && cempManifest?.source?.clip_count === contract.external_cemp.clip_count
  && cempManifest?.source?.frame_count === contract.external_cemp.frame_count
  && cempVerification?.clip_count === contract.external_cemp.clip_count
  && cempVerification?.frame_count === contract.external_cemp.frame_count
  && cempVerification?.status === "PASS_CEMP_EXTERNAL_SOURCE_BOUND"
  && cempBytes && sha(cempBytes) === contract.external_cemp.pack_sha256
  && cempBytes.length === contract.external_cemp.pack_bytes
  && cempVerification?.pack_sha256 === contract.external_cemp.pack_sha256
  && cempVerification?.manifest_sha256 === contract.external_cemp.manifest_sha256);

/* The source pack is only useful for the target if the WB55 mount buffers can
 * hold the same catalog.  Keep this check tied to the binary CEMP header so a
 * future pack expansion cannot silently regress to CAPACITY_EXCEEDED. */
let stm32AppBleBytes = null;
let stm32AppBleText = null;
try {
  stm32AppBleBytes = read("cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c");
  stm32AppBleText = stm32AppBleBytes.toString("utf8");
} catch { stm32AppBleText = null; }
let stm32MakefileBytes = null;
let stm32MakefileText = null;
try {
  stm32MakefileBytes = read("cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile");
  stm32MakefileText = stm32MakefileBytes.toString("utf8");
} catch { stm32MakefileText = null; }
let flashRunnerBytes = null;
let flashRunnerText = null;
try {
  flashRunnerBytes = read("tools/flash_nucleo_bringup.ps1");
  flashRunnerText = flashRunnerBytes.toString("utf8");
} catch { flashRunnerText = null; }
const capacityFor = name => {
  const match = stm32AppBleText?.match(new RegExp(`^\\s*#define\\s+${name}\\s+(\\d+)u?`, "m"));
  return match ? Number(match[1]) : 0;
};
const cempClipCount = cempBytes?.length >= 32 ? cempBytes.readUInt16LE(28) : 0;
const cempFrameCount = cempBytes?.length >= 32 ? cempBytes.readUInt16LE(30) : 0;
const cempStringSize = cempBytes?.length >= 48 ? cempBytes.readUInt32LE(44) : 0;
requireCheck("stm32_cemp_capacity",
  capacityFor("COMPANION_SCREEN_ASSET_CLIP_CAPACITY") >= cempClipCount
  && capacityFor("COMPANION_SCREEN_ASSET_FRAME_CAPACITY") >= cempFrameCount
  && capacityFor("COMPANION_SCREEN_ASSET_STRING_CAPACITY") >= cempStringSize);
const stm32AppBleSha = stm32AppBleBytes ? sha(stm32AppBleBytes) : null;
const stm32MakefileSha = stm32MakefileBytes ? sha(stm32MakefileBytes) : null;
requireCheck("stm32_mount_contract",
  contract.stm32_mount_contract?.path === "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
  && contract.stm32_mount_contract?.sha256 === stm32AppBleSha
  && contract.stm32_mount_contract?.activation_macro === "COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK"
  && contract.stm32_mount_contract?.activation_default === capacityFor("COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK")
  && contract.stm32_mount_contract?.activation_default === 0
  && contract.stm32_mount_contract?.activation_candidate_value === 1
  && contract.stm32_mount_contract?.build_switch?.makefile_path === "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
  && contract.stm32_mount_contract?.build_switch?.makefile_sha256 === stm32MakefileSha
  && contract.stm32_mount_contract?.build_switch?.make_variable === "EPAPER_COMP_REQ_638_SOURCE_PACK"
  && contract.stm32_mount_contract?.build_switch?.make_value === 1
  && stm32MakefileText?.includes("EPAPER_COMP_REQ_638_SOURCE_PACK")
  && contract.stm32_mount_contract?.clip_capacity === capacityFor("COMPANION_SCREEN_ASSET_CLIP_CAPACITY")
  && contract.stm32_mount_contract?.frame_capacity === capacityFor("COMPANION_SCREEN_ASSET_FRAME_CAPACITY")
  && contract.stm32_mount_contract?.string_capacity === capacityFor("COMPANION_SCREEN_ASSET_STRING_CAPACITY")
  && contract.stm32_mount_contract?.covers_current_cemp === true
  && contract.stm32_mount_contract?.clip_capacity >= cempClipCount
  && contract.stm32_mount_contract?.frame_capacity >= cempFrameCount
  && contract.stm32_mount_contract?.string_capacity >= cempStringSize);
const candidateBuild = contract.stm32_mount_contract?.candidate_build;
const candidateArtifactSha = relative => {
  try { return sha(read(relative)); } catch { return null; }
};
requireCheck("stm32_candidate_build",
  candidateBuild?.build_dir === "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_638"
  && candidateBuild?.define === "COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1"
  && candidateBuild?.status === "PASS_ARM_GCC_FIRMWARE_BUILD"
  && candidateBuild?.elf_sha256 === candidateArtifactSha(candidateBuild?.elf_path)
  && candidateBuild?.hex_sha256 === candidateArtifactSha(candidateBuild?.hex_path)
  && candidateBuild?.bin_sha256 === candidateArtifactSha(candidateBuild?.bin_path)
  && candidateBuild?.physical_execute === false
  && candidateBuild?.hardware_contact === 0);
const provisionBuild = contract.stm32_mount_contract?.provision_build;
const provisionArtifactBytes = relative => {
  try { return read(relative); } catch { return null; }
};
requireCheck("stm32_provision_build",
  provisionBuild?.build_dir === "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_638_provision"
  && provisionBuild?.define === "COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1;COMPANION_SCREEN_ASSET_PROVISION=1"
  && provisionBuild?.status === "PASS_ARM_GCC_PROVISION_BUILD"
  && provisionBuild?.manifest_path === contract.external_cemp.manifest_path
  && provisionBuild?.manifest_sha256 === sha(read(provisionBuild?.manifest_path))
  && provisionBuild?.embedded_pack_sha256 === candidateArtifactSha(provisionBuild?.embedded_pack_path)
  && provisionBuild?.embedded_pack_bytes === provisionArtifactBytes(provisionBuild?.embedded_pack_path)?.length
  && provisionBuild?.embedded_pack_sha256 === contract.external_cemp.pack_sha256
  && provisionBuild?.embedded_pack_bytes === contract.external_cemp.pack_bytes
  && provisionBuild?.header_sha256 === candidateArtifactSha(provisionBuild?.header_path)
  && provisionBuild?.elf_sha256 === candidateArtifactSha(provisionBuild?.elf_path)
  && provisionBuild?.hex_sha256 === candidateArtifactSha(provisionBuild?.hex_path)
  && provisionBuild?.bin_sha256 === candidateArtifactSha(provisionBuild?.bin_path)
  && provisionBuild?.physical_execute === false
  && provisionBuild?.hardware_contact === 0);
const flashRunner = contract.stm32_mount_contract?.flash_runner;
const flashRunnerSha = flashRunnerBytes ? sha(flashRunnerBytes) : null;
requireCheck("stm32_flash_runner",
  flashRunner?.path === "tools/flash_nucleo_bringup.ps1"
  && flashRunner?.sha256 === flashRunnerSha
  && flashRunner?.provision_switch === "-CompReq638Provision"
  && flashRunner?.candidate_switch === "-CompReq638Candidate"
  && flashRunner?.provision_hex_sha256 === provisionBuild?.hex_sha256
  && flashRunner?.candidate_hex_sha256 === candidateBuild?.hex_sha256
  && flashRunner?.hardware_lock_required === true
  && flashRunner?.physical_execute === false
  && flashRunnerText?.includes("CompReq638Provision")
  && flashRunnerText?.includes("CompReq638Candidate")
  && flashRunnerText?.includes("Enter-CompanionWb55Lock"));

const uniqueCount = manifest.invariants.unique_frame_count;
const stateChecks = [];
for (const state of manifest.states || []) {
  const pbmPath = `${packRel}/${state.pbm_file}`;
  const pbm = fs.readFileSync(path.join(root, pbmPath));
  const marker = Buffer.from("P4\n200 200\n", "ascii");
  const payload = pbm.subarray(marker.length);
  const uniqueIndex = Number(state.unique_frame_index);
  const unique = frameBytes.subarray(uniqueIndex * 5000, (uniqueIndex + 1) * 5000);
  stateChecks.push(
    uniqueIndex >= 0 && uniqueIndex < uniqueCount
      && state.gray_input_pixels === 0
      && state.black_pixels > 0
      && sha(pbm) === state.pbm_sha256
      && payload.length === 5000
      && Buffer.compare(payload, unique) === 0,
  );
}
requireCheck("state_payloads", stateChecks.length === manifest.states.length && stateChecks.every(Boolean));
requireCheck("physical_closed", contract.physical_sync?.current_status === "NOT_EXECUTED"
  && contract.consumer?.hardware_contact === 0);
const handoffRel = contract.physical_sync?.handoff_path;
let handoff = null;
try { handoff = handoffRel ? load(handoffRel) : null; } catch { handoff = null; }
requireCheck("current_handoff_bound", handoff?.schema === "companion.comp_req_638.current_physical_handoff.v1"
  && handoff?.status === "READY_CURRENT_SOURCE_NO_EXECUTE"
  && handoff?.page?.sha256 === actualPageSha
  && handoff?.source_pack?.manifest_sha256 === sha(manifestBytes)
  && handoff?.source_pack?.c_sha256 === manifest.files?.c?.sha256
  && handoff?.source_pack?.h_sha256 === manifest.files?.h?.sha256
  && handoff?.source_pack?.frames_sha256 === manifest.files?.frames?.sha256
  && handoff?.source_pack?.arm_gcc_object_sha256 === compile?.object?.sha256
  && handoff?.source_pack?.arm_gcc_default_off_object_sha256 === compile?.default_off_object?.sha256
  && handoff?.stm32_mount_contract?.path === contract.stm32_mount_contract?.path
  && handoff?.stm32_mount_contract?.sha256 === stm32AppBleSha
  && handoff?.stm32_mount_contract?.activation_macro === "COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK"
  && handoff?.stm32_mount_contract?.activation_default === 0
  && handoff?.stm32_mount_contract?.activation_candidate_value === 1
  && handoff?.stm32_mount_contract?.build_switch?.makefile_path === contract.stm32_mount_contract?.build_switch?.makefile_path
  && handoff?.stm32_mount_contract?.build_switch?.makefile_sha256 === stm32MakefileSha
  && handoff?.stm32_mount_contract?.build_switch?.make_variable === "EPAPER_COMP_REQ_638_SOURCE_PACK"
  && handoff?.stm32_mount_contract?.build_switch?.make_value === 1
  && handoff?.stm32_mount_contract?.candidate_build?.elf_sha256 === candidateBuild?.elf_sha256
  && handoff?.stm32_mount_contract?.candidate_build?.hex_sha256 === candidateBuild?.hex_sha256
  && handoff?.stm32_mount_contract?.candidate_build?.bin_sha256 === candidateBuild?.bin_sha256
  && handoff?.stm32_mount_contract?.candidate_build?.physical_execute === false
  && handoff?.stm32_mount_contract?.candidate_build?.hardware_contact === 0
  && handoff?.stm32_mount_contract?.provision_build?.embedded_pack_sha256 === provisionBuild?.embedded_pack_sha256
  && handoff?.stm32_mount_contract?.provision_build?.embedded_pack_bytes === provisionBuild?.embedded_pack_bytes
  && handoff?.stm32_mount_contract?.provision_build?.header_sha256 === provisionBuild?.header_sha256
  && handoff?.stm32_mount_contract?.provision_build?.elf_sha256 === provisionBuild?.elf_sha256
  && handoff?.stm32_mount_contract?.provision_build?.hex_sha256 === provisionBuild?.hex_sha256
  && handoff?.stm32_mount_contract?.provision_build?.bin_sha256 === provisionBuild?.bin_sha256
  && handoff?.stm32_mount_contract?.provision_build?.physical_execute === false
  && handoff?.stm32_mount_contract?.provision_build?.hardware_contact === 0
  && handoff?.stm32_mount_contract?.flash_runner?.path === flashRunner?.path
  && handoff?.stm32_mount_contract?.flash_runner?.sha256 === flashRunnerSha
  && handoff?.stm32_mount_contract?.flash_runner?.provision_hex_sha256 === provisionBuild?.hex_sha256
  && handoff?.stm32_mount_contract?.flash_runner?.candidate_hex_sha256 === candidateBuild?.hex_sha256
  && handoff?.stm32_mount_contract?.flash_runner?.hardware_lock_required === true
  && handoff?.stm32_mount_contract?.flash_runner?.physical_execute === false
  && handoff?.stm32_mount_contract?.clip_capacity === capacityFor("COMPANION_SCREEN_ASSET_CLIP_CAPACITY")
  && handoff?.stm32_mount_contract?.frame_capacity === capacityFor("COMPANION_SCREEN_ASSET_FRAME_CAPACITY")
  && handoff?.stm32_mount_contract?.string_capacity === capacityFor("COMPANION_SCREEN_ASSET_STRING_CAPACITY")
  && handoff?.stm32_mount_contract?.covers_cemp_clips >= cempClipCount
  && handoff?.stm32_mount_contract?.covers_cemp_frames >= cempFrameCount
  && handoff?.stm32_mount_contract?.covers_cemp_strings >= cempStringSize
  && handoff?.physical_execute === false
  && handoff?.hardware_contact === 0
  && handoff?.stale_handoff_rejection?.identity_matches_current === false);

const report = {
  schema: "companion.comp_req_638.source_pack_verification.v1",
  status: failures.length === 0 ? "PASS_SOURCE_PACK_BOUND" : "NO_GO_SOURCE_PACK",
  page_sha256: actualPageSha,
  source_pack_manifest_sha256: sha(manifestBytes),
  checks,
  failures,
  state_count: manifest.states?.length || 0,
  unique_frame_count: uniqueCount,
};
const reportRel = `${packRel}/source-pack-verification.json`;
fs.writeFileSync(path.join(root, reportRel), `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (report.status !== "PASS_SOURCE_PACK_BOUND") process.exitCode = 1;
