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
const THOUGHTFUL_PRE_FIX_CANONICAL_SHA256 =
  "B0FD8BDFFDF8932A22CFC962B413F1D6DB860514835A9698C761AB21477A5362";
const COMPONENT_PRE_FIX_CANONICAL_SHA256 =
  "D33950E3771649A2AB3F980F51351FA77FEE306436A58FC2C7170F40F0BD0507";
const SUCCESSOR_CANONICAL_SHA256 =
  "D3537B7EDE53075DC25091C6F5CFF75408E4975F2A71D0FDF5D1A248C871CBC8";
const COMP_REQ_543_PREVIEW_SHA256 =
  "D91C6A2440FC75A2FE8CCD7626FA28B7CE588219EFC960B1F6CDFF907E1954CC";
const CURRENT_DYNAMIC_PAGE_SHA256 =
  "8E95CD8F770E5B8EFF22749EAE952D7ECD2AFCF9BB9B0E53615DA27DCDA527DB";

const FAMILY_PLANS = [
  {
    state: "calm",
    story: "calm_presence",
    baseline_frame: 4,
    description: "soft_blink_glint_settle",
    beat: [
      { frame: 2, gaze: "0,0,0,0", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
      { frame: 3, gaze: "1,-1,1,-1", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,0,0,0", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
      { frame: 3, gaze: "1,-1,1,-1", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,0,0,0", components: ["eyelid", "gaze_highlight"], max_step_px: 1 },
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
      { frame: 1, gaze: "2,-1,2,-1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "3,-1,3,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "2,-1,2,-1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "warm",
    story: "warm_presence",
    baseline_frame: 2,
    description: "soft_blink_smile_cheek_settle",
    beat: [
      {
        frame: 1,
        gaze: "1,1,1,1",
        components: ["eyelid", "brow", "gaze_highlight"],
        max_step_px: 1,
        transplants: [
          { story: "calm_presence", frame: 3, rect: [38, 108, 44, 52] },
          { story: "calm_presence", frame: 3, rect: [120, 108, 44, 52] },
        ],
      },
      { frame: 2, gaze: "0,1,0,1", components: ["mouth", "cheek", "gaze_highlight"], max_step_px: 1 },
      {
        frame: 1,
        gaze: "1,1,1,1",
        components: ["eyelid", "brow", "gaze_highlight"],
        max_step_px: 1,
        transplants: [
          { story: "calm_presence", frame: 3, rect: [38, 108, 44, 52] },
          { story: "calm_presence", frame: 3, rect: [120, 108, 44, 52] },
        ],
      },
      { frame: 2, gaze: "0,1,0,1", components: ["mouth", "cheek", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "1,1,1,1", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 1 },
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
      { frame: 1, gaze: "2,0,2,1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "3,-1,3,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 2 },
      { frame: 1, gaze: "2,0,2,1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
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
      { frame: 1, gaze: "1,1,1,2", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 2 },
      { frame: 2, gaze: "0,2,0,2", components: ["eyelid", "sleep_symbol", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "1,1,1,2", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 2 },
    ],
  },
  {
    state: "delighted",
    story: "delighted_presence",
    baseline_frame: 2,
    description: "compact_brow_cheek_lift",
    beat: [
      {
        frame: 2,
        gaze: "1,-1,1,-2",
        components: ["brow", "cheek", "gaze_highlight"],
        max_step_px: 2,
        shifts: [
          { rect: [40, 76, 38, 28], delta: [0, -1] },
          { rect: [120, 76, 38, 28], delta: [0, -1] },
          { rect: [27, 150, 27, 23], delta: [0, -1] },
          { rect: [147, 150, 27, 23], delta: [0, -1] },
        ],
      },
      {
        frame: 2,
        gaze: "1,-1,1,-2",
        components: ["brow", "cheek", "gaze_highlight"],
        max_step_px: 2,
        shifts: [
          { rect: [40, 76, 38, 28], delta: [0, -1] },
          { rect: [120, 76, 38, 28], delta: [0, -1] },
        ],
      },
      {
        frame: 2,
        gaze: "0,-1,0,-1",
        components: ["cheek", "gaze_highlight"],
        max_step_px: 1,
        shifts: [
          { rect: [27, 150, 27, 23], delta: [0, -1] },
          { rect: [147, 150, 27, 23], delta: [0, -1] },
        ],
      },
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
      { frame: 1, gaze: "0,1,0,2", components: ["brow", "gaze_highlight"], max_step_px: 2 },
      { frame: 2, gaze: "1,2,1,2", components: ["mouth", "cheek", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "0,1,0,2", components: ["brow", "gaze_highlight"], max_step_px: 2 },
    ],
  },
  {
    state: "thoughtful",
    story: "thoughtful_presence",
    baseline_frame: 2,
    description: "measured_side_gaze_brow_settle",
    beat: [
      { frame: 1, gaze: "0,0,0,0", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,-1,0,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "0,0,0,0", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,-1,0,-1", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "0,0,0,0", components: ["brow", "gaze_highlight"], max_step_px: 1 },
    ],
  },
  {
    state: "focused",
    story: "focused_presence",
    baseline_frame: 2,
    description: "narrow_blink_centered_return",
    beat: [
      {
        frame: 2,
        gaze: "1,-1,1,-1",
        components: ["eyelid", "brow", "gaze_highlight"],
        max_step_px: 1,
        transplants: [
          { story: "calm_presence", frame: 3, rect: [38, 108, 44, 52] },
          { story: "calm_presence", frame: 3, rect: [120, 108, 44, 52] },
        ],
      },
      { frame: 2, gaze: "0,-1,0,-1", components: ["eyelid", "mouth", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "1,-1,1,-1", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "0,-1,0,-1", components: ["eyelid", "mouth", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "1,-1,1,-1", components: ["eyelid", "brow", "gaze_highlight"], max_step_px: 1 },
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
      { frame: 1, gaze: "2,-1,2,-1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
      { frame: 2, gaze: "2,0,2,0", components: ["brow", "mouth", "gaze_highlight"], max_step_px: 1 },
      { frame: 1, gaze: "2,-1,2,-1", components: ["brow", "gaze_highlight"], max_step_px: 1 },
    ],
  },
];

// COMP-REQ-544 keeps blink out of the family beat. These are slow, authored
// pose changes; the sparse blink timeline below owns eyelid closure separately.
const familyBeat = (frame, gaze, components, max_step_px = 1, extra = {}) => ({
  frame,
  gaze,
  components,
  max_step_px,
  ...extra,
});
const NON_BLINK_BEATS = {
  calm: [
    familyBeat(4, "-2,0,-6,0", ["gaze", "gaze_highlight", "brow"], 1, { shifts: [{ rect: [40, 76, 38, 28], delta: [0, -1] }, { rect: [120, 76, 38, 28], delta: [0, -1] }] }),
    familyBeat(4, "5,0,5,0", ["gaze", "gaze_highlight", "brow", "cheek"], 1, { shifts: [{ rect: [40, 76, 38, 28], delta: [0, -1] }, { rect: [120, 76, 38, 28], delta: [0, -1] }, { rect: [27, 150, 27, 23], delta: [0, -1] }, { rect: [147, 150, 27, 23], delta: [0, -1] }] }),
    familyBeat(4, "1,4,1,6", ["gaze", "gaze_highlight", "mouth"], 1),
    familyBeat(4, "0,0,0,0", ["gaze", "gaze_highlight", "brow", "mouth"], 1, { shifts: [{ rect: [95, 128, 12, 12], delta: [0, -1] }] }),
  ],
  curious: [
    familyBeat(1, "1,-3,1,-6", ["gaze", "gaze_highlight", "brow"]),
    familyBeat(2, "5,0,5,0", ["gaze", "gaze_highlight", "brow", "mouth"]),
    familyBeat(1, "-2,0,-6,0", ["gaze", "gaze_highlight", "brow", "cheek"]),
    familyBeat(2, "0,0,0,0", ["gaze", "gaze_highlight", "brow", "mouth"]),
  ],
  warm: [
    familyBeat(1, "-2,0,-6,0", ["gaze", "brow", "gaze_highlight"]),
    familyBeat(2, "1,-3,1,-6", ["gaze", "mouth", "cheek", "gaze_highlight"]),
    familyBeat(3, "5,0,5,0", ["gaze", "mouth", "cheek", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "mouth", "gaze_highlight"]),
  ],
  playful: [
    familyBeat(1, "5,0,5,0", ["gaze", "brow", "gaze_highlight"]),
    familyBeat(2, "-2,0,-6,0", ["gaze", "brow", "mouth", "gaze_highlight"], 2),
    familyBeat(3, "1,4,1,6", ["gaze", "brow", "cheek", "gaze_highlight"], 2),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "mouth", "gaze_highlight"], 2),
  ],
  sleepy: [
    familyBeat(1, "1,4,1,6", ["eyelid", "gaze", "brow", "gaze_highlight"], 2),
    familyBeat(2, "1,-3,1,-6", ["eyelid", "sleep_symbol", "gaze", "gaze_highlight"]),
    familyBeat(3, "-2,0,-6,0", ["eyelid", "sleep_symbol", "mouth", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["eyelid", "gaze", "brow", "gaze_highlight"]),
  ],
  delighted: [
    familyBeat(1, "1,-3,1,-6", ["gaze", "brow", "cheek", "gaze_highlight"], 2),
    familyBeat(2, "5,0,5,0", ["gaze", "brow", "mouth", "cheek", "gaze_highlight"], 2),
    familyBeat(3, "1,4,1,6", ["gaze", "mouth", "cheek", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "cheek", "gaze_highlight"]),
  ],
  bashful: [
    familyBeat(1, "1,4,1,6", ["gaze", "brow", "gaze_highlight"], 2),
    familyBeat(2, "-2,0,-6,0", ["gaze", "mouth", "cheek", "gaze_highlight"]),
    familyBeat(3, "1,-3,1,-6", ["gaze", "mouth", "cheek", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "mouth", "gaze_highlight"]),
  ],
  thoughtful: [
    familyBeat(1, "1,-3,1,-6", ["gaze", "brow", "gaze_highlight"]),
    familyBeat(2, "-2,0,-6,0", ["gaze", "brow", "mouth", "gaze_highlight"]),
    familyBeat(3, "5,0,5,0", ["gaze", "brow", "cheek", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "mouth", "gaze_highlight"]),
  ],
  focused: [
    familyBeat(1, "5,0,5,0", ["gaze", "brow", "gaze_highlight"]),
    familyBeat(2, "1,-3,1,-6", ["gaze", "brow", "mouth", "gaze_highlight"]),
    familyBeat(3, "-2,0,-6,0", ["gaze", "cheek", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "mouth", "gaze_highlight"]),
  ],
  alert: [
    familyBeat(1, "-2,0,-6,0", ["gaze", "brow", "gaze_highlight"]),
    familyBeat(2, "1,4,1,6", ["gaze", "brow", "mouth", "gaze_highlight"]),
    familyBeat(3, "5,0,5,0", ["gaze", "brow", "cheek", "gaze_highlight"]),
    familyBeat(4, "0,0,0,0", ["gaze", "brow", "mouth", "gaze_highlight"]),
  ],
};
for (const plan of FAMILY_PLANS) plan.beat = NON_BLINK_BEATS[plan.state];

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
  && initialSha256 !== THOUGHTFUL_PRE_FIX_CANONICAL_SHA256
  && initialSha256 !== COMPONENT_PRE_FIX_CANONICAL_SHA256
  && initialSha256 !== SUCCESSOR_CANONICAL_SHA256
  && initialSha256 !== COMP_REQ_543_PREVIEW_SHA256
  && initialSha256 !== CURRENT_DYNAMIC_PAGE_SHA256
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
      cycle_steps: 10,
      active_steps: [1, 3, 5, 7, 8],
      baseline_return_step: 9,
      first_nonbaseline_max_ms: 960,
      repeat_quiet_steps: 1,
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
      changed_frames_per_beat: 5,
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
      first_beat_max_ms: 960,
      max_changed_frames: 5,
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
}

const familyRuntime = String.raw`const familyMicroBasePromises=new Map();
function familyMicroPlan(storyName=overallController.state.storyName){return epaperVisualManifest.family_micro_choreography.plans.find(plan=>plan.story===storyName)||null}
function familyMicroSpec(plan,step){const normalized=((Number(step)||0)%epaperVisualManifest.idle_glint.cycle_steps+epaperVisualManifest.idle_glint.cycle_steps)%epaperVisualManifest.idle_glint.cycle_steps,beatIndex=epaperVisualManifest.idle_glint.active_steps.indexOf(normalized),beat=beatIndex>=0?plan.beat[beatIndex]:null;return{normalized,frameIndex:beat?beat.frame:plan.baseline_frame,key:beat?beat.gaze:epaperVisualManifest.idle_glint.baseline_key,components:beat?[...beat.components]:[],maxStepPx:beat?beat.max_step_px:0,transplants:beat?.transplants?.map(item=>({...item,rect:[...item.rect]}))||[],shifts:beat?.shifts?.map(item=>({...item,rect:[...item.rect],delta:[...item.delta]}))||[],phase:beat?'micro_'+(beatIndex+1):(normalized===epaperVisualManifest.idle_glint.baseline_return_step?'baseline_return':'quiet_hold')}}
function familyMicroPreparedBase(frame,spec){if(!spec.transplants.length&&!spec.shifts.length)return touchGazeClearedBase(frame,'');const source=frame?.touch_base||frame?.src;if(!source)return Promise.resolve(null);const cacheKey=JSON.stringify([source,spec.transplants,spec.shifts]);if(!familyMicroBasePromises.has(cacheKey)){const transplantFrames=spec.transplants.map(item=>storyByName.get(item.story)?.frames[item.frame]),sources=[source,...transplantFrames.map(item=>item?.touch_base||item?.src)];familyMicroBasePromises.set(cacheKey,Promise.all(sources.map(item=>item?touchGazeImage(cached(item)):Promise.resolve(null))).then(images=>{if(images.some(item=>!item))return null;const canvas=document.createElement('canvas');canvas.width=canvas.height=200;const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;context.fillStyle='#fff';context.fillRect(0,0,200,200);context.drawImage(images[0],0,0);spec.transplants.forEach((item,index)=>{const[x,y,width,height]=item.rect;context.fillStyle='#fff';context.fillRect(x,y,width,height);context.drawImage(images[index+1],x,y,width,height,x,y,width,height)});spec.shifts.forEach(item=>{const[x,y,width,height]=item.rect,[dx,dy]=item.delta,temp=document.createElement('canvas');temp.width=width;temp.height=height;const tempContext=temp.getContext('2d');tempContext.imageSmoothingEnabled=false;tempContext.drawImage(canvas,x,y,width,height,0,0,width,height);context.fillStyle='#fff';context.fillRect(x,y,width,height);context.drawImage(temp,x+dx,y+dy)});return canvas.toDataURL('image/png')}))}return familyMicroBasePromises.get(cacheKey)}
async function presentFamilyMicroSpec(plan,spec,source){const story=storyByName.get(plan.story),frame=story?.frames[spec.frameIndex];if(!frame||!touchData.overlays[spec.key])return false;const state=overallController.state,request=++idleGlintState.request,epoch=++gazeEpoch,stateRequest=state.request,offset=[0,0],[baseSrc,overlayImage]=await Promise.all([familyMicroPreparedBase(frame,spec),touchGazeImage(cached(touchData.overlays[spec.key]))]);if(!baseSrc||!overlayImage||request!==idleGlintState.request||epoch!==gazeEpoch||interactionMode!=='expression'||!overallStage.isConnected||state.storyName!==plan.story||state.request!==stateRequest)return false;await touchGazeImage(baseSrc);if(request!==idleGlintState.request||epoch!==gazeEpoch||interactionMode!=='expression'||state.storyName!==plan.story||state.request!==stateRequest)return false;clearTimeout(state.timer);state.timer=0;state.touching=true;state.activeFrame=frame;state.activeFrameIndex=spec.frameIndex;state.activeBaseSrc=frame.touch_base||frame.src;state.activeFrameStartedAt=performance.now();state.activeFrameDurationMs=epaperVisualManifest.cadence_ms;state.pausedRemainingMs=epaperVisualManifest.cadence_ms;state.request++;state.gazeRequest++;state.refreshRequestCount++;overallFrame.dataset.gazeCleared='true';overallFrame.src=baseSrc;overallGaze.style.transform='translate('+offset[0]+'px,'+offset[1]+'px)';overallGaze.src=cached(touchData.overlays[spec.key]);overallFrame.hidden=false;overallGaze.hidden=false;overallStaging.hidden=true;idleGlintState.currentKey=spec.key;idleGlintState.currentFrameSrc=frame.src+'|'+sha256LikeMicroSpec(spec);idleGlintState.family=plan.state;lastInteraction=source;return true}
function sha256LikeMicroSpec(spec){return JSON.stringify([spec.frameIndex,spec.transplants,spec.shifts])}
const blinkTimelineState={timer:0,active:false,phase:0,interval_index:0,next_due_at:0,deferred:0,trace:[],interrupted:0};
function blinkEligible(){return interactionMode==='expression'&&!gesture&&!pendingTapPoint&&!touchStoryPaused&&!naturalState.bridge&&naturalState.modeOverride==='none'&&!recordingState.active&&!blinkTimelineState.active&&!!familyMicroPlan()}
function deferBlink(reason){if(blinkTimelineState.timer)clearTimeout(blinkTimelineState.timer);blinkTimelineState.timer=0;if(blinkTimelineState.active){blinkTimelineState.active=false;blinkTimelineState.interrupted++}if(reason!=='test_freeze'){blinkTimelineState.deferred++;blinkTimelineState.next_due_at=performance.now()+epaperVisualManifest.blink.minimum_interval_ms}}
function familyBlinkSpec(plan,phase){const calm=storyByName.get(epaperVisualManifest.blink.story),frameIndex=epaperVisualManifest.blink.ordered_frame_indices[phase],frame=calm?.frames[frameIndex],eyeRects=[{story:epaperVisualManifest.blink.story,frame:frameIndex,rect:[38,108,44,52]},{story:epaperVisualManifest.blink.story,frame:frameIndex,rect:[120,108,44,52]}];return{normalized:0,frameIndex:plan.baseline_frame,key:idleGlintState.currentKey||epaperVisualManifest.idle_glint.baseline_key,components:['blink','eyelid'],maxStepPx:1,transplants:eyeRects,shifts:[],phase:['close','closed','reopen','hold'][phase],blink_frame:frame?.src||null}}
async function commitBlinkPhase(plan,phase){const spec=familyBlinkSpec(plan,phase),ok=await presentFamilyMicroSpec(plan,spec,'blink_timeline');if(ok)blinkTimelineState.trace.push({phase:spec.phase,frame:spec.blink_frame,elapsed_ms:phase*epaperVisualManifest.cadence_ms,committed_1bpp:true});return ok}
function scheduleBlinkTimeline(){if(blinkTimelineState.timer||blinkTimelineState.active||!familyMicroPlan())return;const now=performance.now(),delay=Math.max(0,(blinkTimelineState.next_due_at||now+epaperVisualManifest.blink.minimum_interval_ms)-now);blinkTimelineState.timer=setTimeout(async()=>{blinkTimelineState.timer=0;if(!blinkEligible()){blinkTimelineState.next_due_at=performance.now()+epaperVisualManifest.blink.minimum_interval_ms;scheduleBlinkTimeline();return}const plan=familyMicroPlan();blinkTimelineState.active=true;blinkTimelineState.phase=0;clearTimeout(idleGlintState.timer);idleGlintState.timer=0;await commitBlinkPhase(plan,0);const advance=async()=>{if(!blinkTimelineState.active)return;blinkTimelineState.phase++;if(blinkTimelineState.phase>=epaperVisualManifest.blink.ordered_frame_indices.length){blinkTimelineState.active=false;blinkTimelineState.next_due_at=performance.now()+epaperVisualManifest.blink.interval_sequence_ms[blinkTimelineState.interval_index++%epaperVisualManifest.blink.interval_sequence_ms.length];await resumeFamilyMicroBaseline('blink_reopen');return}blinkTimelineState.timer=setTimeout(async()=>{blinkTimelineState.timer=0;await commitBlinkPhase(plan,blinkTimelineState.phase);advance()},epaperVisualManifest.cadence_ms)};advance()},delay)}
function idleGlintEligible(){return interactionMode==='expression'&&!gesture&&!pendingTapPoint&&!touchStoryPaused&&!naturalState.bridge&&naturalState.modeOverride==='none'&&!blinkTimelineState.active&&overallController.state.activeFrame&&!overallFrame.hidden&&!!familyMicroPlan()}
function stopIdleGlint(reason='stop'){if(idleGlintState.timer)clearTimeout(idleGlintState.timer);idleGlintState.timer=0;idleGlintState.active=false;idleGlintState.request++;gazeEpoch++;if(reason!=='test_freeze'){idleGlintState.interruptions++;deferBlink(reason)}}
async function commitIdleGlintStep(step,source='scheduler'){const plan=familyMicroPlan();if(!plan)return null;const spec=familyMicroSpec(plan,step),frame=storyByName.get(plan.story)?.frames[spec.frameIndex],frameIdentity=frame?.src+'|'+sha256LikeMicroSpec(spec),previousKey=idleGlintState.currentKey,previousFrame=idleGlintState.currentFrameSrc,changed=spec.key!==previousKey||frameIdentity!==previousFrame;idleGlintState.step=spec.normalized;if(changed){if(!await presentFamilyMicroSpec(plan,spec,source))return null;idleGlintState.refreshRequests++}else idleGlintState.unchangedSteps++;const row={sequence:idleGlintState.trace.length+1,cycle:idleGlintState.cycle,step:spec.normalized,family:plan.state,story:plan.story,phase:spec.phase,frame:frame?.src||null,frame_identity:frameIdentity,frame_index:spec.frameIndex,key:spec.key,previous_key:previousKey,previous_frame:previousFrame,changed,refresh_requested:changed,components:spec.components,max_component_step_px:spec.maxStepPx,transplant_count:spec.transplants.length,shift_count:spec.shifts.length,source};idleGlintState.trace.push(row);if(idleGlintState.trace.length>300)idleGlintState.trace.shift();return row}
function scheduleIdleGlint(){if(!idleGlintEligible()||idleGlintState.timer)return;idleGlintState.active=true;idleGlintState.timer=setTimeout(async()=>{idleGlintState.timer=0;if(!idleGlintEligible()){idleGlintState.active=false;return}const next=(idleGlintState.step+1)%epaperVisualManifest.idle_glint.cycle_steps;if(next===0)idleGlintState.cycle++;await commitIdleGlintStep(next);scheduleIdleGlint()},epaperVisualManifest.cadence_ms)}
async function resumeFamilyMicroBaseline(reason){const plan=familyMicroPlan();if(!plan||!idleGlintEligible())return false;const spec=familyMicroSpec(plan,0),frame=storyByName.get(plan.story)?.frames[spec.frameIndex],identity=frame?.src+'|'+sha256LikeMicroSpec(spec),needsRestore=idleGlintState.currentKey!==spec.key||idleGlintState.currentFrameSrc!==identity;if(needsRestore&&!await presentFamilyMicroSpec(plan,spec,'resume_'+reason))return false;idleGlintState.step=0;idleGlintState.active=true;scheduleIdleGlint();scheduleBlinkTimeline();return true}
window.__interruptEpaperIdleGlint=reason=>{stopIdleGlint(reason);idleGlintState.step=0};
window.__resumeEpaperIdleGlint=reason=>{const eligible=idleGlintEligible();if(eligible)resumeFamilyMicroBaseline(reason);return{reason,active:eligible}};
window.__epaperFreezeIdleGlintStep=async step=>{stopIdleGlint('test_freeze');return commitIdleGlintStep(step,'test_freeze')};
window.__resumeEpaperIdleGlintScheduler=()=>{idleGlintState.active=true;scheduleIdleGlint();return idleGlintState.active};
window.__resetEpaperIdleGlintRealClock=async()=>{stopIdleGlint('test_freeze');idleGlintState.step=0;idleGlintState.cycle=0;idleGlintState.trace=[];idleGlintState.refreshRequests=0;idleGlintState.unchangedSteps=0;blinkTimelineState.active=false;blinkTimelineState.phase=0;blinkTimelineState.trace=[];blinkTimelineState.deferred=0;blinkTimelineState.next_due_at=performance.now()+epaperVisualManifest.blink.minimum_interval_ms;const plan=familyMicroPlan();if(!plan)return{eligible:false,started:false,cadence_ms:epaperVisualManifest.cadence_ms};const baseline=familyMicroSpec(plan,0);if(!await presentFamilyMicroSpec(plan,baseline,'idle_real_clock_reset'))return{eligible:false,started:false,cadence_ms:epaperVisualManifest.cadence_ms};scheduleIdleGlint();scheduleBlinkTimeline();return{eligible:idleGlintEligible(),started:idleGlintState.active,cadence_ms:epaperVisualManifest.cadence_ms,family:plan.state}};
window.__setFamilyMicroChoreographyFamily=async family=>{const plan=epaperVisualManifest.family_micro_choreography.plans.find(item=>item.state===family);if(!plan)throw new Error('unknown family '+family);stopIdleGlint('test_freeze');naturalEpoch++;naturalClearTimer();naturalState.bridge=null;naturalState.coalescedPending=null;naturalState.pendingOrient=null;naturalState.baseAffect=plan.state;naturalState.reactionPhase='steady';naturalState.modeOverride='none';naturalState.gazeTarget={x:100,y:100,key:epaperVisualManifest.idle_glint.baseline_key};const state=overallController.state,story=storyByName.get(plan.story),baseline=familyMicroSpec(plan,0);clearTimeout(state.timer);state.timer=0;state.touching=true;state.storyName=plan.story;state.frameIndex=plan.baseline_frame;state.activeFrame=story.frames[plan.baseline_frame];state.activeFrameIndex=plan.baseline_frame;state.activeBaseSrc=state.activeFrame.touch_base||state.activeFrame.src;state.request++;idleGlintState.currentFrameSrc='';idleGlintState.currentKey='';idleGlintState.family=plan.state;const presented=await presentFamilyMicroSpec(plan,baseline,'family_test_select');renderExpressionStateView({kind:'family_test_select',family:plan.state});return{family:plan.state,story:plan.story,presented,baseline_frame:plan.baseline_frame}};
window.__familyMicroChoreographyState=()=>({manifest:naturalClone(epaperVisualManifest.family_micro_choreography),family:familyMicroPlan()?.state||null,active:idleGlintState.active,step:idleGlintState.step,cycle:idleGlintState.cycle,current_key:idleGlintState.currentKey,current_frame:idleGlintState.currentFrameSrc,refresh_requests:idleGlintState.refreshRequests,unchanged_steps:idleGlintState.unchangedSteps,interruptions:idleGlintState.interruptions,trace:idleGlintState.trace.map(row=>({...row,components:[...row.components]})),blink:{active:blinkTimelineState.active,phase:blinkTimelineState.phase,deferred:blinkTimelineState.deferred,interrupted:blinkTimelineState.interrupted,trace:blinkTimelineState.trace.map(row=>({...row}))}});
`;

if (initialSha256 === PREDECESSOR_CANONICAL_SHA256) {
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

if (initialSha256 === THOUGHTFUL_PRE_FIX_CANONICAL_SHA256) {
  page = replaceExact(
    page,
    '"gaze":"0,0,-1,0","components":["brow","gaze_highlight"]',
    '"gaze":"0,0,0,0","components":["brow","gaze_highlight"]',
    "thoughtful registered first gaze",
  );
  page = replaceExact(
    page,
    '"gaze":"-1,-1,-1,-1","components":["brow","mouth","gaze_highlight"]',
    '"gaze":"0,-1,0,-1","components":["brow","mouth","gaze_highlight"]',
    "thoughtful registered second gaze",
  );
}

if (
  initialSha256 === COMPONENT_PRE_FIX_CANONICAL_SHA256
  || initialSha256 === CURRENT_DYNAMIC_PAGE_SHA256
) {
  page = page.replace(
    /(<script id="companion-epaper-visual-manifest" type="application\/json">)(.*?)(<\/script>)/s,
    (_match, prefix, rawManifest, suffix) => {
      const manifest = JSON.parse(rawManifest);
      manifest.family_micro_choreography.plans = FAMILY_PLANS;
      return `${prefix}${JSON.stringify(manifest)}${suffix}`;
    },
  );
  page = replaceRange(
    page,
    "function familyMicroPlan(",
    "window.__familyMicroChoreographyState=()=>",
    familyRuntime.trimEnd(),
    "registered component micro runtime",
  );
}

// The successor page is a generated single-line artifact. Keep its live manifest
// and runtime aligned when applying this source to that already-bound candidate.
page = page.replace(
  '"cycle_steps":12,"active_steps":[2,3],"baseline_return_step":4,"first_nonbaseline_max_ms":960,"repeat_quiet_steps":9',
  '"cycle_steps":10,"active_steps":[2,4,6,8],"baseline_return_step":9,"first_nonbaseline_max_ms":960,"repeat_quiet_steps":1',
);
page = page.replace(
  '"cycle_steps":10,"active_steps":[1,3,5,7,8],"baseline_return_step":9,"first_nonbaseline_max_ms":960,"repeat_quiet_steps":1',
  '"cycle_steps":10,"active_steps":[2,4,6,8],"baseline_return_step":9,"first_nonbaseline_max_ms":960,"repeat_quiet_steps":1',
);
page = page.replace('"changed_frames_per_beat":3,"interrupt_policy"', '"changed_frames_per_beat":5,"interrupt_policy"');
page = page.replace('"changed_frames_per_beat":5,"interrupt_policy"', '"changed_frames_per_beat":4,"interrupt_policy"');
page = page.replace('"first_beat_max_ms":2880,"max_changed_frames":3', '"first_beat_max_ms":960,"max_changed_frames":5');
page = page.replace(
  'beat=beatIndex>=0?plan.beat[(beatIndex+1)%plan.beat.length]:null',
  'beat=beatIndex>=0?plan.beat[beatIndex]:null',
);
page = page.replace(
  'beat=beatIndex>=0?plan.beat[beatIndex%plan.beat.length]:null',
  'beat=beatIndex>=0?plan.beat[beatIndex]:null',
);
page = page.replace(
  '"blink":{"story":"calm_presence","ordered_frame_indices":[1,2,3,4],"reopen_frame_index":4,"registered_event_only":true}',
  '"blink":{"story":"calm_presence","ordered_frame_indices":[1,2,3,4],"reopen_frame_index":4,"registered_event_only":true,"mode":"sparse_deterministic","minimum_interval_ms":8000,"interval_sequence_ms":[8000,10000,12000],"frame_cadence_ms":480,"duration_ms":1920,"sleepy_only_settle":true}',
);
page = page.replace(
  /(?:const familyMicroBasePromises=new Map\(\);\s*){2,}/,
  "const familyMicroBasePromises=new Map();\n",
);

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
