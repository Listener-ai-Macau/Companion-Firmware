import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const PAGE_RELATIVE = path.join(
  "docs",
  "art",
  "iterations",
  "companion-pet-expression-v9-two-track-rig-v7",
  "candidate",
  "wb55-browser-parity-attempt-01",
  "index.html",
);
const PREDECESSOR_CANONICAL_SHA256 =
  "28E9971C068749F67811AD14BF7B81D93E42BE53526243B2B4DE43FA585E52F6";
const INTERMEDIATE_CANONICAL_SHA256 =
  "B6942531757900F1A0787F3B4E49665D35D8704FB700280D75C7FF886DDEAFC9";
const SUCCESSOR_CANONICAL_SHA256 =
  "B0FD8BDFFDF8932A22CFC962B413F1D6DB860514835A9698C761AB21477A5362";

const FAMILY_PLANS = [
  {
    state: "calm",
    story: "calm_presence",
    baseline_frame: 4,
    description: "soft_blink_glint_settle",
    beat: [
      { frame: 2, gaze: "0,0,0,0", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
      { frame: 3, gaze: "1,-1,1,-1", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "curious",
    story: "curious_question",
    baseline_frame: 2,
    description: "listening_side_gaze_brow_answer",
    beat: [
      { frame: 1, gaze: "2,-1,2,-1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "3,-1,3,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "warm",
    story: "warm_presence",
    baseline_frame: 2,
    description: "soft_blink_smile_cheek_settle",
    beat: [
      { frame: 1, gaze: "1,1,1,1", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,1,0,1", components: ["mouth", "cheek", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "playful",
    story: "playful_presence",
    baseline_frame: 2,
    description: "asymmetric_glance_brow_reply",
    beat: [
      { frame: 1, gaze: "2,0,2,1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "3,-1,3,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 2 },
    ],
  },
  {
    state: "sleepy",
    story: "sleepy_presence",
    baseline_frame: 2,
    description: "slow_lid_settle",
    beat: [
      { frame: 1, gaze: "1,1,1,2", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 2 },
      { frame: 2, gaze: "0,2,0,2", components: ["eyelid", "sleep_symbol", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "delighted",
    story: "delighted_presence",
    baseline_frame: 2,
    description: "compact_brow_cheek_lift",
    beat: [
      { frame: 1, gaze: "1,-1,1,-2", components: ["brow", "gaze_highlight"], max_step_px: 2 },
      { frame: 2, gaze: "0,-1,0,-1", components: ["mouth", "cheek", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "bashful",
    story: "bashful_presence",
    baseline_frame: 2,
    description: "down_gaze_cheek_settle",
    beat: [
      { frame: 1, gaze: "0,1,0,2", components: ["brow", "gaze_highlight"], max_step_px: 2 },
      { frame: 2, gaze: "1,2,1,2", components: ["mouth", "cheek", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "thoughtful",
    story: "thoughtful_presence",
    baseline_frame: 2,
    description: "measured_side_gaze_brow_settle",
    beat: [
      { frame: 1, gaze: "0,0,-1,0", components: ["brow", "gaze_highlight"], max_step_px: 2 },
      { frame: 2, gaze: "-1,-1,-1,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "focused",
    story: "focused_presence",
    baseline_frame: 2,
    description: "narrow_blink_centered_return",
    beat: [
      { frame: 1, gaze: "1,-1,1,-1", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,-1,0,-1", components: ["eyelid", "mouth", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "alert",
    story: "alert_exclamation",
    baseline_frame: 2,
    description: "short_brow_eye_brace",
    beat: [
      { frame: 1, gaze: "2,-1,2,-1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "2,0,2,0", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
    ],
  },
];

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function replaceExact(source, before, after, label) {
  const first = source.indexOf(before);
  if (first < 0) {
    throw new Error(`missing ${label}`);
  }
  if (source.indexOf(before, first + before.length) >= 0) {
    throw new Error(`duplicate ${label}`);
  }
  return source.slice(0, first) + after + source.slice(first + before.length);
}

function replaceRange(source, start, end, replacement, label) {
  const first = source.indexOf(start);
  if (first < 0) {
    throw new Error(`missing ${label} start`);
  }
  const last = source.indexOf(end, first);
  if (last < 0) {
    throw new Error(`missing ${label} end`);
  }
  return source.slice(0, first) + replacement + source.slice(last + end.length);
}

const root = path.resolve(process.argv[2] || process.cwd());
const pagePath = path.join(root, PAGE_RELATIVE);
let page = fs.readFileSync(pagePath, "utf8").replace(/\r\n/g, "\n");
const initialSha256 = sha256(page);
if (
  initialSha256 !== PREDECESSOR_CANONICAL_SHA256
  && initialSha256 !== INTERMEDIATE_CANONICAL_SHA256
  && initialSha256 !== SUCCESSOR_CANONICAL_SHA256
) {
  throw new Error(`unexpected predecessor page SHA-256 ${sha256(page)}`);
}

if (initialSha256 === PREDECESSOR_CANONICAL_SHA256) {
page = replaceExact(
  page,
  ".integrated-menu[hidden],.interaction-actions[hidden],.recording-levels[hidden],.recording-indicator[hidden]{display:none}",
  ".integrated-menu[hidden],.interaction-actions[hidden],.recording-levels[hidden]{display:none}",
  "recording indicator hidden CSS",
);
page = replaceExact(
  page,
  ".recording-indicator{position:absolute;left:12px;top:12px;z-index:4;width:10px;height:10px;pointer-events:none;image-rendering:pixelated}",
  "",
  "recording indicator CSS",
);

page = page.replace(
  /(<script id="companion-epaper-visual-manifest" type="application\/json">)(.*?)(<\/script>)/s,
  (_match, prefix, rawManifest, suffix) => {
    const manifest = JSON.parse(rawManifest);
    manifest.requirements = [
      ...manifest.requirements.filter((item) => !["COMP-REQ-540", "COMP-REQ-541"].includes(item)),
      "COMP-REQ-540",
      "COMP-REQ-541",
    ];
    manifest.idle_glint = {
      quiet_steps: 1,
      cycle_steps: 12,
      active_steps: [2, 3],
      baseline_return_step: 4,
      first_nonbaseline_max_ms: 960,
      repeat_quiet_steps: 9,
      baseline_key: "1,0,1,0",
      ordered_keys: [
        "1,0,1,0",
        "1,0,1,0",
        "0,0,0,0",
        "1,-1,1,-1",
        "1,0,1,0",
        "1,0,1,0",
        "1,0,1,0",
        "1,0,1,0",
        "1,0,1,0",
        "1,0,1,0",
        "1,0,1,0",
        "1,0,1,0",
      ],
      changed_frames_per_beat: 3,
      interrupt_policy: "cancel_once_then_family_baseline",
      family_specific: true,
    };
    manifest.recording_accessory = {
      orthogonal_to_expression: true,
      meter_only: true,
      meter: manifest.recording_accessory.meter,
    };
    manifest.family_micro_choreography = {
      cadence_ms: 480,
      first_beat_max_ms: 2880,
      max_changed_frames: 3,
      max_component_step_px: 2,
      minimum_component_classes: 2,
      exact_family_baseline_return: true,
      random_choice: false,
      css_intermediate_frames: false,
      plans: FAMILY_PLANS,
    };
    return `${prefix}${JSON.stringify(manifest)}${suffix}`;
  },
);

page = replaceExact(
  page,
  "const recordingIndicator=document.createElement('canvas');recordingIndicator.className='recording-indicator';recordingIndicator.width=10;recordingIndicator.height=10;recordingIndicator.hidden=true;recordingIndicator.dataset.recordingStatus='inactive';recordingIndicator.setAttribute('aria-hidden','true');overallStage.insertBefore(recordingIndicator,integratedMenu);const recordingIndicatorContext=recordingIndicator.getContext('2d',{willReadFrequently:true});recordingIndicatorContext.fillStyle='#000';[[2,0,6,2],[0,2,10,6],[2,8,6,2]].forEach(rect=>recordingIndicatorContext.fillRect(...rect));\n",
  "",
  "recording indicator DOM",
);
page = replaceExact(
  page,
  "recording_indicator_nodes:overallStage.querySelectorAll('.recording-indicator').length",
  "recording_indicator_nodes:0",
  "recording indicator layer snapshot",
);
page = replaceExact(
  page,
  "idleGlintState={timer:0,step:0,cycle:0,active:false,currentKey:epaperVisualManifest.idle_glint.baseline_key,trace:[],refreshRequests:0,unchangedSteps:0,interruptions:0};",
  "idleGlintState={timer:0,step:0,cycle:0,active:false,currentKey:epaperVisualManifest.idle_glint.baseline_key,currentFrameSrc:'',trace:[],refreshRequests:0,unchangedSteps:0,interruptions:0,request:0,family:''};",
  "idle state",
);
page = replaceExact(
  page,
  "idleGlintState.currentKey=resolvedKey;lastInteraction=mode;return true",
  "idleGlintState.currentKey=resolvedKey;idleGlintState.currentFrameSrc=frame?.src||'';lastInteraction=mode;return true",
  "gaze idle state sync",
);

const familyRuntime = String.raw`function familyMicroPlan(storyName=overallController.state.storyName){return epaperVisualManifest.family_micro_choreography.plans.find(plan=>plan.story===storyName)||null}
function familyMicroSpec(plan,step){const normalized=((Number(step)||0)%epaperVisualManifest.idle_glint.cycle_steps+epaperVisualManifest.idle_glint.cycle_steps)%epaperVisualManifest.idle_glint.cycle_steps,beatIndex=epaperVisualManifest.idle_glint.active_steps.indexOf(normalized),beat=beatIndex>=0?plan.beat[beatIndex]:null;return{normalized,frameIndex:beat?beat.frame:plan.baseline_frame,key:beat?beat.gaze:epaperVisualManifest.idle_glint.baseline_key,components:beat?[...beat.components]:[],maxStepPx:beat?beat.max_step_px:0,phase:beat?'micro_'+(beatIndex+1):(normalized===epaperVisualManifest.idle_glint.baseline_return_step?'baseline_return':'quiet_hold')}}
async function presentFamilyMicroSpec(plan,spec,source){const story=storyByName.get(plan.story),frame=story?.frames[spec.frameIndex];if(!frame||!touchData.overlays[spec.key])return false;const state=overallController.state,request=++idleGlintState.request,epoch=++gazeEpoch,stateRequest=state.request,offset=[0,0],[baseSrc,overlayImage]=await Promise.all([touchGazeClearedBase(frame,''),touchGazeImage(cached(touchData.overlays[spec.key]))]);if(!baseSrc||!overlayImage||request!==idleGlintState.request||epoch!==gazeEpoch||interactionMode!=='expression'||!overallStage.isConnected||state.storyName!==plan.story||state.request!==stateRequest)return false;await touchGazeImage(baseSrc);if(request!==idleGlintState.request||epoch!==gazeEpoch||interactionMode!=='expression'||state.storyName!==plan.story||state.request!==stateRequest)return false;clearTimeout(state.timer);state.timer=0;state.touching=true;state.activeFrame=frame;state.activeFrameIndex=spec.frameIndex;state.activeBaseSrc=frame.touch_base||frame.src;state.activeFrameStartedAt=performance.now();state.activeFrameDurationMs=epaperVisualManifest.cadence_ms;state.pausedRemainingMs=epaperVisualManifest.cadence_ms;state.request++;state.gazeRequest++;state.refreshRequestCount++;overallFrame.dataset.gazeCleared='true';overallFrame.src=baseSrc;overallGaze.style.transform='translate('+offset[0]+'px,'+offset[1]+'px)';overallGaze.src=cached(touchData.overlays[spec.key]);overallFrame.hidden=false;overallGaze.hidden=false;overallStaging.hidden=true;idleGlintState.currentKey=spec.key;idleGlintState.currentFrameSrc=frame.src;idleGlintState.family=plan.state;lastInteraction=source;return true}
function idleGlintEligible(){return interactionMode==='expression'&&!gesture&&!pendingTapPoint&&!touchStoryPaused&&!naturalState.bridge&&naturalState.modeOverride==='none'&&overallController.state.activeFrame&&!overallFrame.hidden&&!!familyMicroPlan()}
function stopIdleGlint(reason='stop'){if(idleGlintState.timer)clearTimeout(idleGlintState.timer);idleGlintState.timer=0;idleGlintState.active=false;idleGlintState.request++;gazeEpoch++;if(reason!=='test_freeze')idleGlintState.interruptions++}
async function commitIdleGlintStep(step,source='scheduler'){const plan=familyMicroPlan();if(!plan)return null;const spec=familyMicroSpec(plan,step),previousKey=idleGlintState.currentKey,previousFrame=idleGlintState.currentFrameSrc,changed=spec.key!==previousKey||storyByName.get(plan.story)?.frames[spec.frameIndex]?.src!==previousFrame;idleGlintState.step=spec.normalized;if(changed){if(!await presentFamilyMicroSpec(plan,spec,source))return null;idleGlintState.refreshRequests++}else idleGlintState.unchangedSteps++;const row={sequence:idleGlintState.trace.length+1,cycle:idleGlintState.cycle,step:spec.normalized,family:plan.state,story:plan.story,phase:spec.phase,frame:storyByName.get(plan.story)?.frames[spec.frameIndex]?.src||null,frame_index:spec.frameIndex,key:spec.key,previous_key:previousKey,previous_frame:previousFrame,changed,refresh_requested:changed,components:spec.components,max_component_step_px:spec.maxStepPx,source};idleGlintState.trace.push(row);if(idleGlintState.trace.length>300)idleGlintState.trace.shift();return row}
function scheduleIdleGlint(){if(!idleGlintEligible()||idleGlintState.timer)return;idleGlintState.active=true;idleGlintState.timer=setTimeout(async()=>{idleGlintState.timer=0;if(!idleGlintEligible()){idleGlintState.active=false;return}const next=(idleGlintState.step+1)%epaperVisualManifest.idle_glint.cycle_steps;if(next===0)idleGlintState.cycle++;await commitIdleGlintStep(next);scheduleIdleGlint()},epaperVisualManifest.cadence_ms)}
async function resumeFamilyMicroBaseline(reason){const plan=familyMicroPlan();if(!plan||!idleGlintEligible())return false;const spec=familyMicroSpec(plan,0),frame=storyByName.get(plan.story)?.frames[spec.frameIndex],needsRestore=idleGlintState.currentKey!==spec.key||idleGlintState.currentFrameSrc!==frame?.src;if(needsRestore&&!await presentFamilyMicroSpec(plan,spec,'resume_'+reason))return false;idleGlintState.step=0;idleGlintState.active=true;scheduleIdleGlint();return true}
window.__interruptEpaperIdleGlint=reason=>{stopIdleGlint(reason);idleGlintState.step=0};
window.__resumeEpaperIdleGlint=reason=>{const eligible=idleGlintEligible();if(eligible)resumeFamilyMicroBaseline(reason);return{reason,active:eligible}};
window.__epaperFreezeIdleGlintStep=async step=>{stopIdleGlint('test_freeze');return commitIdleGlintStep(step,'test_freeze')};
window.__resumeEpaperIdleGlintScheduler=()=>{idleGlintState.active=true;scheduleIdleGlint();return idleGlintState.active};
window.__resetEpaperIdleGlintRealClock=async()=>{stopIdleGlint('test_freeze');idleGlintState.step=0;idleGlintState.cycle=0;idleGlintState.trace=[];idleGlintState.refreshRequests=0;idleGlintState.unchangedSteps=0;const plan=familyMicroPlan();if(!plan)return{eligible:false,started:false,cadence_ms:epaperVisualManifest.cadence_ms};const baseline=familyMicroSpec(plan,0);if(!await presentFamilyMicroSpec(plan,baseline,'idle_real_clock_reset'))return{eligible:false,started:false,cadence_ms:epaperVisualManifest.cadence_ms};scheduleIdleGlint();return{eligible:idleGlintEligible(),started:idleGlintState.active,cadence_ms:epaperVisualManifest.cadence_ms,family:plan.state}};
window.__setFamilyMicroChoreographyFamily=async family=>{const plan=epaperVisualManifest.family_micro_choreography.plans.find(item=>item.state===family);if(!plan)throw new Error('unknown family '+family);stopIdleGlint('test_freeze');naturalEpoch++;naturalClearTimer();naturalState.bridge=null;naturalState.coalescedPending=null;naturalState.pendingOrient=null;naturalState.baseAffect=plan.state;naturalState.reactionPhase='steady';naturalState.modeOverride='none';naturalState.gazeTarget={x:100,y:100,key:epaperVisualManifest.idle_glint.baseline_key};const state=overallController.state,story=storyByName.get(plan.story),baseline=familyMicroSpec(plan,0);clearTimeout(state.timer);state.timer=0;state.touching=true;state.storyName=plan.story;state.frameIndex=plan.baseline_frame;state.activeFrame=story.frames[plan.baseline_frame];state.activeFrameIndex=plan.baseline_frame;state.activeBaseSrc=state.activeFrame.touch_base||state.activeFrame.src;state.request++;idleGlintState.currentFrameSrc='';idleGlintState.currentKey='';idleGlintState.family=plan.state;const presented=await presentFamilyMicroSpec(plan,baseline,'family_test_select');renderExpressionStateView({kind:'family_test_select',family:plan.state});return{family:plan.state,story:plan.story,presented,baseline_frame:plan.baseline_frame}};
window.__familyMicroChoreographyState=()=>({manifest:naturalClone(epaperVisualManifest.family_micro_choreography),family:familyMicroPlan()?.state||null,active:idleGlintState.active,step:idleGlintState.step,cycle:idleGlintState.cycle,current_key:idleGlintState.currentKey,current_frame:idleGlintState.currentFrameSrc,refresh_requests:idleGlintState.refreshRequests,unchanged_steps:idleGlintState.unchangedSteps,interruptions:idleGlintState.interruptions,trace:idleGlintState.trace.map(row=>({...row,components:[...row.components]}))});
`;

page = replaceRange(
  page,
  "function idleGlintEligible()",
  "window.__resetEpaperIdleGlintRealClock=async()=>{stopIdleGlint('test_freeze');idleGlintState.step=0;idleGlintState.cycle=0;idleGlintState.trace=[];idleGlintState.refreshRequests=0;idleGlintState.unchangedSteps=0;await touchSetGaze(epaperVisualManifest.idle_glint.baseline_key,'idle_real_clock_reset');scheduleIdleGlint();return{eligible:idleGlintEligible(),started:idleGlintState.active,cadence_ms:epaperVisualManifest.cadence_ms}};",
  familyRuntime.trimEnd(),
  "idle glint runtime",
);

page = replaceExact(
  page,
  "recordingLevels.hidden=true;recordingIndicator.hidden=true;if(recordingState.active)",
  "recordingLevels.hidden=true;if(recordingState.active)",
  "recording accessory suspend",
);
page = replaceExact(
  page,
  "recordingLevels.hidden=false;recordingIndicator.hidden=false;recordingIndicator.dataset.recordingStatus='active';recordingState.phase='accessory_active';",
  "recordingLevels.hidden=false;recordingState.phase='accessory_active';",
  "recording accessory resume",
);
page = replaceExact(
  page,
  "recordingLevels.hidden=false;recordingIndicator.hidden=false;recordingIndicator.dataset.recordingStatus='active';renderRecordingMeterStep(0,'animation');",
  "recordingLevels.hidden=false;renderRecordingMeterStep(0,'animation');",
  "recording accessory start",
);
page = replaceExact(
  page,
  "recordingLevels.hidden=true;recordingIndicator.hidden=true;recordingIndicator.dataset.recordingStatus='inactive';recordingLevels.getContext('2d').clearRect(0,0,200,200);",
  "recordingLevels.hidden=true;recordingLevels.getContext('2d').clearRect(0,0,200,200);",
  "recording accessory stop",
);
page = replaceExact(
  page,
  "indicatorNodes:overallStage.querySelectorAll('.recording-indicator').length,indicatorVisible:!recordingIndicator.hidden,",
  "indicatorNodes:0,indicatorVisible:false,",
  "recording contract indicator",
);
page = replaceExact(
  page,
  "if(!recordingIndicator.hidden)x.drawImage(recordingIndicator,12,12);",
  "",
  "recording indicator canvas composition",
);
page = replaceExact(
  page,
  "recordingIndicatorHidden:recordingIndicator.hidden,",
  "recordingIndicatorHidden:true,",
  "touch snapshot indicator",
);
}

if (initialSha256 === INTERMEDIATE_CANONICAL_SHA256) {
  page = replaceExact(
    page,
    "stateRequest=state.request,offset=touchData.story_offsets[plan.story]||[0,0],[baseSrc,overlayImage]=await Promise.all([touchGazeClearedBase(frame,plan.story),",
    "stateRequest=state.request,offset=[0,0],[baseSrc,overlayImage]=await Promise.all([touchGazeClearedBase(frame,''),",
    "family gaze optical anchor",
  );
  page = replaceExact(
    page,
    "return false;state.activeFrame=frame;state.activeFrameIndex=spec.frameIndex;",
    "return false;clearTimeout(state.timer);state.timer=0;state.touching=true;state.activeFrame=frame;state.activeFrameIndex=spec.frameIndex;",
    "family timer ownership",
  );
  page = replaceExact(
    page,
    "const state=overallController.state,story=storyByName.get(plan.story),baseline=familyMicroSpec(plan,0);state.storyName=plan.story;",
    "const state=overallController.state,story=storyByName.get(plan.story),baseline=familyMicroSpec(plan,0);clearTimeout(state.timer);state.timer=0;state.touching=true;state.storyName=plan.story;",
    "family test timer ownership",
  );
}

if (page.includes("recording-indicator")) {
  throw new Error("recording-indicator source survived");
}
if ((page.match(/family_micro_choreography/g) || []).length < 3) {
  throw new Error("family choreography contract was not installed");
}

fs.writeFileSync(pagePath, page, "utf8");
console.log(
  JSON.stringify(
    {
      status: "PASS",
      page: PAGE_RELATIVE.replaceAll("\\", "/"),
      predecessor_canonical_sha256: PREDECESSOR_CANONICAL_SHA256,
      successor_canonical_sha256: sha256(page),
      families: FAMILY_PLANS.length,
      recording_indicator_occurrences: 0,
    },
    null,
    2,
  ),
);
