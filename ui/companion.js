'use strict';

/* ------------------------------------------------------------------ helpers */

const $ = (q) => document.querySelector(q);
const $$ = (q) => [...document.querySelectorAll(q)];
const esc = (t) => String(t === null || t === undefined ? '' : t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const api = () => (window.pywebview && window.pywebview.api) || null;
const call = (name, ...a) => { const x = api(); return x && x[name] ? x[name](...a) : Promise.resolve(null); };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

const S = {
  catalog: null, d: null, version: -1, dataVersion: -1, page: 'status',
  settings: {}, booted: false, matCounts: {}, saves: [], selectedSave: '', rebuildStarted: false,
  inv: { cat: '', filter: '', sel: null },
  armor: { slot: '', owned: true, set: '', filter: '', sel: null },
  map: { layer: 'surface', zoom: 1, tx: 0, ty: 0, cats: new Set(), found: 'found', search: '', sel: null,
         reveal: false, medals: true, path: false, pathData: null, pathFor: -1, pathLoading: false,
         fitted: false, layerSet: false, pending: null, raf: 0, drag: null,
         iconImages: {}, activeReveal: null, activeRevealFor: null, pingUntil: 0, pingTimer: 0,
         sources: [], sourceMat: null, sourceSel: null, sourceTotal: 0,
         miniDrag: false, miniRAF: 0 },
  progress: { cat: 'overview', mode: 'found', filter: '' },
  comp: { group: '', state: 'TakePhoto', filter: '', sel: null },
  cook: { filter: '', fx: '', sort: 'hearts', sel: null, all: false, allRows: null, allFor: -1 },
  modal: false,
  sourceModal: false,
  sourceActor: null,
};

/* Drawn glyphs, 24x24, one stroke weight. Original drawings, no game art. */
const ICONS = {
  meat: '<ellipse cx="14.2" cy="9.8" rx="6.6" ry="5.4" transform="rotate(-38 14.2 9.8)"/><path d="M11.5 10.5c.8-1.8 2.4-3 4.3-3.2"/><path d="M9.6 14.4L5.6 18.4"/><circle cx="4.6" cy="17.6" r="1.5"/><circle cx="6.4" cy="19.4" r="1.5"/>',
  fish: '<path d="M2.8 12c3.1-4.6 8.6-6.3 13.2-3.4L20.8 5v14l-4.8-3.6C11.4 18.3 5.9 16.6 2.8 12z"/><circle cx="7.6" cy="11.2" r=".9"/><path d="M11.2 9.4c.9 1.6.9 3.6 0 5.2"/>',
  mushroom: '<path d="M3.4 12.2C3.8 7.3 7.6 4 12 4s8.2 3.3 8.6 8.2z"/><path d="M9.6 12.2l-.6 6.3a3 3 0 0 0 6 0l-.6-6.3"/><circle cx="9" cy="8.3" r="1.1"/><circle cx="14.6" cy="7.4" r=".8"/><circle cx="16.2" cy="10" r=".7"/>',
  fruit: '<path d="M12 7.6c-1.7-1.4-7.2-1.9-7.2 4.4 0 4.3 2.9 8.6 5 8.6.9 0 1.3-.5 2.2-.5s1.3.5 2.2.5c2.1 0 5-4.3 5-8.6 0-6.3-5.5-5.8-7.2-4.4z"/><path d="M12 7.6c0-2 .7-3.4 2.3-4.2"/><path d="M12.6 5.4c1.6-.9 3.6-.6 4.6.6-1.4 1-3.3 1-4.6-.6z"/>',
  plant: '<path d="M12 21V9.5"/><path d="M12 14.2c-4.2 0-6.6-2.7-6.6-6.6 3.9 0 6.6 2.4 6.6 6.6z"/><path d="M12 11.4c0-3.9 2.6-6.6 6.6-6.6 0 3.9-2.7 6.6-6.6 6.6z"/><path d="M8.5 21h7"/>',
  spice: '<path d="M8.6 7.4c-3.1 2.3-4 7.7-1.8 12 .6 1.2 2 1.3 2.7.3 2.6-3.6 5.6-7.4 6.9-10.6.6-1.6-.8-3.1-2.5-2.8z"/><path d="M14 6.2c-.1-1.6.9-2.9 2.5-3.3"/><path d="M8.6 7.4l5.3-1.2"/>',
  insect: '<ellipse cx="12" cy="13.6" rx="4.6" ry="6"/><circle cx="12" cy="5.8" r="2"/><path d="M12 7.8v11.6"/><path d="M7.6 11.2L4 9.4M7.4 14.4H3.6M7.8 17.4l-3.2 2M16.4 11.2L20 9.4M16.6 14.4h3.8M16.2 17.4l3.2 2"/><path d="M10.8 4.2L9.4 2.6M13.2 4.2l1.4-1.6"/>',
  enemy: '<path d="M5.4 20.4c-.6-7.2 2.7-13.4 13.8-16.8-3.6 3.9-5.1 8.6-4.1 16.8z"/><path d="M7.8 16.6c2.2-.5 4.4-.4 6.6.2M9.2 12.4c1.8-.4 3.5-.2 5.2.4M11.4 8.6c1.2-.3 2.6-.1 3.8.4"/>',
  golem: '<path d="M12 3.2l7.6 4.4v8.8L12 20.8l-7.6-4.4V7.6z"/><circle cx="12" cy="12" r="3.2"/><path d="M12 3.2v5.6M12 15.2v5.6"/>',
  ore: '<path d="M7.4 4.4h9.2l4 5L12 20 3.4 9.4z"/><path d="M3.4 9.4h17.2M9.6 4.4L8.2 9.4 12 20l3.8-10.6-1.4-5"/>',
  pouch: '<path d="M8 7.2h8l3.2 9.6a3 3 0 0 1-2.9 3.9H7.7a3 3 0 0 1-2.9-3.9z"/><path d="M8 7.2L6.6 3.6h10.8L16 7.2"/><path d="M9.4 11.4c1.6.8 3.6.8 5.2 0"/>',
  elixir: '<path d="M9.8 3.4h4.4M10.4 3.4v4.4L5.9 15a4.4 4.4 0 0 0 3.8 6.6h4.6a4.4 4.4 0 0 0 3.8-6.6l-4.5-7.2V3.4"/><path d="M7.4 14.2c3 1.4 6.2-1 9.2.2"/>',
  pot: '<path d="M4 11h16v2.5a6 6 0 0 1-6 6h-4a6 6 0 0 1-6-6z"/><path d="M2.5 11h19M9 5.5c0 1.2 1 1.6 1 2.8M13 4.5c0 1.3 1 1.7 1 3"/><path d="M8 19.5l-1 2M16 19.5l1 2"/>',
  sword: '<path d="M14.8 3.8l5.4 1.4-1.4 5.4L9 19.4l-3.4-3.4z"/><path d="M6.2 16.2l1.6 1.6M4 20l2.2-2.2"/>',
  bow: '<path d="M5 19c-3-4.6-3-9.4 0-14"/><path d="M5 19L19 5M17.8 6.2l1.2-1.2-1.2-1.2"/>',
  shield: '<path d="M12 3.5l7 2.2v5c0 4.2-2.8 7.2-7 9.8-4.2-2.6-7-5.6-7-9.8v-5z"/>',
  head: '<path d="M6.2 13.5c0-3.5 2.5-6.2 5.8-6.2s5.8 2.7 5.8 6.2c0 2.1-1.1 3.6-2.7 4.4v2.6H8.9v-2.6c-1.6-.8-2.7-2.3-2.7-4.4z"/><path d="M9.4 12.2h1M13.6 12.2h1"/>',
  body: '<path d="M8.2 4.8L12 7l3.8-2.2 3 4.4-2.6 2.1v7.4H7.8v-7.4L5.2 9.2z"/>',
  legs: '<path d="M8 4.5h8l-.8 7.5-1 7.5h-2.1l-.1-6.2-.1 6.2H9.8l-1-7.5z"/>',
  rupee: '<path d="M12 3.2l6 4.4v8.8L12 20.8 6 16.4V7.6z"/><path d="M12 7.4v9.2M9.4 10.2h4.2a1.8 1.8 0 0 1 0 3.6H9.4"/>',
  stamina: '<path d="M13.5 3.5L6 13.4h4.3L9.8 20.5l7.7-10.1h-4.4z"/>',
  battery: '<rect x="4" y="8" width="14" height="9" rx="2"/><path d="M18 11h2v3h-2M7 11h4v3H7"/>',
  sun: '<circle cx="12" cy="12" r="3.4"/><path d="M12 3.5v2.2M12 18.3v2.2M3.5 12h2.2M18.3 12h2.2M5.9 5.9l1.6 1.6M16.5 16.5l1.6 1.6M18.1 5.9l-1.6 1.6M7.5 16.5l-1.6 1.6"/>',
  map: '<path d="M3.5 5.8l5.5-2 6 2 5.5-2v14.4l-5.5 2-6-2-5.5 2z"/><path d="M9 3.8v14.4M15 5.8v14.4"/>',
  check: '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.2l2.6 2.6L16.5 9"/>',
  book: '<path d="M4 5.2c2.8-1.2 5.2-1.2 8 0 2.8-1.2 5.2-1.2 8 0v13.2c-2.8-1.2-5.2-1.2-8 0-2.8-1.2-5.2-1.2-8 0z"/><path d="M12 5.2v13.2"/>',
  gear: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>',
};
const HEART = 'M12 20.4C6.5 16.5 2.8 13 2.8 8.9 2.8 6.2 4.9 4.1 7.5 4.1c1.9 0 3.4 1 4.5 2.6 1.1-1.6 2.6-2.6 4.5-2.6 2.6 0 4.7 2.1 4.7 4.8 0 4.1-3.7 7.6-9.2 11.5z';
const FX = {
  LifeMaxUp: '#f1c84a', StaminaRecover: '#9bd46f', ExStaminaMaxUp: '#d9e66c', AllSpeed: '#6fc9ea',
  AttackUp: '#ee7b52', AttackUpCold: '#ee7b52', AttackUpHot: '#ee7b52', AttackUpThunderstorm: '#ee7b52',
  DefenseUp: '#8eaad8', QuietnessUp: '#ab90e2', ResistCold: '#f0924c', ResistHot: '#86d4ec',
  ResistElectric: '#f3de58', ResistBurn: '#e8604f', LifeRepair: '#f6b24c', LightEmission: '#f5ee9e',
  NotSlippy: '#b9c66d', MiasmaGuard: '#cf94e2', SwimSpeedUp: '#62b9e2', SnowMoveUp: '#c7e3f0', SandMoveUp: '#e3c48e',
  ClimbSpeedUp: '#a6cf7a', DivingMobilityUp: '#8fd0d8',
};
const EFFECT_DESC = {
  AttackUp: 'Raises attack power by 20% at Lv. 1, 30% at Lv. 2, and 50% at Lv. 3.',
  AttackUpCold: 'Adds ice damage to charge attacks and combo finishers in cold weather.',
  AttackUpHot: 'Adds fire damage to charge attacks and combo finishers in hot weather.',
  AttackUpThunderstorm: 'Adds electric damage to charge attacks and combo finishers in storms.',
  AttackUpBone: 'Bone weapons deal 80% more damage.',
  DefenseUp: 'Adds 4 defense at Lv. 1, 12 at Lv. 2, and 24 at Lv. 3.',
  ResistCold: 'Endures cold down to -10 C at Lv. 1, and any cold at Lv. 2.',
  ResistHot: 'Endures heat up to 50 C at Lv. 1, and any heat at Lv. 2.',
  ResistElectric: 'Takes one third less shock damage at Lv. 1, two thirds less at Lv. 2, and none at Lv. 3.',
  ResistBurn: 'Endures some scorching heat at Lv. 1, and any scorching heat at Lv. 2.',
  ResistFreeze: 'Prevents ice damage and being frozen.',
  ResitLightning: 'Prevents lightning damage and knockback.',
  NoBurning: 'Prevents fire damage and catching fire.',
  MiasmaGuard: 'Reduces gloom damage by 1 heart per level.',
  MiasmaDefenseUp: 'Blocks 4 gloom hearts.',
  AllSpeed: 'Move 10% faster at Lv. 1, 20% at Lv. 2, and 30% at Lv. 3.',
  QuietnessUp: 'Produces 20% less sound at Lv. 1, 40% at Lv. 2, and 70% at Lv. 3.',
  SwimSpeedUp: 'Swims 30% faster at Lv. 1, 60% at Lv. 2, and twice as fast at Lv. 3.',
  ClimbSpeedUp: 'Climbs 20% faster at Lv. 1, 30% at Lv. 2, and 40% at Lv. 3.',
  ClimbSpeedUpOnlyHorizontaly: 'Climbs 70% faster horizontally.',
  ClimbWaterfall: 'Allows swimming up waterfalls.',
  DivingMobilityUp: 'Improves skydive mobility.',
  SandMoveUp: 'Moves at normal speed on sand.',
  SnowMoveUp: 'Moves at normal speed on snow.',
  NotSlippy: 'Never slips while climbing in rain or on ice.',
  NightMoveSpeedUp: 'Moves 20% faster at night.',
  LightEmission: 'Glows in the dark.',
  LightFootprint: 'Leaves glowing footprints in the Depths every 5 seconds.',
  DecreaseSwimStamina: 'Uses 75% less stamina for swim dashes.',
  DecreaseWallJumpStamina: 'Uses 50% less stamina for climbing jumps.',
  DecreaseChargeAttackStamina: 'Uses 50% less stamina for charge attacks.',
  ChargePowerUpCold: 'Charge attacks charge twice as fast in cold weather.',
  ChargePowerUpHot: 'Charge attacks charge twice as fast in hot weather.',
  ChargePowerUpThunderstorm: 'Charge attacks charge twice as fast in storms.',
  ZonauEnergyHealUp: 'Zonai devices recover energy 50% faster.',
  NoFallDamage: 'Prevents fall damage.',
  SwordBeamUp: 'Master Sword beams deal 50% more damage.',
  StalDisguise: 'Stal enemies do not appear at night and Stalnox ignore Link.',
  EmitTerror: 'Terrifies NPCs.',
  EnableUseSwordBeam: 'Allows Master Sword beams without full hearts.',
  SpinAttack: 'Allows a spin attack while swimming.',
  Moisturizing: 'Keeps Link wet for longer after touching water.',
  RupeeGuard: 'Converts damage into rupees.',
  RupeeGuardRate: 'Converts damage into rupees.',
  MaskBokoblin: 'Bokoblins do not attack unless provoked.',
  MaskMoriblin: 'Moblins do not attack unless provoked.',
  MaskLizalfos: 'Lizalfos do not attack unless provoked.',
  MaskLynel: 'Lynels ignore Link at close range for 30 seconds.',
  MaskHorablin: 'Horriblins do not attack unless provoked.',
  MaskAll: 'Monsters do not attack unless provoked.',
  DecreaseZonauEnergy: 'Zonai devices use less energy.',
  NightGlow: 'Glows at night.',
  NoSlip: 'Never slips while climbing in rain or on ice.',
  SoulPowerUpFire: "Increases Yunobo's attack power.",
  SoulPowerUpLightning: "Increases Riju's attack power.",
  SoulPowerUpSpirit: "Increases Mineru's attack power.",
  SoulPowerUpWater: "Increases Sidon's attack power.",
  SoulPowerUpWind: "Increases Tulin's attack power.",
  WakeWind: "Improves Tulin's gust.",
  YigaDisguise: 'Yiga Clan members do not attack.',
};
function effectDesc(effect) {
  return EFFECT_DESC[(effect && effect.type) || effect] || '';
}
const EFFECT_AMOUNT = {
  AttackUp: ['', '+20% attack', '+30% attack', '+50% attack'],
  DefenseUp: ['', '+4 defense', '+12 defense', '+24 defense'],
  QuietnessUp: ['', '20% less sound', '40% less sound', '70% less sound'],
  AllSpeed: ['', '10% faster', '20% faster', '30% faster'],
  ClimbSpeedUp: ['', '20% faster climbing', '30% faster climbing', '40% faster climbing'],
  SwimSpeedUp: ['', '30% faster swimming', '60% faster swimming', '2x swim speed'],
  DivingMobilityUp: ['', '1.5x skydive mobility', '2x skydive mobility', '2.5x skydive mobility'],
  MiasmaGuard: ['', '1 gloom heart', '2 gloom hearts', '3 gloom hearts'],
  MiasmaDefenseUp: ['', '4 gloom hearts', '4 gloom hearts', '4 gloom hearts'],
  ResistCold: ['', 'endure -10 C', 'endure any cold', 'endure any cold'],
  ResistHot: ['', 'endure 50 C', 'endure any heat', 'endure any heat'],
  ResistBurn: ['', 'endure some scorching heat', 'endure any scorching heat', 'endure any scorching heat'],
  ResistElectric: ['', '1/3 less shock damage', '2/3 less shock damage', 'no shock damage'],
  LightEmission: ['', 'glow 10', 'glow 30', 'glow 60'],
  NotSlippy: ['', 'slip every 6 seconds', 'slip every 8 seconds', 'slip every 10 seconds'],
  AttackUpBone: ['', '80% more bone weapon attack', '80% more bone weapon attack', '80% more bone weapon attack'],
  SwordBeamUp: ['', '50% more beam damage', '50% more beam damage', '50% more beam damage'],
  DecreaseSwimStamina: ['', '75% less swim dash stamina', '75% less swim dash stamina', '75% less swim dash stamina'],
  DecreaseWallJumpStamina: ['', '50% less climbing jump stamina', '50% less climbing jump stamina', '50% less climbing jump stamina'],
  DecreaseChargeAttackStamina: ['', '50% less charge attack stamina', '50% less charge attack stamina', '50% less charge attack stamina'],
  ChargePowerUpCold: ['', 'charge twice as fast in cold', 'charge twice as fast in cold', 'charge twice as fast in cold'],
  ChargePowerUpHot: ['', 'charge twice as fast in heat', 'charge twice as fast in heat', 'charge twice as fast in heat'],
  ChargePowerUpThunderstorm: ['', 'charge twice as fast in storms', 'charge twice as fast in storms', 'charge twice as fast in storms'],
  ZonauEnergyHealUp: ['', '50% faster energy recharge', '50% faster energy recharge', '50% faster energy recharge'],
  NightMoveSpeedUp: ['', '20% faster at night', '20% faster at night', '20% faster at night'],
  NoBurning: ['', 'fireproof', 'fireproof', 'fireproof'],
  ResistFreeze: ['', 'unfreezable', 'unfreezable', 'unfreezable'],
  NoFallDamage: ['', 'no fall damage', 'no fall damage', 'no fall damage'],
  ResitLightning: ['', 'no lightning damage', 'no lightning damage', 'no lightning damage'],
  ClimbWaterfall: ['', 'swim up waterfalls', 'swim up waterfalls', 'swim up waterfalls'],
  SpinAttack: ['', 'spin attack while swimming', 'spin attack while swimming', 'spin attack while swimming'],
  EnableUseSwordBeam: ['', 'beam without full hearts', 'beam without full hearts', 'beam without full hearts'],
};
function effectAmount(type, level) {
  const map = EFFECT_AMOUNT[type];
  if (!map) return '';
  return map[clamp(Math.round(Number(level) || 1), 0, 3)] || '';
}

const MARKS = {
  AllSpeed: ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0], SwimSpeedUp: ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0],
  ClimbSpeedUp: ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0], SnowMoveUp: ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0],
  SandMoveUp: ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0], DivingMobilityUp: ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0],
  ResistCold: ['M12 7.6v8.8M8.2 9.8l7.6 4.4M8.2 14.2l7.6-4.4', 0],
  ResistHot: ['M12 7.4c2.6 2.6 3.4 4.3 3.4 5.8a3.4 3.4 0 0 1-6.8 0c0-1.3.6-2.2 1.5-2.8 0 1 .5 1.7 1.1 1.7 0-1.6.2-3 .8-4.7z', 1],
  ResistBurn: ['M12 7.4c2.6 2.6 3.4 4.3 3.4 5.8a3.4 3.4 0 0 1-6.8 0c0-1.3.6-2.2 1.5-2.8 0 1 .5 1.7 1.1 1.7 0-1.6.2-3 .8-4.7z', 1],
  ResistElectric: ['M13.2 7l-3.7 5.6h3L11 17l3.6-5.6h-3z', 1],
  AttackUp: ['M15.6 8.4l-5.8 5.8M8.6 12.8l2.6 2.6M9.4 14.6l-1.4 1.4', 0],
  AttackUpCold: ['M15.6 8.4l-5.8 5.8M8.6 12.8l2.6 2.6M9.4 14.6l-1.4 1.4', 0],
  AttackUpHot: ['M15.6 8.4l-5.8 5.8M8.6 12.8l2.6 2.6M9.4 14.6l-1.4 1.4', 0],
  AttackUpThunderstorm: ['M15.6 8.4l-5.8 5.8M8.6 12.8l2.6 2.6M9.4 14.6l-1.4 1.4', 0],
  DefenseUp: ['M12 7.6l3.7 1.3v2.7c0 2.4-1.5 4-3.7 4.8-2.2-.8-3.7-2.4-3.7-4.8V8.9z', 1],
  StaminaRecover: ['M15.8 12a3.8 3.8 0 1 1-1.1-2.7', 0],
  ExStaminaMaxUp: ['M15.8 12a3.8 3.8 0 1 1-1.1-2.7M12 10v4M10 12h4', 0],
  QuietnessUp: ['M13.4 7.8a4.2 4.2 0 1 0 2.8 7.4 3.4 3.4 0 0 1-2.8-7.4z', 1],
  LifeMaxUp: ['M12 15.8c-2.4-1.7-4-3.2-4-5 0-1.2.9-2.1 2-2.1.8 0 1.5.4 2 1.1.5-.7 1.2-1.1 2-1.1 1.1 0 2 .9 2 2.1 0 1.8-1.6 3.3-4 5z', 1],
  LifeRepair: ['M12 15.8c-2.4-1.7-4-3.2-4-5 0-1.2.9-2.1 2-2.1.8 0 1.5.4 2 1.1.5-.7 1.2-1.1 2-1.1 1.1 0 2 .9 2 2.1 0 1.8-1.6 3.3-4 5z', 1],
  LightEmission: ['M12 9.4a2.6 2.6 0 1 1 0 5.2 2.6 2.6 0 0 1 0-5.2z', 1],
  NotSlippy: ['M9 10.5h6M9 13.5h6M10.5 9v6M13.5 9v6', 0],
  MiasmaGuard: ['M12 7.8l3.4 1.2v2.6c0 2.3-1.4 3.8-3.4 4.6-2-.8-3.4-2.3-3.4-4.6V9z', 0],
};

function icon(name, cls, color) {
  const st = color ? ` style="--fxc:${color}"` : '';
  return `<svg class="${cls || 'g'}" viewBox="0 0 24 24" aria-hidden="true"${st}>${ICONS[name] || ICONS.pouch}</svg>`;
}
function micon(name, title, cls) {
  const label = title ? ` title="${esc(title)}"` : '';
  const body = (window.MATERIAL_ICONS || {})[name] || '';
  return `<svg class="msi ${cls || ''}"${label} viewBox="0 0 24 24" aria-hidden="true" fill="currentColor" style="stroke:none">${body}</svg>`;
}
function initStaticIcons() {
  for (const el of $$('[data-micon]')) {
    const cls = el.className.replace(/\bmsi\b/g, '').trim();
    el.outerHTML = micon(el.dataset.micon, '', cls);
  }
}
function art(it, cls) {
  cls = cls || 'g';
  if (it && it.icon) return `<img class="${cls} art" src="companion_data/icons/${encodeURIComponent(it.icon)}" alt="" draggable="false" decoding="async">`;
  return icon((it && it.glyph) || 'pouch', cls, it && FX[it.effect]);
}
function mark(effect, c) {
  const m = MARKS[effect];
  if (!m) return `<path d="M12 8l4 4-4 4-4-4z" fill="${c}" stroke="none"/>`;
  return m[1] ? `<path d="${m[0]}" fill="${c}" stroke="none"/>` : `<path d="${m[0]}" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>`;
}
function sigil(effect, cls) {
  const c = FX[effect];
  if (!c) return '';
  return `<svg class="${cls || 'sig'}" viewBox="0 0 24 24" aria-hidden="true" style="stroke:${c}"><path d="M12 2.5l9.5 9.5-9.5 9.5L2.5 12z" stroke-width="2"/>${mark(effect, c)}</svg>`;
}
function heart(q, yellow) {
  const fill = q >= 4 ? `<path class="hf" d="${HEART}"/>` : q > 0 ? `<path class="hf" d="${HEART}" clip-path="url(#q${q})"/>` : '';
  return `<svg class="heart${yellow ? ' y' : ''}" viewBox="0 0 24 24" aria-hidden="true"><path class="hb" d="${HEART}"/>${fill}<path class="ho" d="${HEART}"/></svg>`;
}
function hearts(h, yellow, max) {
  let quarters = Math.round(h * 4), out = '', n = 0;
  max = max || 40;
  while (quarters > 0 && n < max) { out += heart(Math.min(4, quarters), yellow); quarters -= 4; n++; }
  return out;
}
function heartsWithMax(cur, max, yellow) {
  const total = Math.min(60, Math.ceil(Math.round(max * 4) / 4));
  const quarters = Math.round(cur * 4);
  const cells = [];
  for (let i = 0; i < total; i++) cells.push(heart(clamp(quarters - i * 4, 0, 4), yellow));
  let out = '';
  for (let i = 0; i < cells.length; i += 20) {
    out += `<div class="heart-row">${cells.slice(i, i + 20).join('')}</div>`;
  }
  return out;
}
function fmtHearts(h) {
  const whole = Math.floor(h + 1e-9), q = Math.round((h - whole) * 4);
  const frac = ['', '¼', '½', '¾', ''][q];
  const w = q === 4 ? whole + 1 : whole;
  if (!w && !frac) return '0';
  return w ? `${w}${frac ? ' ' + frac : ''}` : frac;
}
function fmtTime(s) { return s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : ''; }
function fmtNum(n) { return Number(n || 0).toLocaleString(); }
function pct(a, b) { return b ? Math.round((a / b) * 1000) / 10 : 0; }
function plural(n, one, many) { return `${n} ${n === 1 ? one : many}`; }
function ago(mtime) {
  const s = Date.now() / 1000 - mtime;
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(mtime * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
function dist3(a, b) {
  if (!a || !b) return null;
  return Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2) + Math.pow(a.z - b.z, 2));
}
function fmtDist(d) { return d === null ? '' : `${fmtNum(Math.round(d))} m`; }
function gameCoord(v) {
  const n = Math.round(Number(v) || 0);
  return `${n < 0 ? '-' : ''}${String(Math.abs(n)).padStart(4, '0')}`;
}
function fmtXYZ(x, y, z) {
  return `X ${gameCoord(x)} · Y ${gameCoord(-z)} · Z ${gameCoord(y)}`;
}
function fmtXZ(x, z) {
  return `X ${gameCoord(x)} · Y ${gameCoord(-z)}`;
}
const HEIGHT_CACHE = {};
function heightLayer(layer) {
  const all = window.MAP_HEIGHTS;
  if (!all || !all[layer]) return null;
  if (HEIGHT_CACHE[layer]) return HEIGHT_CACHE[layer];
  const raw = atob(all[layer].data || '');
  const data = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) data[i] = raw.charCodeAt(i);
  HEIGHT_CACHE[layer] = { w: all[layer].w, h: all[layer].h, min: all[layer].min, max: all[layer].max, data };
  return HEIGHT_CACHE[layer];
}
function heightAt(layer, x, z) {
  const h = heightLayer(layer);
  const m = cat().map;
  if (!h || !m) return null;
  const w = m.world;
  const px = clamp(Math.floor((x - w.x_min) / (w.x_max - w.x_min) * h.w), 0, h.w - 1);
  const py = clamp(Math.floor((z - w.z_min) / (w.z_max - w.z_min) * h.h), 0, h.h - 1);
  const v = h.data[py * h.w + px];
  return h.min + (v / 255) * (h.max - h.min);
}
function layerLabel(l) { return l === 'sky' ? 'Sky' : l === 'depths' ? 'Depths' : 'Surface'; }
function bearing(a, b) {
  if (!a || !b) return null;
  return Math.atan2(b.x - a.x, -(b.z - a.z)) * 180 / Math.PI;
}
function cardinal(deg) {
  if (deg === null) return '';
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round((((deg % 360) + 360) % 360) / 45) % 8];
}
function dirIcon(deg) {
  if (deg === null) return '';
  return `<span class="dir" style="--a:${deg.toFixed(1)}deg" title="${cardinal(deg)}">` +
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l6.5 19L12 16.8 5.5 21z"/></svg></span>`;
}
function normText(s) {
  return String(s || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
}
function editDistance(a, b) {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = cur;
  }
  return prev[b.length];
}
function fuzzyScore(query, text) {
  const q = normText(query), t = normText(text);
  if (!q) return 0;
  if (t.includes(q)) return 1000 - t.indexOf(q);
  const words = t.split(/\s+/);
  const qwords = q.split(/\s+/);
  if (qwords.length > 1 && qwords.every((w) => words.some((x) => x.startsWith(w)))) return 820;
  if (q.length >= 2) {
    let i = 0, gaps = 0, first = -1, last = -1;
    for (let j = 0; j < t.length && i < q.length; j++) {
      if (t[j] === q[i]) {
        if (first < 0) first = j;
        if (last >= 0) gaps += j - last - 1;
        last = j;
        i++;
      }
    }
    const span = last - first + 1;
    if (i === q.length && span <= q.length + 3) {
      return Math.max(240, 560 - gaps * 6 - (span - q.length) * 5);
    }
  }
  if (q.length >= 4) {
    const max = Math.max(2, Math.floor(q.length / 3));
    for (const w of words) {
      if (w.length < 3 || Math.abs(w.length - q.length) > max) continue;
      const dw = editDistance(q, w);
      if (dw <= max) return 480 - dw * 30;
    }
    const d = editDistance(q, t);
    if (d <= max) return 440 - d * 25;
  }
  return 0;
}

/* ------------------------------------------------------------------ nav/load */

const NAV = [
  ['status', 'Status', 'check'], ['inventory', 'Inventory', 'pouch'], ['armor', 'Armor', 'shield'],
  ['map', 'Map', 'map'], ['progress', 'Progress', 'check'], ['compendium', 'Compendium', 'book'],
  ['cook', 'Cooking', 'pot'],
];

function cat() { return S.catalog || {}; }
function dyn() { return S.d || {}; }
function catMeta(key) {
  for (const c of (cat().collectible_categories || [])) if (c.key === key) return c;
  return { key: key, label: key, color: '#dcc890', kind: 'dot' };
}
function mapOnly(key) { return !!catMeta(key).map_only; }
function ainfo(actor) { return (cat().actors || {})[actor] || {}; }
function invCat(key) {
  const list = (dyn().inventory || []);
  for (const c of list) if (c.key === key) return c;
  return { key: key, label: key, items: [] };
}
function navBadge(key) {
  const d = dyn();
  if (!d.inventory) return '';
  if (key === 'inventory') return d.inventory.reduce((n, c) => n + (c.key === 'arrows' || c.key === 'armor' ? 0 : c.items.length), 0);
  if (key === 'armor') return invCat('armor').items.length;
  if (key === 'compendium') return (d.compendium || []).filter((x) => x.state !== 'Unopened').length;
  if (key === 'cook') return (d.cooking && d.cooking.dishes ? d.cooking.dishes.length : 0);
  if (key === 'progress' && d.completion) return `${pct(d.completion.totals.complete, d.completion.totals.total)}%`;
  return '';
}
function renderSaves() {
  const sel = $('#save-slot');
  if (!sel) return;
  const opts = ['<option value="">Auto (newest)</option>'].concat(S.saves.map((s) => {
    const active = s.path === S.selectedSave;
    const profile = (s.profile || '').slice(-6);
    return `<option value="${esc(s.path)}"${active ? ' selected' : ''}>${esc(s.slot.replace('_', ' '))} · ${esc(profile)}</option>`;
  }));
  sel.innerHTML = opts.join('');
  sel.value = S.selectedSave || '';
}

function renderNav() {
  const nav = $('#nav');
  const d = dyn();
  nav.innerHTML = NAV.map(([key, label, ic]) => {
    const b = navBadge(key);
    return `<button class="navbtn" role="tab" data-page="${key}" aria-selected="${S.page === key}" title="${esc(label)}">` +
      `${icon(ic, 'ni')}<span>${esc(label)}</span>${b !== '' ? `<span class="badge">${esc(b)}</span>` : ''}</button>`;
  }).join('');
  // The nav uses its own compact icon class.
  nav.querySelectorAll('svg').forEach((s) => { s.style.width = '16px'; s.style.height = '16px'; s.style.fill = 'none'; s.style.stroke = 'currentColor'; });
}

const SET_BONUS_LEVEL = 2;
const EFFECT_MAX_LEVEL = { ResistCold: 2, ResistHot: 2, ResistBurn: 2, ResistElectric: 3,
                           MiasmaGuard: 3, LightEmission: 3, NotSlippy: 3, SwimSpeedUp: 3 };
const POUCH_NOUN = { weapons: 'weapon', bows: 'bow', shields: 'shield', armor: 'armor', materials: 'material',
                     food: 'meal', zonai: 'device', keyitems: 'key item' };
const DEFAULT_MAP_CATS = ['shrines', 'lightroots', 'towers', 'villages', 'stables',
                          'great_fairies', 'labs', 'challenges', 'wells', 'chasms',
                          'old_maps', 'sages_wills', 'schema_stones'];
const MAP_CAT_ORDER = ['shrines', 'towers', 'lightroots', 'stables', 'caves', 'villages',
                       'wells', 'great_fairies', 'labs', 'shops', 'dispensers',
                       'challenges', 'dragon_tears', 'chasms', 'locations',
                       'hidden_koroks', 'carry_koroks', 'bubbuls', 'hinoxes', 'taluses',
                       'moldugas', 'flux_constructs', 'froxes', 'gleeoks', 'old_maps',
                       'sages_wills', 'addison_signposts', 'schema_stones',
                       'yiga_schematics'];
const MAP_CAT_RANK = new Map(MAP_CAT_ORDER.map((key, i) => [key, i]));
const FAST_TRAVEL_CATS = new Set(['shrines', 'towers', 'lightroots']);
const INV_KEYS = ['', 'weapons', 'bows', 'shields', 'materials', 'food', 'zonai', 'keyitems', 'arrows'];
const MAP_LAYERS = ['surface', 'sky', 'depths'];
const MAP_FOUND = ['all', 'missing', 'found'];
const PROGRESS_MODES = ['all', 'missing', 'found'];
const COMP_STATES = ['', 'Unopened', 'TakePhoto', 'Buy'];

function restoreUiState(raw) {
  if (!raw || typeof raw !== 'object') return;
  const inv = raw.inv || {};
  if (INV_KEYS.includes(inv.cat)) S.inv.cat = inv.cat;
  if (typeof inv.filter === 'string') S.inv.filter = inv.filter;

  const armor = raw.armor || {};
  if (armor.slot === '' || ['Head', 'Upper', 'Lower'].includes(armor.slot)) S.armor.slot = armor.slot;
  if (typeof armor.owned === 'boolean') S.armor.owned = armor.owned;
  if (typeof armor.set === 'string' &&
      (!armor.set || (cat().armor_sets || []).some((s) => s.key === armor.set))) S.armor.set = armor.set;
  if (typeof armor.filter === 'string') S.armor.filter = armor.filter;

  const map = raw.map || {};
  if (MAP_LAYERS.includes(map.layer)) { S.map.layer = map.layer; S.map.layerSet = true; }
  if (MAP_FOUND.includes(map.found)) S.map.found = map.found;
  if (typeof map.reveal === 'boolean') S.map.reveal = map.reveal;
  if (typeof map.medals === 'boolean') S.map.medals = map.medals;
  if (typeof map.path === 'boolean') S.map.path = map.path;
  if (typeof map.search === 'string') S.map.search = map.search;
  if (Array.isArray(map.cats)) {
    const valid = new Set((cat().collectible_categories || []).map((c) => c.key));
    S.map.cats = new Set(map.cats.filter((k) => valid.has(k)));
  }
  if (Number(map.cat_version || 1) < 2) {
    for (const k of ['villages', 'stables', 'great_fairies', 'labs', 'challenges']) {
      if ((cat().collectible_categories || []).some((c) => c.key === k)) S.map.cats.add(k);
    }
  }

  const progress = raw.progress || {};
  const pcats = new Set(['overview'].concat((cat().collectible_categories || [])
    .filter((c) => !c.map_only).map((c) => c.key)));
  if (pcats.has(progress.cat)) S.progress.cat = progress.cat;
  if (PROGRESS_MODES.includes(progress.mode)) S.progress.mode = progress.mode;
  if (typeof progress.filter === 'string') S.progress.filter = progress.filter;

  const comp = raw.comp || {};
  const groups = new Set((cat().compendium || []).map((x) => x.group));
  if (typeof comp.group === 'string' && (!comp.group || groups.has(comp.group))) S.comp.group = comp.group;
  if (COMP_STATES.includes(comp.state)) S.comp.state = comp.state;
  if (typeof comp.filter === 'string') S.comp.filter = comp.filter;

  const cook = raw.cook || {};
  if (typeof cook.filter === 'string') S.cook.filter = cook.filter;
  if (typeof cook.fx === 'string') S.cook.fx = cook.fx;
  if (typeof cook.sort === 'string' && SORT_FN[cook.sort]) S.cook.sort = cook.sort;
  if (typeof cook.all === 'boolean') S.cook.all = cook.all;
}

function uiState() {
  return {
    inv: { cat: S.inv.cat, filter: S.inv.filter },
    armor: { slot: S.armor.slot, owned: S.armor.owned, set: S.armor.set, filter: S.armor.filter },
    map: { layer: S.map.layerSet ? S.map.layer : null, found: S.map.found,
           reveal: S.map.reveal, medals: S.map.medals, path: S.map.path,
           search: S.map.search, cats: [...S.map.cats], cat_version: 2 },
    progress: { cat: S.progress.cat, mode: S.progress.mode, filter: S.progress.filter },
    comp: { group: S.comp.group, state: S.comp.state, filter: S.comp.filter },
    cook: { filter: S.cook.filter, fx: S.cook.fx, sort: S.cook.sort, all: S.cook.all },
  };
}

let uiSaveTimer = 0;
function saveUiState() {
  if (uiSaveTimer) { clearTimeout(uiSaveTimer); uiSaveTimer = 0; }
  const p = call('set_setting', 'ui_state', uiState());
  if (p && p.catch) p.catch(() => {});
}
function saveUiStateSoon() {
  if (uiSaveTimer) clearTimeout(uiSaveTimer);
  uiSaveTimer = setTimeout(saveUiState, 350);
}

function resetFilters() {
  S.inv = { cat: '', filter: '', sel: null };
  S.armor = { slot: '', owned: true, set: '', filter: '', sel: null };
  S.map.cats = new Set(DEFAULT_MAP_CATS);
  S.map.found = 'found';
  S.map.search = '';
  S.map.reveal = false;
  S.map.medals = true;
  S.map.path = false;
  S.map.sel = null;
  S.map.sourceSel = null;
  S.map.sourceMat = null;
  S.map.sources = [];
  S.progress = { cat: 'overview', mode: 'found', filter: '' };
  S.comp = { group: '', state: 'TakePhoto', filter: '', sel: null };
  S.cook = { filter: '', fx: '', sort: 'hearts', sel: null, all: false, allRows: null, allFor: -1 };
  saveUiState();
  renderPage(S.page, true);
  if (S.page === 'map') {
    renderMapToolbar(); renderMapCats(); renderMapDetail(); renderNearby(); drawMap();
  }
}

async function start() {
  const boot = await call('bootstrap');
  if (!boot || !boot.catalog) { setTimeout(start, 250); return; }
  S.catalog = boot.catalog;
  S.settings = boot.settings || {};
  S.saves = boot.saves || [];
  S.selectedSave = boot.selected_save || '';
  S.page = S.settings.tab || 'status';
  if (!NAV.some((x) => x[0] === S.page)) S.page = 'status';
  restoreUiState(S.settings.ui_state);
  // Keep the first map readable; the sidebar can show every category.
  const savedCats = S.settings.ui_state && S.settings.ui_state.map &&
                    Array.isArray(S.settings.ui_state.map.cats);
  if (!savedCats) {
    for (const c of DEFAULT_MAP_CATS) S.map.cats.add(c);
  }
  initStaticIcons();
  loadMapIcons();
  renderNav();
  renderSaves();
  attachStatic();
  document.addEventListener('click', saveUiStateSoon);
  document.addEventListener('input', saveUiStateSoon);
  document.addEventListener('change', saveUiStateSoon);
  window.addEventListener('beforeunload', saveUiState);
  await poll(true);
  showPage(S.page, true);
  setTimeout(() => { if (cat().map && !S.map.fitted) loadMapImage(); }, 900);
}

async function poll(first) {
  try {
    const p = await call('state', S.version);
    if (p) {
      const changed = first || p.data_version !== S.dataVersion;
      S.version = p.version;
      S.d = p;
      S.dataVersion = p.data_version;
      if (p.settings) Object.assign(S.settings, p.settings);
      rebuildMaterialCounts();
      renderNav();
      if (changed) {
        S.map.pathData = null;
        S.map.pathFor = -1;
        S.cook.allRows = null;
        S.cook.allFor = -1;
        renderPage(S.page);
        renderStatusLine();
        document.documentElement.dataset.ready = '1';
      } else {
        renderStatusLine();
      }
      renderRebuildStatus();
      const rb = p.save && p.save.rebuild;
      if (rb && rb.done && S.rebuildStarted) {
        S.rebuildStarted = false;
        call('ack_rebuild');
        setTimeout(() => window.location.reload(), 700);
      }
    }
  } catch (e) { /* window is closing */ }
  setTimeout(poll, 550);
}

function rebuildMaterialCounts() {
  S.matCounts = {};
  for (const it of invCat('materials').items) S.matCounts[it.actor] = it.count;
}

function loadMapIcons() {
  S.map.iconImages = {};
  const files = new Set(Object.values(cat().map_icons || {}));
  for (const stateMap of Object.values(cat().map_icon_states || {})) {
    for (const file of Object.values(stateMap || {})) files.add(file);
  }
  files.forEach((file) => {
    if (!file) return;
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => requestDraw();
    img.src = 'companion_data/' + file;
    S.map.iconImages[file] = img;
  });
  const medallion = ainfo('Obj_WarpDLC_Prototype').icon;
  if (medallion) {
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => requestDraw();
    img.src = 'companion_data/icons/' + encodeURIComponent(medallion);
    S.map.iconImages.medallion = img;
  }
}

function mapIconFile(category, state) {
  const states = (cat().map_icon_states || {})[category];
  if (states && states[String(state)]) return states[String(state)];
  return (cat().map_icons || {})[category] || null;
}

function showPage(key, first) {
  S.page = key;
  $$('.page').forEach((p) => { p.hidden = p.dataset.page !== key; });
  $$('#nav .navbtn').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.page === key)));
  call('set_setting', 'tab', key);
  renderPage(key, first);
}

function renderPage(key, first) {
  if (!S.catalog) return;
  if (key === 'status') renderStatus();
  else if (key === 'inventory') renderInventory();
  else if (key === 'armor') renderArmor();
  else if (key === 'map') renderMap();
  else if (key === 'progress') renderProgress();
  else if (key === 'compendium') renderCompendium();
  else if (key === 'cook') renderCooking();
}

/* ------------------------------------------------------------------ status */

function equipCard(label, item, iconName, meta) {
  if (!item) {
    const armorSlot = label === 'Head' || label === 'Body' || label === 'Legs';
    const action = armorSlot ? 'data-page-go="armor"' : `data-invcat="${label.toLowerCase()}s"`;
    return `<button class="equip-card" ${action}>` +
      `<span class="ico">${icon(iconName, 'g')}</span><span><span class="en">${esc(label)}</span><span class="ev dimmed">Empty</span></span></button>`;
  }
  const fused = item.fused ? ` · Fused: ${item.fused_name || item.fused}` : '';
  return `<button class="equip-card" data-invactor="${esc(item.actor)}">` +
    `<span class="ico">${art(item)}</span><span><span class="en">${esc(label)}</span>` +
    `<span class="ev">${esc(item.name)}</span><span class="em">${esc((meta || '') + fused)}</span></span></button>`;
}

function findEquip(key, actor) {
  for (const it of invCat(key).items) if (it.actor === actor) return it;
  return null;
}

function gearEffectLevels() {
  const eq = (dyn().status && dyn().status.equipped) || {};
  const pieces = ['armor_head', 'armor_upper', 'armor_lower']
    .map((k) => findEquip('armor', eq[k] && eq[k].actor)).filter(Boolean);
  const out = {};
  const add = (type, level, capKey) => {
    const cap = EFFECT_MAX_LEVEL[capKey || type] || 3;
    out[type] = Math.min(cap, (out[type] || 0) + Math.max(1, level || 1));
  };
  for (const piece of pieces) {
    for (const fx of piece.effect_info || []) add(fx.type, fx.level);
  }
  if (pieces.length === 3) {
    const setKey = pieces[0].set_key;
    if (setKey && pieces.every((x) => x.set_key === setKey && (x.rank || 1) >= SET_BONUS_LEVEL)) {
      for (const fx of pieces[0].set_bonus || []) add(fx.type, fx.level);
    }
  }
  return out;
}

function staminaWheel(fill) {
  const c = 2 * Math.PI * 12;
  const dash = c * clamp(fill, 0, 1);
  return `<svg class="wheel" viewBox="0 0 30 30" aria-hidden="true">` +
    `<circle class="wb" cx="15" cy="15" r="12"/>` +
    `<circle class="wf" cx="15" cy="15" r="12" stroke-dasharray="${dash.toFixed(2)} ${(c - dash).toFixed(2)}" transform="rotate(-90 15 15)"/>` +
    `</svg>`;
}

function staminaGauge(wheels) {
  const value = Number(wheels) || 0;
  if (value <= 0) return '<span class="dimmed">None</span>';
  const whole = Math.floor(value + 1e-6);
  const frac = value - whole;
  let out = '';
  for (let i = 0; i < whole; i++) out += staminaWheel(1);
  if (frac > 0.02) out += staminaWheel(frac);
  return out;
}

function energyCell(fill) {
  const p = clamp(fill, 0, 1);
  const h = 25 * p;
  return `<svg class="battery" viewBox="0 0 24 34" aria-hidden="true">` +
    `<rect class="bt" x="9" y="1" width="6" height="3" rx="1"/>` +
    `<rect class="bb" x="4" y="3" width="16" height="27" rx="3"/>` +
    `<rect class="bf" x="7" y="${(28 - h).toFixed(2)}" width="10" height="${h.toFixed(2)}" rx="1.5"/>` +
    `</svg>`;
}

function energyGauge(cells) {
  const value = Number(cells) || 0;
  if (value <= 0) return '<span class="dimmed">None</span>';
  const whole = Math.floor(value + 1e-6);
  const frac = value - whole;
  let out = '';
  for (let i = 0; i < whole; i++) out += energyCell(1);
  if (frac > 0.02) out += energyCell(frac);
  return out;
}

function sageTile(s) {
  const state = s.is_follow ? 'Following' : s.is_summon ? 'Summoned' : s.is_get ? 'Ready' : 'Not met';
  const known = s.is_get || s.is_follow || s.is_summon;
  const icon = (cat().sage_icons || {})[s.key];
  const avatar = icon
    ? `<img class="sage-av" src="companion_data/icons/${encodeURIComponent(icon)}" alt="">`
    : `<span class="sage-fallback">${esc((s.name || '?')[0])}</span>`;
  return `<div class="sage${known ? ' on' : ''}${s.is_follow ? ' follow' : ''}" title="${esc(s.name)}: ${state}">` +
    avatar + `<span class="sn">${esc(s.name)}</span><span class="ss">${state}</span></div>`;
}

function abilityChip(a) {
  const meta = ainfo(a.actor);
  const img = meta.icon
    ? `<img class="ab-ic" src="companion_data/icons/${encodeURIComponent(meta.icon)}" alt="">`
    : `<span class="ab-ic">${icon('golem', 'g')}</span>`;
  return `<span class="ability">${img}<span>${esc(a.name)}</span></span>`;
}

function renderStatus() {
  const el = $('#page-status');
  const d = dyn();
  if (!d.status) {
    el.innerHTML = `<div class="empty" style="padding-top:80px"><b>Reading your save</b>The companion fills in as soon as it finds the newest save.</div>`;
    return;
  }
  const st = d.status;
  const eq = st.equipped || {};
  const comp = d.completion || { categories: [], totals: { complete: 0, started: 0, total: 0 } };
  const cats = {};
  for (const c of comp.categories) cats[c.key] = c;
  const weapon = findEquip('weapons', eq.weapons && eq.weapons.actor);
  const bow = findEquip('bows', eq.bows && eq.bows.actor);
  const shield = findEquip('shields', eq.shields && eq.shields.actor);
  const head = findEquip('armor', eq.armor_head && eq.armor_head.actor);
  const body = findEquip('armor', eq.armor_upper && eq.armor_upper.actor);
  const legs = findEquip('armor', eq.armor_lower && eq.armor_lower.actor);
  const wornArmor = [head, body, legs].filter(Boolean);
  const effectMap = new Map();
  for (const piece of wornArmor) {
    for (const fx of piece.effect_info || []) {
      const cur = effectMap.get(fx.type);
      const level = Math.max(1, fx.level || 1);
      const cap = EFFECT_MAX_LEVEL[fx.type] || 3;
      if (cur) cur.level = Math.min(cap, (cur.level || 1) + level);
      else effectMap.set(fx.type, { ...fx, level });
    }
  }
  const activeEffects = [...effectMap.values()];
  const wornSetKey = wornArmor.length === 3 ? wornArmor[0].set_key : null;
  const setBonusFx = wornSetKey &&
    wornArmor.every((x) => x.set_key === wornSetKey && (x.rank || 1) >= SET_BONUS_LEVEL)
    ? (wornArmor[0].set_bonus || []) : [];
  let attackLevel = (effectMap.get('AttackUp') || {}).level || 0;
  for (const fx of setBonusFx) {
    if (fx.type === 'AttackUp') attackLevel = Math.max(attackLevel, Math.max(1, fx.level || 1), Math.min(3, attackLevel + 1));
  }
  attackLevel = Math.min(3, attackLevel);
  const attackMult = attackLevel === 1 ? 1.2 : attackLevel === 2 ? 1.3 : attackLevel === 3 ? 1.5 : 1;
  const weaponAttack = weapon ? ((weapon.weapon && weapon.weapon.attack) || 0) : 0;
  const fuseAttack = weapon && weapon.fused ? (ainfo(weapon.fused).fuse_attack || 0) : 0;
  const attackMod = weapon && weapon.effect === 'AttackUp' ? (weapon.effect_value || 0) : 0;
  const attack = weaponAttack + fuseAttack + attackMod;
  const defense = wornArmor.reduce((n, p) => n + (p.defense || 0), 0);
  const headDef = head ? head.defense || 0 : 0;
  const bodyDef = body ? body.defense || 0 : 0;
  const legDef = legs ? legs.defense || 0 : 0;
  const matCount = invCat('materials').items.length;
  const foodCount = invCat('food').items.length;
  const quick = (label, catKey) => {
    const c = cats[catKey];
    if (!c) return '';
    const done = c.complete;
    const meta = catMeta(catKey);
    const iconFile = (cat().map_icons || {})[catKey];
    const ico = iconFile ? `<img class="qico" src="companion_data/${encodeURIComponent(iconFile)}" alt="">` : '';
    return `<button class="quick" data-pcat="${catKey}" style="--c:${meta.color}">` +
      `<span class="qk">${ico}${esc(label)}</span>` +
      `<span class="qv">${done}<small> / ${c.total}</small></span>` +
      `<span class="qs">${c.missing} missing${c.started ? ` · ${c.started} started` : ''}</span>` +
      `<span class="bar"><i style="width:${pct(done, c.total)}%"></i></span></button>`;
  };
  const pouchStat = (key, label) => {
    const c = invCat(key);
    if (!c.cap) return '';
    const sub = c.next_cost ? `Next slot: ${c.next_cost} seeds · max ${c.max}` : `${POUCH_NOUN[key] || 'item'} slots`;
    const action = key === 'armor' ? 'data-page-go="armor"' : `data-invcat="${key}"`;
    return `<button class="stat" ${action}><span class="k">${esc(label)}</span>` +
      `<span class="v">${c.used}<small> / ${c.cap}</small></span>` +
      `<span class="vv">${esc(sub)}</span></button>`;
  };
  const keyItem = (actor, label) => {
    const it = invCat('keyitems').items.find((x) => x.actor === actor);
    const count = it ? it.count : 0;
    const icon = ainfo(actor).icon;
    return `<button class="keyitem" data-invactor="${esc(actor)}">` +
      `${icon ? `<img src="companion_data/icons/${encodeURIComponent(icon)}" alt="">` : ''}` +
      `<span>${esc(label)}</span><b>${fmtNum(count)}</b></button>`;
  };
  const sages = (st.sages || []).map(sageTile).join('');
  const abilities = (st.abilities || []).map(abilityChip).join('') || '<span class="dimmed">None yet</span>';
  const pos = st.position || {};
  const layer = st.layer || st.map_layer || 'Surface';
  const staminaMax = Number((st.stamina || {}).max) || 0;
  const energyMax = Number((st.energy || {}).max) || 0;
  const playHours = st.playtime !== null && st.playtime !== undefined ? Math.floor(st.playtime / 3600) : null;
  const playMinutes = st.playtime !== null && st.playtime !== undefined ? Math.floor((st.playtime % 3600) / 60) : null;
  const pathKm = st.path_distance !== null && st.path_distance !== undefined ? st.path_distance / 1000 : null;
  const rupee = ainfo('PutRupee_Gold');
  const rupeeIcon = rupee.icon ? `<img class="rupee-icon" src="companion_data/icons/${encodeURIComponent(rupee.icon)}" alt="">` : '';
  el.innerHTML = `
  <div class="status-grid">
    <section class="card hero status-main">
      <div class="status-top">
        <div class="who">
          <div class="mark">${icon('check', 'g')}</div>
          <div><h1 class="h-name">Link</h1>
            <div class="h-sub">${esc(layer)} · ${esc((d.save && d.save.slot) || 'save')} · read-only</div></div>
        </div>
        <div class="rupees">${rupeeIcon}<span>${fmtNum(st.rupees)}</span><small>RUPEES</small></div>
      </div>
      <div class="hearts">${heartsWithMax(st.hearts.current, st.hearts.max, false)}</div>
      <div class="h-line">${fmtHearts(st.hearts.current)} of ${fmtHearts(st.hearts.max)} hearts filled</div>

      <div class="vitals">
        <div class="vital">
          <span class="vk">Stamina</span>
          <div class="gauge">${staminaGauge(staminaMax)}</div>
          <span class="vv">${staminaMax.toFixed(1)} wheels</span>
        </div>
        <button class="vital" data-invcat="zonai">
          <span class="vk">Energy</span>
          <div class="gauge">${energyGauge(energyMax)}</div>
          <span class="vv">${energyMax.toFixed(1)} cells</span>
        </button>
        <button class="vital" data-invcat="materials">
          <span class="vk">Materials</span>
          <span class="vbig">${matCount}</span>
          <span class="vv">in pouch</span>
        </button>
      </div>

      <div class="statrow combat">
        <button class="stat" data-invcat="weapons"><span class="k">Attack</span><span class="v">${attack}</span>
          <span class="vv">${weapon ? `Weapon ${weaponAttack}${fuseAttack ? ` + fuse ${fuseAttack}` : ''}${attackMod ? ` + mod ${attackMod}` : ''}` : 'No weapon equipped'}</span></button>
        <button class="stat" data-page-go="armor"><span class="k">Defense</span><span class="v">${defense}</span>
          <span class="vv">${wornArmor.length ? `${headDef} + ${bodyDef} + ${legDef}` : 'No armor equipped'}</span></button>
        ${attackLevel ? `<button class="stat" data-invcat="weapons"><span class="k">With Attack Up</span><span class="v">${Math.round(attack * attackMult)}</span><span class="vv">Lv. ${attackLevel}${setBonusFx.some((x) => x.type === 'AttackUp') ? ' · set bonus' : ''}</span></button>` : ''}
      </div>

      <div class="status-meta">
        <span>${fmtXYZ(pos.x, pos.y, pos.z)}</span>
        <span>${esc(layer)}</span>
      </div>

      <div class="keyitem-strip">
        ${keyItem('Obj_KorokNuts', 'Korok Seeds')}
        ${keyItem('CaveMasterMedal', 'Bubbul Gems')}
        ${keyItem('Obj_DungeonClearSeal', 'Light of Blessing')}
      </div>

      <h3>Equipped</h3>
      <div class="equip-grid">
        ${equipCard('Weapon', weapon, 'sword', weapon ? `${weapon.life || 0} / ${(weapon.weapon && weapon.weapon.max_life || 0) + (weapon.extra || 0)} durability` : '')}
        ${equipCard('Bow', bow, 'bow', bow ? `${bow.life || 0} / ${(bow.weapon && bow.weapon.max_life || 0) + (bow.extra || 0)} durability` : '')}
        ${equipCard('Shield', shield, 'shield', shield ? `${shield.life || 0} / ${(shield.weapon && shield.weapon.max_life || 0) + (shield.extra || 0)} durability` : '')}
        ${equipCard('Head', head, 'head', head ? `Defense ${head.defense || 0}${head.rank ? ` · Lv ${head.rank}` : ''}` : '')}
        ${equipCard('Body', body, 'body', body ? `Defense ${body.defense || 0}${body.rank ? ` · Lv ${body.rank}` : ''}` : '')}
        ${equipCard('Legs', legs, 'legs', legs ? `Defense ${legs.defense || 0}${legs.rank ? ` · Lv ${legs.rank}` : ''}` : '')}
      </div>
      ${(activeEffects.length || setBonusFx.length)
        ? `<h3 class="fx-gap">Link effects</h3><div class="tagrow">${effectChips(activeEffects, 'eff')}${effectChips(setBonusFx, 'bonus')}</div>` +
          effectNotes(activeEffects.concat(setBonusFx))
        : ''}
    </section>

    <section class="card status-side">
      <h3>Sages <span class="sub">${(st.sages || []).filter((s) => s.is_get || s.is_follow || s.is_summon).length} of 5</span></h3>
      <div class="sage-grid">${sages || '<span class="dimmed">No sage data in this save.</span>'}</div>
      <h3 class="side-gap">Abilities</h3>
      <div class="chiprow">${abilities}</div>
      <h3 class="side-gap">Journey <span class="sub">from the save</span></h3>
      <div class="statrow journey">
        <div class="stat"><span class="k">Playtime</span><span class="v">${playHours !== null ? `${playHours}<small>h ${playMinutes}m</small>` : '--'}</span></div>
        <div class="stat"><span class="k">Deaths</span><span class="v">${st.deaths !== null && st.deaths !== undefined ? fmtNum(st.deaths) : '--'}</span></div>
        <div class="stat"><span class="k">Distance</span><span class="v">${pathKm !== null ? `${pathKm.toFixed(1)}<small>km</small>` : '--'}</span></div>
        <div class="stat"><span class="k">Path points</span><span class="v">${st.path_points !== null && st.path_points !== undefined ? fmtNum(st.path_points) : '--'}</span></div>
      </div>
    </section>

    <section class="card pouch-wide">
      <h3>Pouch <span class="sub">slots and next upgrades</span></h3>
      <div class="statrow pouch">
        ${pouchStat('weapons', 'Weapons')}
        ${pouchStat('bows', 'Bows')}
        ${pouchStat('shields', 'Shields')}
        ${pouchStat('armor', 'Armor')}
        ${pouchStat('materials', 'Materials')}
        ${pouchStat('food', 'Meals')}
        ${pouchStat('zonai', 'Zonai devices')}
        ${pouchStat('keyitems', 'Key items')}
      </div>
    </section>

    <section class="card wide">
      <h3>Completion <span class="sub">${comp.totals.complete} of ${comp.totals.total} tracked</span></h3>
      <div class="quick-grid">
        ${quick('Shrines', 'shrines')}
        ${quick('Lightroots', 'lightroots')}
        ${quick('Koroks', 'hidden_koroks')}
        ${quick('Caves', 'caves')}
        ${quick('Bubbuls', 'bubbuls')}
        <button class="quick" data-pcat="overview"><span class="qk">Overall</span><span class="qv">${pct(comp.totals.complete, comp.totals.total)}<small>%</small></span><span class="qs">${comp.totals.total - comp.totals.complete - comp.totals.started} missing</span><span class="bar"><i style="width:${pct(comp.totals.complete, comp.totals.total)}%"></i></span></button>
      </div>
    </section>
  </div>`;
}

/* ------------------------------------------------------------------ inventory */

function invCell(it, selected) {
  const key = it.actor + ':' + (it.index === undefined ? 0 : it.index);
  let badge = '';
  if (it.count > 1) badge = `<span class="badge count">×${it.count}</span>`;
  if (it.category === 'Armor') badge = `<span class="level">Lv ${it.rank || 1}</span>`;
  let dur = '';
  if (it.life !== undefined && it.life !== null && it.life >= 0 && it.weapon) {
    const max = (it.weapon.max_life || 0) + (it.extra || 0);
    if (max > 0) dur = `<span class="dur${it.life / max < 0.25 ? ' low' : ''}"><i style="width:${clamp(it.life / max * 100, 0, 100)}%"></i></span>`;
  }
  const dim = it.category === 'Armor' && it.rank === undefined ? ' dim' : '';
  let fused = '';
  if (it.fused) {
    const label = it.fused_name || it.fused;
    fused = it.fused_icon
      ? `<img class="fusebadge" src="companion_data/icons/${encodeURIComponent(it.fused_icon)}" alt="" title="Fused with ${esc(label)}">`
      : `<span class="fusebadge glyph" title="Fused with ${esc(label)}">+</span>`;
  }
  const lowDur = it.life !== undefined && it.life !== null && it.life >= 0 && it.life <= 3;
  return `<button class="cell${dim}${dur ? ' has-dur' : ''}${lowDur ? ' lowdur' : ''}" role="option" aria-selected="${selected}" data-invkey="${esc(key)}" data-actor="${esc(it.actor)}">` +
    `${it.equipped ? '<span class="eq"></span>' : ''}${badge}${fused}${art(it)}${dur}<span class="nm">${esc(it.name)}</span></button>`;
}

function renderInventory() {
  const categories = (dyn().inventory || []).filter((c) => c.key !== 'armor');
  if (S.inv.cat === 'armor' || (S.inv.cat && !categories.some((c) => c.key === S.inv.cat))) S.inv.cat = '';
  const allItems = categories.flatMap((c) => c.items);
  const current = S.inv.cat ? invCat(S.inv.cat) : { key: '', label: 'All items', items: allItems };
  const armorCount = invCat('armor').items.length;
  $('#inv-cats').innerHTML = `<button class="fxchip" data-invcat="" aria-pressed="${S.inv.cat === ''}"><span>All</span><span class="c">${allItems.length}</span></button>` +
    categories.map((c) => {
      const cap = c.cap ? `/${c.cap}` : '';
      const title = c.next_cost ? `Next slot: ${c.next_cost} Korok Seeds. Max ${c.max}.`
        : c.cap ? `${c.used} of ${c.cap} slots.` : '';
      return `<button class="fxchip" data-invcat="${c.key}" aria-pressed="${S.inv.cat === c.key}"${title ? ` title="${esc(title)}"` : ''}>` +
        `<span>${esc(c.label)}</span><span class="c">${c.items.length}${cap}</span></button>`;
    }).join('') +
    `<button class="fxchip armor-link" data-page="armor" title="Armor has its own tab"><span>Armor</span><span class="c">${armorCount}</span></button>`;
  const pouch = $('#inv-pouch');
  if (pouch) {
    const cap = current.cap;
    if (cap) {
      const bits = [];
      bits.push(`<b>${current.used} / ${cap}</b> ${POUCH_NOUN[current.key] || 'item'} slots`);
      if (current.next_cost) {
        const seed = ainfo('Obj_KorokNuts').icon;
        bits.push(`${seed ? `<img src="companion_data/icons/${encodeURIComponent(seed)}" alt="">` : ''} Next slot: <b>${current.next_cost}</b> Korok Seeds`);
      }
      if (current.max && current.key !== 'armor') bits.push(`Max ${current.max}`);
      pouch.innerHTML = bits.join('<span class="sep">·</span>');
      pouch.hidden = false;
    } else {
      pouch.hidden = true;
      pouch.innerHTML = '';
    }
  }
  $('#inv-filter').value = S.inv.filter;
  $('#inv-filter').placeholder = S.inv.cat ? `Filter ${current.label.toLowerCase()}` : 'Filter inventory';
  const f = S.inv.filter.trim().toLowerCase();
  const items = current.items.filter((it) => {
    if (!f) return true;
    return [it.name, it.caption, it.kind, it.effect_name, it.set_name, it.category].some((v) => v && String(v).toLowerCase().includes(f));
  });
  const armorHint = $('#inv-armor-hint');
  if (armorHint) {
    const armorMatch = f && (cat().armor || []).some((a) =>
      [a.name, a.set_name, a.caption, ...((a.effect_info || []).map((e) => e.name))]
        .some((v) => v && String(v).toLowerCase().includes(f)));
    if (armorMatch) {
      armorHint.innerHTML = `<span>Armor has its own tab.</span> ` +
        `<button class="btn tiny" data-armor-search>Search armor for "${esc(S.inv.filter)}"</button>`;
      armorHint.hidden = false;
    } else {
      armorHint.hidden = true;
      armorHint.innerHTML = '';
    }
  }
  const grid = $('#inv-grid');
  if (!items.length) {
    grid.innerHTML = `<div class="empty"><b>Nothing here</b>${f ? 'No item matches the filter.' : 'This pouch category is empty.'}</div>`;
    $('#inv-detail').innerHTML = '';
    return;
  }
  let sel = S.inv.sel;
  if (!items.some((it) => it.actor + ':' + (it.index === undefined ? 0 : it.index) === sel)) sel = items[0].actor + ':' + (items[0].index === undefined ? 0 : items[0].index);
  S.inv.sel = sel;
  grid.innerHTML = items.map((it) => invCell(it, it.actor + ':' + (it.index === undefined ? 0 : it.index) === sel)).join('');
  const chosen = items.find((it) => it.actor + ':' + (it.index === undefined ? 0 : it.index) === sel) || items[0];
  renderInvDetail(chosen);
}

function durabilityHTML(it) {
  if (it.life === undefined || it.life === null || it.life < 0) return '';
  const max = (it.weapon && it.weapon.max_life || 0) + (it.extra || 0);
  if (!max) return `<div class="grid2"><dt>Durability</dt><dd>${it.life}</dd></div>`;
  return `<div class="durable"><span>Durability</span><span class="bar"><i style="width:${clamp(it.life / max * 100, 0, 100)}%"></i></span><b>${it.life} / ${max}</b></div>`;
}

function renderInvDetail(it) {
  const el = $('#inv-detail');
  if (!it) { el.innerHTML = ''; return; }
  const meta = [];
  if (it.category) meta.push(`<span class="tag">${esc(it.category)}</span>`);
  if (it.kind && it.kind !== it.category) meta.push(`<span class="tag">${esc(it.kind)}</span>`);
  if (it.equipped) meta.push('<span class="tag gold">Equipped</span>');
  let body = '';
  if (it.category === 'Weapon' || it.category === 'Bow' || it.category === 'Shield') {
    body += durabilityHTML(it);
    if (it.fused) {
      const fuseIcon = it.fused_icon
        ? `<img class="fuse-ico" src="companion_data/icons/${encodeURIComponent(it.fused_icon)}" alt="">`
        : '';
      body += `<div class="grid2"><dt>Fused with</dt><dd>${fuseIcon}${esc(it.fused_name || it.fused)}</dd></div>`;
    }
    body += `<div class="grid2"><dt>Attack</dt><dd>${it.weapon && it.weapon.attack ? it.weapon.attack : '--'}</dd>`;
    if (it.effect) body += `<dt>Modifier</dt><dd>${esc(it.effect)}${it.effect_value ? ` +${it.effect_value}` : ''}</dd>`;
    body += `<dt>Sell</dt><dd>${fmtNum(it.sell)} rupees</dd></div>`;
  } else if (it.category === 'Armor') {
    body += `<div class="grid2"><dt>Defense</dt><dd>${it.defense || 0}</dd><dt>Level</dt><dd>${it.rank || 1} of 4</dd>` +
      `<dt>Set</dt><dd>${esc(it.set_name || '--')}</dd>`;
    if (it.defense_next) body += `<dt>Next defense</dt><dd>${it.defense_next}</dd>`;
    body += `</div>`;
    body += upgradeHTML(it);
  } else if (it.category === 'Food') {
    body += `<div class="grid2"><dt>Hearts</dt><dd>${it.hearts ? fmtHearts(it.hearts) : '--'}</dd>` +
      `<dt>Effect</dt><dd>${esc(it.effect_name || 'None')}${it.level ? ` (level ${it.level})` : ''}</dd>` +
      (it.seconds ? `<dt>Duration</dt><dd>${fmtTime(it.seconds)}</dd>` : '') +
      `<dt>Count</dt><dd>${it.count}</dd></div>`;
    if (it.ingredients && it.ingredients.length) {
      body += `<h3 class="label">Ingredients</h3><div class="used">` +
        it.ingredients.map((a) => `<button data-invactor="${esc(a)}">${esc(ainfo(a).name || a)}</button>`).join('') + `</div>`;
    }
  } else if (it.category === 'Material') {
    body += `<div class="grid2"><dt>In pouch</dt><dd>${it.count}</dd>` +
      `<dt>Hearts cooked</dt><dd>${it.hearts ? fmtHearts(it.hearts) : '--'}</dd>` +
      `<dt>Effect</dt><dd>${esc(it.effect_name || 'None')}</dd>` +
      `<dt>Kind</dt><dd>${esc((it.kinds || []).join(', ') || '--')}</dd>` +
      `<dt>Sell</dt><dd>${fmtNum(it.sell)} rupees</dd></div>`;
    const src = (cat().material_sources || {})[it.actor];
    if (src) {
      body += `<div class="actions" style="margin-top:10px"><button class="btn" data-srcmat="${esc(it.actor)}">Sources</button>` +
        `<span class="dimmed" style="align-self:center;font-size:12.5px">Buy, drop, and world-spawn locations</span></div>`;
    }
    const used = ((dyn().cooking && dyn().cooking.dishes) || []).filter((d) => (d.pot || []).some((p) => p.actor === it.actor)).slice(0, 8);
    if (used.length) body += `<h3 class="label">Used in</h3><div class="used">` + used.map((d) => `<button data-cdish="${esc(d.id)}">${esc(d.name)}</button>`).join('') + `</div>`;
  } else {
    body += `<div class="grid2"><dt>Count</dt><dd>${it.count < 0 ? 'Owned' : it.count}</dd>` +
      `<dt>Kind</dt><dd>${esc(it.kind || it.category || '--')}</dd>` +
      (it.sell ? `<dt>Sell</dt><dd>${fmtNum(it.sell)} rupees</dd>` : '') + `</div>`;
  }
  el.innerHTML = `<div class="in"><div class="d-head">${art(it, 'hero')}<div><h2 class="d-name">${esc(it.name)}</h2>` +
    `<div class="d-sub">${esc(it.category || 'Item')}${it.count > 1 ? ` · ${it.count} in pouch` : ''}</div></div></div>` +
    `<div class="tagrow">${meta.join('')}</div>` +
    (it.caption ? `<p class="cap">${esc(it.caption)}</p>` : '') +
    body + `</div>`;
}

function upgradeHTML(it) {
  const next = it.upgrade || [];
  if (!next.length) return `<p class="note">No Great Fairy upgrade path is recorded for this piece.</p>`;
  const rows = next.map((u) => {
    const have = S.matCounts[u.actor] || 0;
    const meta = ainfo(u.actor);
    if ((cat().material_sources || {})[u.actor]) {
      return `<button class="u${have < u.n ? ' miss' : ''}" data-srcmat="${esc(u.actor)}" title="Where to find ${esc(meta.name || u.actor)}">` +
        `${art(meta, 'i')}<span class="n">${esc(meta.name || u.actor)}</span><span class="c">${have} / ${u.n}</span>` +
        `<span class="src">Sources</span></button>`;
    }
    return `<div class="u${have < u.n ? ' miss' : ''}">${art(meta, 'i')}<span class="n">${esc(meta.name || u.actor)}</span><span class="c">${have} / ${u.n}</span></div>`;
  }).join('');
  return `<h3 class="label">Upgrade materials</h3><div class="upg">${rows}</div>` +
    `<div class="grid2"><dt>Rupees</dt><dd>${fmtNum(it.price)}</dd></div>`;
}

/* ------------------------------------------------------------------ armor */

function armorPieces() {
  const byBase = {};
  for (const row of (cat().armor || [])) {
    const base = row.base || row.actor;
    if (!byBase[base]) byBase[base] = { base: base, ranks: [] };
    byBase[base].ranks.push(row);
  }
  const owned = {};
  for (const it of invCat('armor').items) {
    const base = it.base || it.actor;
    if (!owned[base] || (it.rank || 0) > (owned[base].rank || 0)) owned[base] = it;
  }
  return Object.keys(byBase).map((b) => {
    const p = byBase[b];
    p.ranks.sort((a, c) => a.rank - c.rank);
    p.maxRank = p.ranks[p.ranks.length - 1].rank || 1;
    p.owned = owned[b] || null;
    p.current = p.owned ? (p.ranks.find((r) => r.actor === p.owned.actor) || p.ranks[0]) : p.ranks[0];
    p.name = p.current.name || p.ranks[0].name;
    p.icon = p.current.icon || p.ranks[0].icon;
    p.slot = p.current.slot;
    p.set_key = p.current.set_key;
    p.set_name = p.current.set_name;
    p.next = p.current.next ? p.ranks.find((r) => r.actor === p.current.next) : null;
    return p;
  }).sort((a, b) => (a.set_name || '').localeCompare(b.set_name || '') ||
    (a.slot === b.slot ? 0 : a.slot === 'Head' ? -1 : a.slot === 'Upper' ? 1 : 0) ||
    a.name.localeCompare(b.name));
}

function rankDefense(piece, rank) {
  const rows = piece.ranks || [];
  if (!rows.length) return 0;
  const exact = rows.find((r) => r.rank === rank);
  if (exact) return exact.defense || 0;
  const top = rows[rows.length - 1];
  return top ? (top.defense || 0) : 0;
}

function setDefense(pieces, mode) {
  return pieces.reduce((n, x) => {
    if (mode === 'now') return n + (x.owned ? (x.current.defense || 0) : 0);
    if (mode === 'lv2') return n + rankDefense(x, SET_BONUS_LEVEL);
    return n + rankDefense(x, x.maxRank || 1);
  }, 0);
}

// Piece effects stack across the set; upgrades do not change them.
function fullSetEffects(pieces) {
  const totals = new Map();
  for (const piece of pieces) {
    const row = (piece.ranks || [])[0];
    for (const fx of (row && row.effect_info) || []) {
      const cur = totals.get(fx.type) || { type: fx.type, name: fx.name, level: 0, pieces: 0 };
      cur.level += Math.max(1, fx.level || 1);
      cur.pieces += 1;
      totals.set(fx.type, cur);
    }
  }
  return [...totals.values()]
    .filter((x) => x.pieces > 1)
    .map((x) => ({ ...x, level: Math.min(EFFECT_MAX_LEVEL[x.type] || 3, x.level) }));
}

function armorCell(p, selected) {
  const owned = !!p.owned;
  const lvl = owned ? (p.owned.rank || 1) : 0;
  const badge = owned ? `<span class="level">Lv ${lvl}</span>` : '';
  const upg = (p.current && p.current.upgrade) || [];
  const missing = upg.filter((u) => (S.matCounts[u.actor] || 0) < u.n).length;
  const ready = upg.length > 0 && missing === 0;
  let upstat = '';
  if (upg.length && p.next) {
    upstat = `<span class="upstat ${ready ? 'ready' : 'need'}" title="${ready ? 'Materials ready' : `${missing} material${missing === 1 ? '' : 's'} missing`}">${ready ? 'Ready' : `Need ${missing}`}</span>`;
  } else if (!p.next && owned) {
    upstat = '<span class="upstat max">MAX</span>';
  }
  return `<button class="cell${owned ? '' : ' dim'}" role="option" aria-selected="${selected}" data-armor="${esc(p.base)}">` +
    `${badge}${upstat}${resistanceBadges(p.current && p.current.effect_info)}${art({ icon: p.icon, name: p.name }, 'g')}<span class="nm">${esc(p.name)}</span></button>`;
}

function renderArmor() {
  const pieces = armorPieces();
  if (S.armor.set && !(cat().armor_sets || []).some((s) => s.key === S.armor.set)) S.armor.set = '';
  const slots = [['', 'All'], ['Head', 'Head'], ['Upper', 'Body'], ['Lower', 'Legs']];
  const counted = S.armor.owned ? pieces.filter((p) => p.owned) : pieces;
  $('#armor-slots').innerHTML = slots.map(([k, l]) => {
    const n = k ? counted.filter((p) => p.slot === k).length : counted.length;
    return `<button class="fxchip" data-slot="${k}" aria-pressed="${S.armor.slot === k}"><span>${l}</span><span class="c">${n}</span></button>`;
  }).join('');
  $('#armor-owned').setAttribute('aria-checked', String(S.armor.owned));
  const setSel = $('#armor-set');
  if (!setSel.dataset.ready) {
    const sets = (cat().armor_sets || []).slice().sort((a, b) => a.name.localeCompare(b.name));
    setSel.innerHTML = `<option value="">All sets</option>` + sets.map((s) => `<option value="${esc(s.key)}">${esc(s.name)}</option>`).join('');
    setSel.dataset.ready = '1';
  }
  setSel.value = S.armor.set || '';
  const armorPouch = $('#armor-pouch');
  if (armorPouch) {
    const armorCat = invCat('armor');
    if (armorCat.cap) {
      armorPouch.innerHTML = `<b>${armorCat.used} / ${armorCat.cap}</b> armor slots`;
      armorPouch.hidden = false;
    } else {
      armorPouch.hidden = true;
      armorPouch.innerHTML = '';
    }
  }
  $('#armor-filter').value = S.armor.filter;
  const f = S.armor.filter.trim().toLowerCase();
  const list = pieces.filter((p) => {
    if (S.armor.slot && p.slot !== S.armor.slot) return false;
    if (S.armor.owned && !p.owned) return false;
    if (S.armor.set && p.set_key !== S.armor.set) return false;
    if (f) {
      const hay = [p.name, p.set_name, p.current && p.current.caption,
        ...((p.current && p.current.effect_info) || []).map((e) => e.name)]
        .filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(f)) return false;
    }
    return true;
  });
  const grid = $('#armor-grid');
  if (!list.length) {
    grid.innerHTML = `<div class="empty"><b>No armor matches</b>Try another slot or turn off Owned only.</div>`;
    $('#armor-detail').innerHTML = '';
    return;
  }
  let sel = S.armor.sel;
  if (!list.some((p) => p.base === sel)) sel = list[0].base;
  S.armor.sel = sel;
  grid.innerHTML = list.map((p) => armorCell(p, p.base === sel)).join('');
  renderArmorDetail(list.find((p) => p.base === sel) || list[0]);
}

function effectChips(list, cls) {
  return (list || []).map((e) => {
    const desc = effectDesc(e);
    return `<span class="tag ${cls || ''}"${desc ? ` title="${esc(desc)}"` : ''}>${esc(e.name)}${e.level > 1 && !e.set ? ` Lv. ${e.level}` : ''}</span>`;
  }).join('');
}
function effectNotes(list) {
  const seen = new Set();
  const rows = [];
  for (const e of (list || [])) {
    const desc = effectDesc(e);
    if (!desc || seen.has(e.type)) continue;
    seen.add(e.type);
    const level = Math.max(1, e.level || 1);
    const amount = effectAmount(e.type, level);
    const shown = amount || desc;
    rows.push(`<div class="fxnote"><b>${esc(e.name)}${level > 1 && !e.set ? ` Lv. ${level}` : ''}</b><span>: ${esc(shown)}</span></div>`);
  }
  return rows.length ? `<div class="fxnotes">${rows.join('')}</div>` : '';
}
const RESIST_ICONS = {
  ResistCold: 'ac-unit', ResistHot: 'sunny', ResistElectric: 'bolt', ResistBurn: 'local-fire-department',
  ResistFreeze: 'ac-unit', NoBurning: 'local-fire-department', ResitLightning: 'bolt',
  MiasmaGuard: 'shield', MiasmaDefenseUp: 'shield', NotSlippy: 'hiking', SwimSpeedUp: 'pool',
  ClimbSpeedUp: 'hiking', LightEmission: 'lightbulb', QuietnessUp: 'visibility-off',
};
function resistanceBadges(list, cls) {
  const seen = new Set();
  const out = [];
  for (const e of (list || [])) {
    const name = RESIST_ICONS[e.type];
    if (!name || seen.has(name)) continue;
    seen.add(name);
    out.push(micon(name, e.name, cls));
  }
  return out.length ? `<span class="resists">${out.join('')}</span>` : '';
}

function slotLabel(slot) {
  return slot === 'Head' ? 'Head' : slot === 'Upper' ? 'Body' : 'Legs';
}

function renderArmorDetail(p) {
  const el = $('#armor-detail');
  if (!p) { el.innerHTML = ''; return; }
  const owned = !!p.owned;
  const current = p.current;
  const ranks = (p.ranks || []).slice().sort((a, b) => a.rank - b.rank);
  const currentRank = owned ? (p.owned.rank || 1) : 0;
  const panels = [];
  for (const r of ranks) {
    const upg = r.upgrade || [];
    const nextRow = r.next ? ranks.find((x) => x.actor === r.next) : null;
    if (!upg.length) continue;
    const toRank = nextRow ? nextRow.rank : r.rank + 1;
    const done = currentRank >= toRank;
    if (done) continue;
    const isNext = currentRank > 0 && r.rank === currentRank;
    const rows = upg.map((u) => {
      const have = S.matCounts[u.actor] || 0;
      const meta = ainfo(u.actor);
      return `<button class="u${have < u.n ? ' miss' : ''}" data-srcmat="${esc(u.actor)}" title="Where to find ${esc(meta.name || u.actor)}">` +
        `${art(meta, 'i')}<span class="n">${esc(meta.name || u.actor)}</span><span class="c">${have} / ${u.n}</span>` +
        `<span class="src">Sources</span></button>`;
    }).join('');
    panels.push(`<div class="upg-panel${isNext ? ' next' : ''}${done ? ' done' : ''}">` +
      `<div class="upg-head"><span class="lv">Lv ${r.rank} → ${nextRow ? nextRow.rank : 'MAX'}</span>` +
      (isNext ? '<span class="tag gold">Next</span>' : '') + `</div>` +
      `<div class="upg">${rows}</div>` +
      `<div class="grid2"><dt>Defense</dt><dd>${r.defense || 0} → ${nextRow ? nextRow.defense : (r.defense || 0)}</dd>` +
      `<dt>Rupees</dt><dd>${fmtNum(r.price)}</dd></div></div>`);
  }
  const maxRank = ranks.length ? ranks[ranks.length - 1].rank : 1;
  const upgradeBlock = panels.length
    ? `<h3 class="label">Upgrades</h3>${panels.join('')}`
    : `<p class="note">${owned && currentRank >= maxRank ? 'Fully upgraded.' : 'No upgrade materials are recorded for this piece.'}</p>`;

  const effects = current.effect_info || [];
  const effectBlock = effects.length
    ? `<h3 class="label">Piece effect</h3><div class="tagrow">${effectChips(effects, 'eff')}</div>` +
      effectNotes(effects)
    : '';

  const slotOrder = { Head: 0, Upper: 1, Lower: 2 };
  const setPieces = armorPieces().filter((x) => x.set_key === p.set_key)
    .sort((a, b) => (slotOrder[a.slot] ?? 9) - (slotOrder[b.slot] ?? 9));
  const ownedPieces = setPieces.filter((x) => x.owned);
  const bonus = current.set_bonus || [];
  const minRank = setPieces.length
    ? Math.min(...setPieces.map((x) => x.owned ? (x.owned.rank || 1) : 0)) : 0;
  const allOwned = setPieces.every((x) => x.owned);
  const multiPiece = setPieces.length > 1;
  const bonusReady = bonus.length > 0 && allOwned && minRank >= SET_BONUS_LEVEL;
  const lowPieces = setPieces.filter((x) => !x.owned || (x.owned.rank || 1) < SET_BONUS_LEVEL);
  const pieceChips = setPieces.map((x) => {
    const lvl = x.owned ? (x.owned.rank || 1) : 0;
    const cls = !x.owned ? 'no' : lvl < SET_BONUS_LEVEL ? 'low' : 'ok';
    const tip = !x.owned ? `${x.name} is not owned`
      : lvl < SET_BONUS_LEVEL ? `${x.name} is Lv ${lvl}; Lv ${SET_BONUS_LEVEL} unlocks the set bonus`
      : `${x.name} is Lv ${lvl}`;
    return `<button class="setpiece-chip" data-armor="${esc(x.base)}" title="${esc(tip)}"><span>${slotLabel(x.slot)}</span>` +
      `<b class="${cls}">${x.owned ? `Lv ${lvl}` : 'Not owned'}</b></button>`;
  }).join('');
  const defNow = setDefense(setPieces, 'now');
  const defLv2 = setDefense(setPieces, 'lv2');
  const defMax = setDefense(setPieces, 'max');
  const nowNote = !ownedPieces.length || allOwned ? '' : ', owned only';
  const stacked = fullSetEffects(setPieces);
  const stackLine = (multiPiece && stacked.length)
    ? `<div class="set-effects"><span class="lab" title="Piece effects stack as you wear more pieces of the set. Upgrading a piece adds defense, not effect levels.">Full set</span>` +
      stacked.map((x) => {
        const amount = effectAmount(x.type, x.level);
        return `<span class="set-effect"><b>${esc(x.name)}${x.level > 1 ? ` Lv. ${x.level}` : ''}</b>${amount ? `: ${esc(amount)}` : ''}</span>`;
      }).join('') + `</div>`
    : '';
  const bonusItems = bonus.map((x) => {
    const level = Math.max(1, x.level || 1);
    const detail = effectAmount(x.type, level) || effectDesc(x);
    return `<span class="bonus-item"><b>${esc(x.name)}</b>${detail ? `<span class="bd">: ${esc(detail)}</span>` : ''}</span>`;
  }).join('');
  const need = multiPiece
    ? `All ${setPieces.length} pieces at Lv ${SET_BONUS_LEVEL} unlock the bonus`
    : `Lv ${SET_BONUS_LEVEL} unlocks the bonus`;
  let bonusWhy = '';
  if (bonus.length) {
    if (bonusReady) {
      bonusWhy = `Unlocked at Lv ${SET_BONUS_LEVEL}. Lv 3 and higher add defense only; the bonus itself does not increase.`;
    } else {
      const lacking = lowPieces.map((x) => x.owned
        ? `${slotLabel(x.slot)} Lv ${x.owned.rank || 1}`
        : `${slotLabel(x.slot)} not owned`).join(', ');
      bonusWhy = `${lacking}. ${need}; Lv 3 and higher add defense only.`;
    }
  } else if (multiPiece) {
    bonusWhy = 'No set bonus. Upgrades add defense only.';
  }
  const bonusBlock = bonus.length
    ? `<div class="bonus-line"><span class="tag ${bonusReady ? 'gold' : ''}">${bonusReady ? 'Set bonus active' : `Unlocks at Lv ${SET_BONUS_LEVEL}`}</span>` +
      `${bonusItems}<span class="bonus-why">${esc(bonusWhy)}</span></div>`
    : (bonusWhy ? `<div class="bonus-line"><span class="bonus-why">${esc(bonusWhy)}</span></div>` : '');
  const setBlock = (multiPiece || bonus.length)
    ? `<h3 class="label">Set</h3><div class="setbox compact"><div class="set-head">` +
      `<span class="setname">${esc(p.set_name || 'Armor')}</span>` +
      `<span class="setpieces-inline">${pieceChips}</span></div>` +
      (multiPiece ? `<div class="set-def" title="Now counts owned pieces at their current level. Lv ${SET_BONUS_LEVEL} and max count all ${setPieces.length} pieces.">Defense <b>${defNow}</b> now${nowNote} · <b>${defLv2}</b> at all Lv ${SET_BONUS_LEVEL} · <b>${defMax}</b> at max</div>` : '') +
      stackLine + bonusBlock +
      (!allOwned ? `<div class="dim small">${ownedPieces.length} of ${setPieces.length} pieces owned.</div>` : '') +
      `</div>`
    : '';

  el.innerHTML = `<div class="in"><div class="d-head">${art({ icon: p.icon }, 'hero')}<div><h2 class="d-name">${esc(p.name)}${resistanceBadges(effects)}</h2>` +
    `<div class="d-sub">${owned ? `owned, level ${p.owned.rank || 1}` : 'not owned'}</div></div></div>` +
    `<div class="tagrow"><span class="tag">${slotLabel(p.slot)}</span>` +
    `<span class="tag">Defense ${current.defense || 0}</span>${owned ? '<span class="tag gold">Owned</span>' : ''}</div>` +
    (current.caption ? `<p class="cap">${esc(current.caption)}</p>` : '') +
    effectBlock + setBlock + upgradeBlock + `</div>`;
}

/* ------------------------------------------------------------------ sources */

function sourcePoints(entry) {
  if (!entry) return [];
  const out = [];
  for (const s of entry.sold || []) {
    if (s.x === null || s.x === undefined) continue;
    const price = s.currency === 'MinusRupee' ? `${fmtNum(s.price)} poes` : `${fmtNum(s.price)} rupees`;
    const label = s.place ? `${s.shop} · ${s.place}` : s.shop;
    out.push({ x: s.x, y: s.y, z: s.z, layer: s.layer, kind: 'buy', label: label,
               meta: `${price}${s.stock ? ` · stock ${s.stock}` : ''}` });
  }
  for (const d of entry.dropped || []) {
    for (const p of d.points || []) {
      out.push({ x: p[0], y: p[1], z: p[2], layer: p[3], kind: 'drop', label: d.enemy,
                 meta: `${Math.round(d.chance)}%${d.total ? ` · ${fmtNum(d.total)} spawns` : ''}` });
    }
  }
  for (const f of entry.found || []) {
    for (const p of f.points || []) {
      out.push({ x: p[0], y: p[1], z: p[2], layer: p[3], kind: 'found', label: f.name,
                 meta: `${fmtNum(f.total)} spots` });
    }
  }
  return out;
}

function openSources(actor) {
  const entry = (cat().material_sources || {})[actor];
  if (!entry) return;
  S.sourceActor = actor;
  S.sourceModal = true;
  S.modal = false;
  $('#settings').hidden = true;
  const settingsBtn = $('#btn-settings');
  if (settingsBtn) settingsBtn.setAttribute('aria-pressed', 'false');
  const el = $('#sources');
  el.hidden = false;
  renderSources();
}

function closeSources() {
  S.sourceModal = false;
  const el = $('#sources');
  if (el) el.hidden = true;
}

function renderSources() {
  const el = $('#sources');
  const actor = S.sourceActor;
  const entry = (cat().material_sources || {})[actor];
  if (!entry) { el.innerHTML = ''; return; }
  const p = playerPos();
  const points = sourcePoints(entry);
  const icon = entry.icon ? `<img src="companion_data/icons/${encodeURIComponent(entry.icon)}" alt="">` : '';
  const used = (entry.used_in || []).length;
  const rows = [];
  for (const s of entry.sold || []) {
    const d = s.x === null || s.x === undefined ? null : (p ? dist3(p, s) : null);
    const price = s.currency === 'MinusRupee' ? `${fmtNum(s.price)} poes` : `${fmtNum(s.price)} rupees`;
    const label = s.place ? `${s.shop} · ${s.place}` : s.shop;
    rows.push(`<div class="src-row"><span class="tag buy">Buy</span><span class="srcl"><b>${esc(label)}</b>` +
      `<span>${esc(price)}${s.stock ? ` · stock ${s.stock}` : ''}</span></span>` +
      `<span class="srcd">${d === null ? '' : fmtDist(d)}</span>` +
      (s.x === null ? '<span></span>' : `<button class="btn tiny" data-srcgroup="buy" data-srclabel="${esc(label)}">Map</button>`) + `</div>`);
  }
  for (const d of entry.dropped || []) {
    let near = null;
    for (const q of d.points || []) {
      if (!p) break;
      const dist = dist3(p, { x: q[0], y: q[1], z: q[2] });
      if (near === null || dist < near) near = dist;
    }
    rows.push(`<div class="src-row"><span class="tag drop">Drop</span><span class="srcl"><b>${esc(d.enemy)}</b>` +
      `<span>${Math.round(d.chance)}%${d.total ? ` · ${fmtNum(d.total)} spawns` : ''}</span></span>` +
      `<span class="srcd">${near === null ? '' : fmtDist(near)}</span>` +
      `<button class="btn tiny" data-srcgroup="drop" data-srclabel="${esc(d.enemy)}">Map</button></div>`);
  }
  for (const f of entry.found || []) {
    let near = null;
    for (const q of f.points || []) {
      if (!p) break;
      const dist = dist3(p, { x: q[0], y: q[1], z: q[2] });
      if (near === null || dist < near) near = dist;
    }
    rows.push(`<div class="src-row"><span class="tag found">Find</span><span class="srcl"><b>${esc(f.name)}</b>` +
      `<span>${fmtNum(f.total)} spots</span></span>` +
      `<span class="srcd">${near === null ? '' : fmtDist(near)}</span>` +
      `<button class="btn tiny" data-srcgroup="found">Map</button></div>`);
  }
  const notes = (entry.notes || []).map((n) => `<p class="src-note">${esc(n)}</p>`).join('');
  el.innerHTML = `<div class="modal-card src-card">` +
    `<div class="src-head">${icon}<div><h2>${esc(entry.name)}</h2>` +
    `<div class="sub">Used in ${used} armor upgrade${used === 1 ? '' : 's'} · ${fmtNum(entry.need)} needed</div></div>` +
    `<button class="btn" data-srcclose>Close</button></div>` +
    `<div class="src-counts"><span><b>${(entry.sold || []).length}</b> ${(entry.sold || []).length === 1 ? 'shop' : 'shops'}</span>` +
    `<span><b>${(entry.dropped || []).length}</b> ${(entry.dropped || []).length === 1 ? 'enemy type' : 'enemy types'}</span>` +
    `<span><b>${(entry.found || []).reduce((n, f) => n + (f.total || 0), 0)}</b> world spots</span>` +
    `<span><b>${points.length}</b> map pins</span></div>` +
    (rows.length ? `<div class="src-list">${rows.join('')}</div>` : '') + notes +
    `<div class="actions"><button class="btn" data-srcshow="all"${points.length ? '' : ' disabled'}>Show all on map</button>` +
    `<button class="btn" data-srcshow="near"${points.length ? '' : ' disabled'}>Nearest on map</button></div></div>`;
}

function loadSourceIcon(actor) {
  const entry = (cat().material_sources || {})[actor];
  if (!entry || !entry.icon) return;
  const key = 'source:' + actor;
  if (S.map.iconImages[key]) return;
  const img = new Image();
  img.decoding = 'async';
  img.onload = () => requestDraw();
  img.src = 'companion_data/icons/' + encodeURIComponent(entry.icon);
  S.map.iconImages[key] = img;
}

function showMaterialSources(actor, mode) {
  const entry = (cat().material_sources || {})[actor];
  if (!entry) return;
  let points = sourcePoints(entry);
  if (!points.length) return;
  const p = playerPos();
  if (p) points.sort((a, b) => dist3(p, a) - dist3(p, b));
  const total = points.length;
  if (mode === 'near') points = points.slice(0, 1);
  else if (mode === 'one') points = points.slice(0, 1);
  else points = points.slice(0, 600);
  loadSourceIcon(actor);
  S.map.sources = points;
  S.map.sourceMat = actor;
  S.map.sourceSel = null;
  S.map.sourceTotal = total;
  S.map.sel = null;
  const layers = {};
  for (const p of points) layers[p.layer] = (layers[p.layer] || 0) + 1;
  const layer = Object.keys(layers).sort((a, b) => layers[b] - layers[a])[0] || points[0].layer;
  S.map.layer = layer;
  S.map.layerSet = true;
  S.map.fitted = true;
  closeSources();
  showPage('map');
  requestAnimationFrame(() => {
    if (mode === 'near') centerOnPoint(points[0]);
    else fitSources(points.filter((p) => p.layer === layer));
    drawMap();
  });
}

function showSourceGroup(actor, kind, label) {
  const entry = (cat().material_sources || {})[actor];
  if (!entry) return;
  let points = sourcePoints(entry);
  if (kind === 'drop') points = points.filter((x) => x.kind === 'drop' && x.label === label);
  else if (kind === 'found') points = points.filter((x) => x.kind === 'found');
  else points = points.filter((x) => x.kind === 'buy' && (!label || x.label === label));
  if (!points.length) return;
  const p = playerPos();
  if (p) points.sort((a, b) => dist3(p, a) - dist3(p, b));
  const total = points.length;
  points = points.slice(0, 600);
  loadSourceIcon(actor);
  S.map.sources = points;
  S.map.sourceMat = actor;
  S.map.sourceSel = null;
  S.map.sourceTotal = total;
  S.map.sel = null;
  S.map.layer = points[0].layer;
  S.map.layerSet = true;
  S.map.fitted = true;
  closeSources();
  showPage('map');
  requestAnimationFrame(() => { centerOnPoint(points[0]); drawMap(); });
}

function clearSources() {
  S.map.sources = [];
  S.map.sourceMat = null;
  S.map.sourceSel = null;
  S.map.sourceTotal = 0;
  renderMapDetail();
  drawMap();
}

function sourceKindLabel(kind) {
  return kind === 'buy' ? 'Sold' : kind === 'drop' ? 'Dropped' : 'Found';
}

/* ------------------------------------------------------------------ map */

function playerLayer() {
  const st = dyn().status || {};
  const l = st.layer || st.map_layer;
  return l === 'Sky' ? 'sky' : l === 'UnderGround' ? 'depths' : 'surface';
}
function projection() {
  const m = cat().map;
  const w = m.world;
  return {
    x: (x) => ((x - w.x_min) / (w.x_max - w.x_min)) * m.width,
    y: (z) => ((z - w.z_min) / (w.z_max - w.z_min)) * m.height,
  };
}
function mapItemState(index) {
  const c = dyn().completion;
  if (!c || !c.states || index >= c.states.length) return 0;
  return c.states[index];
}
function mapVisible() {
  const m = cat().map;
  if (!m) return [];
  const states = (dyn().completion && dyn().completion.states) || [];
  const out = [];
  for (let i = 0; i < (cat().collectibles || []).length; i++) {
    const it = cat().collectibles[i];
    if (it.layer !== S.map.layer || it.map_hidden) continue;
    if (!S.map.cats.has(it.cat)) continue;
    const st = states[i] || 0;
    const only = mapOnly(it.cat);
    if (!only && !FAST_TRAVEL_CATS.has(it.cat)) {
      if (S.map.found === 'missing' && st !== 0) continue;
      if (S.map.found === 'found' && st === 0) continue;
    }
    out.push({ item: it, index: i, state: st, mapOnly: only });
  }
  return out;
}
function searchResults() {
  const q = S.map.search.trim();
  if (!q) return [];
  const p = playerPos();
  const states = (dyn().completion && dyn().completion.states) || [];
  const out = [];
  for (let i = 0; i < (cat().collectibles || []).length; i++) {
    const it = cat().collectibles[i];
    if (it.map_hidden) continue;
    const st = states[i] || 0;
    const only = mapOnly(it.cat);
    if (!only && !FAST_TRAVEL_CATS.has(it.cat)) {
      if (S.map.found === 'missing' && st !== 0) continue;
      if (S.map.found === 'found' && st === 0) continue;
    }
    const score = Math.max(fuzzyScore(q, it.name),
                           fuzzyScore(q, catMeta(it.cat).label) * 0.55);
    if (score > 0) out.push({ item: it, index: i, state: st, score: score, mapOnly: only });
  }
  out.sort((a, b) => b.score - a.score ||
    (p ? dist3(p, a.item) - dist3(p, b.item) : 0) ||
    a.item.name.localeCompare(b.item.name));
  return out;
}
function activeRevealSets() {
  const comp = dyn().completion;
  if (S.map.activeReveal && S.map.activeRevealFor === comp) return S.map.activeReveal;
  const states = (comp && comp.states) || [];
  const towers = new Set();
  const depths = new Set();
  const items = cat().collectibles || [];
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if ((states[i] || 0) < 2) continue;
    if (it.cat === 'towers') {
      let n = Number(String(it.internal || '').slice(-2));
      if (!n) n = Number(it.tower || 0);
      if (n) towers.add(String(n));
    } else if (it.cat === 'lightroots' && it.region) depths.add(it.region);
  }
  S.map.activeReveal = { towers, depths };
  S.map.activeRevealFor = comp;
  return S.map.activeReveal;
}

function activeRevealRegions() {
  const meta = cat().map_regions;
  if (!meta) return [];
  const active = activeRevealSets();
  if (S.map.layer === 'depths') {
    return (meta.depths || []).filter((r) => (r.owners || []).some((o) => active.depths.has(o)));
  }
  return (meta.towers || []).filter((r) => active.towers.has(String(r.tower)));
}

function drawRevealPaths(ctx, px, py) {
  const regions = activeRevealRegions();
  if (!regions.length) return;
  ctx.fillStyle = '#fff';
  for (const region of regions) {
    ctx.beginPath();
    for (const poly of region.polys || []) {
      const rings = [poly.outer].concat(poly.holes || []);
      for (const ring of rings) {
        if (!ring || ring.length < 3) continue;
        ctx.moveTo(px(ring[0][0]), py(ring[0][1]));
        for (let i = 1; i < ring.length; i++) ctx.lineTo(px(ring[i][0]), py(ring[i][1]));
        ctx.closePath();
      }
    }
    ctx.fill('evenodd');
  }
}

function mapLayerCounts(layer) {
  const out = {};
  const states = (dyn().completion && dyn().completion.states) || [];
  for (let i = 0; i < (cat().collectibles || []).length; i++) {
    const it = cat().collectibles[i];
    if (it.layer !== layer || it.map_hidden) continue;
    if (!out[it.cat]) out[it.cat] = { total: 0, complete: 0 };
    out[it.cat].total++;
    if ((states[i] || 0) >= 2) out[it.cat].complete++;
  }
  return out;
}
function playerPos() { return dyn().status && dyn().status.position; }

function setMapLayer(layer, keep) {
  if (S.map.layer === layer && keep) return;
  S.map.layer = layer;
  S.map.sel = null;
  S.map.sourceSel = null;
  S.map.pending = null;
  renderMapToolbar();
  renderMapCats();
  renderMapDetail();
  renderNearby();
  loadMapImage();
  if (layer === playerLayer()) showPlayerPing();
  drawMap();
}
function loadMapImage() {
  const m = cat().map;
  if (!m) return;
  const layer = m.layers[S.map.layer];
  if (!layer) return;
  const img = $('#map-img');
  img.style.width = m.width + 'px';
  img.style.height = m.height + 'px';
  const src = 'companion_data/' + layer.image;
  if (img.dataset.layer === S.map.layer && img.src) { drawMap(); return; }
  img.dataset.layer = S.map.layer;
  const mini = $('#minimap-img');
  if (mini) {
    mini.onload = () => requestMinimapDraw();
    mini.src = src;
  }
  $('#map-loading').hidden = false;
  img.onerror = () => {
    $('#map-loading').hidden = true;
    drawMap();
  };
  img.onload = () => {
    $('#map-loading').hidden = true;
    if (S.map.pending) { const p = S.map.pending; S.map.pending = null; centerOnItem(p); }
    else if (!S.map.fitted) { if (fitMap()) S.map.fitted = true; }
    drawMap();
  };
  img.onerror = () => {
    $('#map-loading').textContent = 'Map image not built. Run build_companion_data.py.';
  };
  img.src = src;
}
function renderMap() {
  if (!cat().map) {
    $('#map-viewport').innerHTML = '<div class="empty"><b>No map data</b>Run build_companion_data.py to build the map tiles.</div>';
    return;
  }
  if (!S.map.layerSet) {
    S.map.layer = playerLayer();
    S.map.layerSet = true;
  }
  renderMapToolbar();
  renderMapCats();
  renderMapDetail();
  renderNearby();
  loadMapImage();
  if (S.map.path && !S.map.pathData) {
    ensureHeroPath().then(() => drawMap());
  }
  if (S.map.layer === playerLayer()) showPlayerPing();
  requestAnimationFrame(() => { if (!S.map.fitted) { if (fitMap()) S.map.fitted = true; } else drawMap(); });
}
function renderMapToolbar() {
  const layers = [['depths', 'Depths', 'dark-mode'], ['surface', 'Surface', 'landscape'], ['sky', 'Sky', 'cloud']];
  $('#map-layers').innerHTML = layers.map(([k, l, ic]) =>
    `<button data-layer="${k}" aria-pressed="${S.map.layer === k}" title="${l}" aria-label="${l}">${micon(ic, l)}</button>`).join('');
  const found = [['all', 'All', 'select-all'], ['missing', 'Missing', 'radio-button-unchecked'], ['found', 'Found', 'check-circle']];
  $('#map-found').innerHTML = found.map(([k, l, ic]) =>
    `<button data-found="${k}" aria-pressed="${S.map.found === k}" title="${l}" aria-label="${l}">${micon(ic, l)}</button>`).join('');
  const actions = $('.map-cat-actions');
  if (actions) {
    actions.innerHTML = `<button data-mcats="all" title="Show all marker types" aria-label="Show all marker types">${micon('visibility')}</button>` +
      `<button data-mcats="none" title="Hide all marker types" aria-label="Hide all marker types">${micon('visibility-off')}</button>`;
  }
  const zoomIn = $('#map-zoomin');
  if (zoomIn) zoomIn.innerHTML = micon('add');
  const zoomOut = $('#map-zoomout');
  if (zoomOut) zoomOut.innerHTML = micon('remove');
  const fit = $('#map-fit');
  if (fit) fit.innerHTML = micon('fit-screen');
  const me = $('#map-me');
  if (me) me.innerHTML = micon('my-location');
  $('#map-search').value = S.map.search;
  const reveal = $('#map-reveal');
  if (reveal) reveal.checked = !!S.map.reveal;
  const path = $('#map-path');
  if (path) path.checked = !!S.map.path;
  renderMapPathNote();
  updateSearchClear();
}

function renderMapPathNote() {
  const el = $('#map-path-note');
  if (!el) return;
  const data = S.map.pathData;
  if (!S.map.path) { el.hidden = true; el.textContent = ''; return; }
  if (!data) {
    el.hidden = false;
    el.textContent = S.map.pathLoading ? 'Reading footprint.sav...' : "No Hero's Path data in this save yet.";
    return;
  }
  const km = (data.distance || 0) / 1000;
  el.hidden = false;
  el.textContent = `${fmtNum(data.points)} points · ${km.toFixed(1)} km · ${fmtNum(data.deaths_count)} deaths`;
}

async function ensureHeroPath() {
  if (S.map.pathData && S.map.pathFor === S.dataVersion) return S.map.pathData;
  if (S.map.pathLoading) return null;
  S.map.pathLoading = true;
  renderMapPathNote();
  try {
    const data = await call('hero_path');
    S.map.pathData = data || null;
    S.map.pathFor = S.dataVersion;
  } finally {
    S.map.pathLoading = false;
    renderMapPathNote();
  }
  return S.map.pathData;
}
function updateSearchClear() {
  const btn = $('#map-search-clear');
  const input = $('#map-search');
  if (btn && input) btn.hidden = !input.value;
}
function renderMapCats() {
  const counts = mapLayerCounts(S.map.layer);
  const el = $('#map-cats');
  const allMedals = dyn().travel_medallions || [];
  const medIcon = ainfo('Obj_WarpDLC_Prototype').icon;
  const medRow = allMedals.length
    ? `<button class="map-cat medal-toggle" data-mmedals="1" aria-pressed="${S.map.medals}">` +
      `${medIcon ? `<img class="mico" src="companion_data/icons/${encodeURIComponent(medIcon)}" alt="">` : ''}` +
      `<span>Travel medallions</span><span class="n">${allMedals.length}</span></button>`
    : '';
  const ordered = (cat().collectible_categories || []).filter((c) => counts[c.key])
    .sort((a, b) => (MAP_CAT_RANK.has(a.key) ? MAP_CAT_RANK.get(a.key) : 999) -
                    (MAP_CAT_RANK.has(b.key) ? MAP_CAT_RANK.get(b.key) : 999) ||
                    a.label.localeCompare(b.label));
  el.innerHTML = medRow + ordered.map((c) => {
    const n = counts[c.key];
    const iconFile = (cat().map_icons || {})[c.key];
    const marker = iconFile
      ? `<img class="mico" src="companion_data/${encodeURI(iconFile)}" alt="">`
      : '';
    const count = c.map_only ? n.total : `${n.complete}/${n.total}`;
    return `<button class="map-cat" data-mcat="${c.key}" aria-pressed="${S.map.cats.has(c.key)}">` +
      `${marker}<span>${esc(c.label)}</span><span class="n">${count}</span></button>`;
  }).join('');
}
function renderMapDetail() {
  const el = $('#map-detail');
  const id = S.map.sel;
  if (id) {
    const item = (cat().collectibles || []).find((x) => x.id === id);
    if (!item) { el.innerHTML = ''; el.hidden = true; return; }
    el.hidden = false;
    const idx = (cat().collectibles || []).indexOf(item);
    const st = mapItemState(idx);
    const meta = catMeta(item.cat);
    const only = !!meta.map_only;
    const p = playerPos();
    const d = p ? dist3(p, item) : null;
    const deg = p ? bearing(p, item) : null;
    const state = st >= 2 ? 'Complete' : st === 1 ? 'Started' : 'Missing';
    const iconFile = mapIconFile(item.cat, st);
    el.innerHTML = `<div class="md-head">${iconFile ? `<img src="companion_data/${encodeURI(iconFile)}" alt="">` : ''}<div><h2>${esc(item.name)}</h2><div class="d-sub">${esc(meta.label)} · ${layerLabel(item.layer)}</div></div></div>` +
      (only ? '' : `<div class="k">Status</div><div class="v">${state}</div>`) +
      `<div class="k">Position</div><div class="v">${fmtXYZ(item.x, item.y, item.z)}</div>` +
      (d !== null ? `<div class="k">From Link</div><div class="v">${fmtDist(d)}${dirIcon(deg)}<span class="dir-label">${cardinal(deg)}</span></div>` : '') +
      `<div class="actions" style="margin-top:10px"><button class="btn" data-mcenter="${esc(item.id)}">${micon('my-location', '', 'sm')} Center</button>` +
      (only ? '' : `<button class="btn" data-mprogress="${esc(item.cat)}">${micon('format-list-bulleted', '', 'sm')} All ${esc(meta.label.toLowerCase())}</button>`) +
      `</div>`;
    return;
  }
  if (S.map.sourceSel !== null && S.map.sources[S.map.sourceSel]) {
    renderSourceDetail();
    return;
  }
  if (S.map.sourceMat) {
    renderSourceSummary();
    return;
  }
  el.innerHTML = '';
  el.hidden = true;
}
function renderSourceSummary() {
  const el = $('#map-detail');
  const entry = (cat().material_sources || {})[S.map.sourceMat];
  if (!entry) { el.innerHTML = ''; el.hidden = true; return; }
  el.hidden = false;
  const p = playerPos();
  const nearest = p && S.map.sources.length ? S.map.sources[0] : null;
  const nearestDeg = nearest ? bearing(p, nearest) : null;
  const onLayer = S.map.sources.filter((x) => x.layer === S.map.layer).length;
  const icon = entry.icon ? `<img src="companion_data/icons/${encodeURIComponent(entry.icon)}" alt="">` : '';
  el.innerHTML = `<div class="md-head">${icon}<div><h2>${esc(entry.name)}</h2>` +
    `<div class="d-sub">Source pins · ${onLayer} on ${layerLabel(S.map.layer)} of ${fmtNum(S.map.sourceTotal)}</div></div></div>` +
    `<div class="k">Sold</div><div class="v">${(entry.sold || []).length} ${(entry.sold || []).length === 1 ? 'shop' : 'shops'}</div>` +
    `<div class="k">Dropped</div><div class="v">${(entry.dropped || []).length} ${(entry.dropped || []).length === 1 ? 'enemy type' : 'enemy types'}</div>` +
    `<div class="k">Found</div><div class="v">${(entry.found || []).reduce((n, f) => n + (f.total || 0), 0)} spots</div>` +
    (nearest && p ? `<div class="k">Nearest</div><div class="v">${fmtDist(dist3(p, nearest))}${dirIcon(nearestDeg)}<span class="dir-label">${cardinal(nearestDeg)}</span></div>` : '') +
    `<div class="actions" style="margin-top:10px"><button class="btn" data-srcclear>Clear sources</button></div>`;
}
function renderSourceDetail() {
  const el = $('#map-detail');
  const entry = (cat().material_sources || {})[S.map.sourceMat];
  const point = S.map.sources[S.map.sourceSel];
  if (!entry || !point) { el.innerHTML = ''; el.hidden = true; return; }
  el.hidden = false;
  const p = playerPos();
  const d = p ? dist3(p, point) : null;
  const deg = p ? bearing(p, point) : null;
  const icon = entry.icon ? `<img src="companion_data/icons/${encodeURIComponent(entry.icon)}" alt="">` : '';
  el.innerHTML = `<div class="md-head">${icon}<div><h2>${esc(entry.name)}</h2>` +
    `<div class="d-sub">${sourceKindLabel(point.kind)} · ${layerLabel(point.layer)}</div></div></div>` +
    `<div class="k">Where</div><div class="v">${esc(point.label)}</div>` +
    `<div class="k">Detail</div><div class="v">${esc(point.meta)}</div>` +
    `<div class="k">Position</div><div class="v">${fmtXYZ(point.x, point.y, point.z)}</div>` +
    (d !== null ? `<div class="k">From Link</div><div class="v">${fmtDist(d)}${dirIcon(deg)}<span class="dir-label">${cardinal(deg)}</span></div>` : '') +
    `<div class="actions" style="margin-top:10px"><button class="btn" data-srcclear>Clear sources</button></div>`;
}
function renderResultsNote(searching) {
  const note = $('#map-results-note');
  if (!note) return;
  if (!searching) { note.hidden = true; note.innerHTML = ''; return; }
  if (S.map.found === 'all') { note.hidden = true; note.innerHTML = ''; return; }
  note.hidden = false;
  note.innerHTML = `<span><b>${S.map.found === 'found' ? 'Found' : 'Missing'}</b> only for collectibles · fast travel always shown</span>` +
    '<button data-maprelax="found">Show all types</button>';
}

function renderNearby() {
  const el = $('#map-nearby');
  const title = $('#map-near-title');
  const p = playerPos();
  const searching = S.map.search.trim() !== '';
  renderResultsNote(searching);
  let items = searching ? searchResults() : mapVisible();
  if (!searching) {
    items.sort((a, b) => {
      if (p) {
        const da = dist3(p, a.item), db = dist3(p, b.item);
        if (da !== db) return da - db;
      }
      return a.item.name.localeCompare(b.item.name);
    });
  }
  const total = items.length;
  items = items.slice(0, searching ? 60 : 40);
  if (!items.length) {
    if (title) title.hidden = true;
    el.hidden = true;
    el.innerHTML = '';
    return;
  }
  if (title) { title.hidden = false; title.textContent = searching ? `Results (${total})` : 'Near Link'; }
  el.hidden = false;
  el.innerHTML = items.map((x) => {
    const d = p ? dist3(p, x.item) : null;
    const deg = p ? bearing(p, x.item) : null;
    const meta = catMeta(x.item.cat);
    const only = !!meta.map_only;
    const state = only ? '' : x.state >= 2 ? 'Complete' : x.state === 1 ? 'Started' : 'Missing';
    const iconFile = mapIconFile(x.item.cat, x.state);
    const layer = x.item.layer !== S.map.layer ? layerLabel(x.item.layer) : '';
    const metaText = [meta.label, state, layer].filter(Boolean).join(' · ');
    return `<button data-midx="${x.index}">` +
      (iconFile ? `<img class="nico" src="companion_data/${encodeURI(iconFile)}" alt="">` : '<span></span>') +
      `<span><span>${esc(x.item.name)}</span>` +
      `<span class="meta">${esc(metaText)}</span></span>` +
      `<span class="dist">${dirIcon(deg)}${d === null ? '' : ` ${fmtDist(d)}`}</span></button>`;
  }).join('');
}
function fitMap() {
  const m = cat().map;
  if (!m) return false;
  const vp = $('#map-viewport');
  const w = vp.clientWidth, h = vp.clientHeight;
  if (!w || !h) return false;
  S.map.zoom = Math.min(w / m.width, h / m.height) * 0.98;
  S.map.tx = (w - m.width * S.map.zoom) / 2;
  S.map.ty = (h - m.height * S.map.zoom) / 2;
  applyMap();
  return true;
}
function fitSources(points) {
  const m = cat().map;
  if (!m || !points.length) return;
  const vp = $('#map-viewport');
  const pr = projection();
  let minx = Infinity, maxx = -Infinity, minz = Infinity, maxz = -Infinity;
  for (const p of points) {
    minx = Math.min(minx, p.x); maxx = Math.max(maxx, p.x);
    minz = Math.min(minz, p.z); maxz = Math.max(maxz, p.z);
  }
  const x1 = pr.x(minx), x2 = pr.x(maxx), y1 = pr.y(minz), y2 = pr.y(maxz);
  const pad = 90;
  const z = clamp(Math.min((vp.clientWidth - pad * 2) / Math.max(1, x2 - x1),
                           (vp.clientHeight - pad * 2) / Math.max(1, y2 - y1)), 0.02, 2);
  S.map.zoom = z;
  S.map.tx = vp.clientWidth / 2 - ((x1 + x2) / 2) * z;
  S.map.ty = vp.clientHeight / 2 - ((y1 + y2) / 2) * z;
  S.map.pending = null;
  S.map.fitted = true;
  applyMap();
  renderMapDetail();
}
function applyMap() {
  const img = $('#map-img');
  if (img) img.style.transform = `translate(${S.map.tx}px, ${S.map.ty}px) scale(${S.map.zoom})`;
  requestDraw();
  requestMinimapDraw();
}
function zoomAt(factor, cx, cy) {
  const vp = $('#map-viewport');
  const rect = vp.getBoundingClientRect();
  const mx = (cx === undefined ? rect.width / 2 : cx - rect.left);
  const my = (cy === undefined ? rect.height / 2 : cy - rect.top);
  const z = clamp(S.map.zoom * factor, 0.08, 10);
  const k = z / S.map.zoom;
  S.map.tx = mx - (mx - S.map.tx) * k;
  S.map.ty = my - (my - S.map.ty) * k;
  S.map.zoom = z;
  applyMap();
}
function centerOnItem(item) {
  const m = cat().map;
  if (!m) return;
  if (item.layer !== S.map.layer) {
    S.map.layer = item.layer;
    renderMapToolbar(); renderMapCats(); loadMapImage();
  }
  const pr = projection();
  const vp = $('#map-viewport');
  const z = Math.max(S.map.zoom, 1.25);
  S.map.zoom = z;
  S.map.tx = vp.clientWidth / 2 - pr.x(item.x) * z;
  S.map.ty = vp.clientHeight / 2 - pr.y(item.z) * z;
  S.map.sel = item.id;
  S.map.pending = null;
  S.map.fitted = true;
  applyMap();
  renderMapDetail(); renderNearby();
}
function centerOnPoint(point) {
  if (!point) return;
  if (S.map.layer !== point.layer) {
    S.map.layer = point.layer;
    renderMapToolbar(); renderMapCats(); loadMapImage();
  }
  const pr = projection();
  const vp = $('#map-viewport');
  const z = Math.max(S.map.zoom, 1.25);
  S.map.zoom = z;
  S.map.tx = vp.clientWidth / 2 - pr.x(point.x) * z;
  S.map.ty = vp.clientHeight / 2 - pr.y(point.z) * z;
  S.map.pending = null;
  S.map.fitted = true;
  applyMap();
  renderMapDetail();
}

function centerOnPlayer() {
  const p = playerPos();
  if (!p) return;
  if (S.map.layer !== playerLayer()) {
    S.map.layer = playerLayer();
    renderMapToolbar(); renderMapCats(); loadMapImage();
  }
  const m = cat().map;
  const pr = projection();
  const vp = $('#map-viewport');
  const z = S.map.zoom;
  const fitZ = Math.min(vp.clientWidth / m.width, vp.clientHeight / m.height) * 0.98;
  if (z <= fitZ * 1.02) {
    showPlayerPing();
    drawMap();
    return;
  }
  S.map.zoom = z;
  S.map.tx = vp.clientWidth / 2 - pr.x(p.x) * z;
  S.map.ty = vp.clientHeight / 2 - pr.y(p.z) * z;
  S.map.pending = null;
  S.map.fitted = true;
  applyMap();
  showPlayerPing();
  drawMap();
}
function showPlayerPing(ms) {
  if (!playerPos()) return;
  const duration = ms || 3200;
  S.map.pingUntil = performance.now() + duration;
  if (S.map.pingTimer) clearTimeout(S.map.pingTimer);
  S.map.pingTimer = setTimeout(() => {
    S.map.pingTimer = 0;
    S.map.pingUntil = 0;
    const el = $('#player-ping');
    if (el) el.hidden = true;
  }, duration);
  requestDraw();
}
function requestDraw() {
  if (S.map.raf) return;
  S.map.raf = requestAnimationFrame(() => { S.map.raf = 0; drawMap(); });
}
function drawFog(ctx, w, h) {
  if (S.map.reveal || !cat().map_regions) return;
  ctx.save();
  ctx.fillStyle = 'rgba(3,7,14,.99)';
  ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = 'destination-out';
  ctx.translate(S.map.tx, S.map.ty);
  ctx.scale(S.map.zoom, S.map.zoom);
  const pr = projection();
  drawRevealPaths(ctx, pr.x, pr.y);
  ctx.restore();
}

function drawHeroPath(ctx, w, h, pr) {
  const data = S.map.pathData;
  if (!S.map.path || !data) return;
  const layer = S.map.layer === 'depths' ? 2 : S.map.layer === 'sky' ? 0 : 1;
  const color = S.map.layer === 'depths' ? 'rgba(255, 143, 188, .62)'
    : S.map.layer === 'sky' ? 'rgba(255, 212, 121, .62)' : 'rgba(143, 231, 255, .62)';
  ctx.save();
  ctx.translate(S.map.tx, S.map.ty);
  ctx.scale(S.map.zoom, S.map.zoom);
  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(1.2, 2.2 / S.map.zoom);
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  for (const seg of data.segments || []) {
    if (seg.layer !== layer || !seg.points || seg.points.length < 4) continue;
    ctx.beginPath();
    ctx.moveTo(pr.x(seg.points[0]), pr.y(seg.points[1]));
    for (let i = 2; i < seg.points.length; i += 2) {
      ctx.lineTo(pr.x(seg.points[i]), pr.y(seg.points[i + 1]));
    }
    ctx.stroke();
  }
  ctx.fillStyle = 'rgba(233, 122, 106, .9)';
  for (const d of data.deaths || []) {
    if (d.layer !== layer) continue;
    ctx.beginPath();
    ctx.arc(pr.x(d.x), pr.y(d.z), Math.max(2, 4 / S.map.zoom), 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawMap() {
  const m = cat().map;
  if (!m) return;
  const vp = $('#map-viewport');
  const canvas = $('#map-canvas');
  const w = vp.clientWidth, h = vp.clientHeight;
  if (!w || !h) return;
  const dpr = window.devicePixelRatio || 1;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const pr = projection();
  if (!S.map.reveal) drawFog(ctx, w, h);
  drawHeroPath(ctx, w, h, pr);
  const items = mapVisible();
  const pts = [];
  for (const x of items) {
    const sx = S.map.tx + pr.x(x.item.x) * S.map.zoom;
    const sy = S.map.ty + pr.y(x.item.z) * S.map.zoom;
    if (sx < -20 || sy < -20 || sx > w + 20 || sy > h + 20) continue;
    pts.push({ x: x, sx: sx, sy: sy });
  }
  pts.sort((a, b) => (b.x.state - a.x.state) || (a.x.item.id === S.map.sel ? 1 : 0) - (b.x.item.id === S.map.sel ? 1 : 0));
  const base = clamp(3.2 + Math.log2(S.map.zoom + 1) * 1.7, 3, 10);
  for (const p of pts) drawMarker(ctx, p.sx, p.sy, base, p.x, p.x.item.id === S.map.sel);
  drawSources(ctx, w, h, pr);
  drawMedallions(ctx, w, h, pr);
  // Link's position, only on the layer he is actually on.
  const pos = playerPos();
  const ping = $('#player-ping');
  const pingActive = S.map.pingUntil > performance.now();
  let pingShown = false;
  if (pos && S.map.layer === playerLayer()) {
    const sx = S.map.tx + pr.x(pos.x) * S.map.zoom;
    const sy = S.map.ty + pr.y(pos.z) * S.map.zoom;
    if (sx > -30 && sy > -30 && sx < w + 30 && sy < h + 30) {
      drawPlayer(ctx, sx, sy);
      if (pingActive && ping) {
        ping.style.transform = `translate(${sx}px, ${sy}px)`;
        ping.hidden = false;
        pingShown = true;
      }
    }
  }
  if (ping && !pingShown) ping.hidden = true;
  requestMinimapDraw();
}

function requestMinimapDraw() {
  if (S.map.miniRAF) return;
  S.map.miniRAF = requestAnimationFrame(() => { S.map.miniRAF = 0; drawMinimap(); });
}

function drawMinimapFog(ctx, w, h, m) {
  if (S.map.reveal || !cat().map_regions) return;
  const xr = m.world.x_max - m.world.x_min;
  const zr = m.world.z_max - m.world.z_min;
  ctx.save();
  ctx.fillStyle = 'rgba(3,7,14,.99)';
  ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = 'destination-out';
  drawRevealPaths(ctx,
    (x) => (x - m.world.x_min) / xr * w,
    (z) => (z - m.world.z_min) / zr * h);
  ctx.restore();
}

function drawMinimap() {
  const m = cat().map;
  if (!m) return;
  const box = $('#minimap');
  const canvas = $('#minimap-canvas');
  if (!box || !canvas) return;
  const w = box.clientWidth, h = box.clientHeight;
  if (!w || !h) return;
  const dpr = window.devicePixelRatio || 1;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const img = $('#minimap-img');
  if (img && img.complete && img.naturalWidth) {
    ctx.drawImage(img, 0, 0, w, h);
  } else {
    ctx.fillStyle = '#06090c';
    ctx.fillRect(0, 0, w, h);
  }
  if (!S.map.reveal) drawMinimapFog(ctx, w, h, m);
  const vp = $('#map-viewport');
  const vw = vp.clientWidth, vh = vp.clientHeight;
  const left = clamp((0 - S.map.tx) / S.map.zoom, 0, m.width);
  const top = clamp((0 - S.map.ty) / S.map.zoom, 0, m.height);
  const right = clamp((vw - S.map.tx) / S.map.zoom, 0, m.width);
  const bottom = clamp((vh - S.map.ty) / S.map.zoom, 0, m.height);
  const rx = left / m.width * w, ry = top / m.height * h;
  const rw = Math.max(2, (right - left) / m.width * w);
  const rh = Math.max(2, (bottom - top) / m.height * h);
  // Darken everything outside the current view, then outline it.
  ctx.fillStyle = 'rgba(4,7,10,.42)';
  ctx.fillRect(0, 0, w, ry);
  ctx.fillRect(0, ry + rh, w, h - (ry + rh));
  ctx.fillRect(0, ry, rx, rh);
  ctx.fillRect(rx + rw, ry, w - (rx + rw), rh);
  ctx.fillStyle = 'rgba(255,240,194,.10)';
  ctx.fillRect(rx, ry, rw, rh);
  ctx.strokeStyle = '#fff0c2';
  ctx.lineWidth = 2;
  ctx.strokeRect(rx, ry, rw, rh);
  const pos = playerPos();
  if (pos && S.map.layer === playerLayer()) {
    const pr = projection();
    const px = pr.x(pos.x) / m.width * w;
    const py = pr.y(pos.z) / m.height * h;
    ctx.fillStyle = '#fff0c2';
    ctx.strokeStyle = 'rgba(5,8,10,.95)';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(px, py, 4, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
  if (S.map.sel) {
    const item = cat().collectibles.find((x) => x.id === S.map.sel);
    if (item) {
      const pr = projection();
      const px = pr.x(item.x) / m.width * w;
      const py = pr.y(item.z) / m.height * h;
      ctx.fillStyle = '#7fd0ff';
      ctx.beginPath(); ctx.arc(px, py, 2.5, 0, Math.PI * 2); ctx.fill();
    }
  }
}

function minimapGoto(e) {
  const m = cat().map;
  const box = $('#minimap');
  const vp = $('#map-viewport');
  if (!m || !box || !vp) return;
  const rect = box.getBoundingClientRect();
  const mx = clamp((e.clientX - rect.left) / rect.width, 0, 1);
  const my = clamp((e.clientY - rect.top) / rect.height, 0, 1);
  S.map.tx = vp.clientWidth / 2 - mx * m.width * S.map.zoom;
  S.map.ty = vp.clientHeight / 2 - my * m.height * S.map.zoom;
  S.map.fitted = true;
  applyMap();
}
function markerRing(ctx, x, y, radius) {
  ctx.save();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = '#fff0c2';
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.stroke();
  ctx.restore();
}
function drawMarker(ctx, x, y, r, xitem, selected) {
  const it = xitem.item;
  const meta = catMeta(it.cat);
  const color = meta.color;
  const st = xitem.state;
  const iconFile = mapIconFile(it.cat, st);
  const icon = iconFile && S.map.iconImages && S.map.iconImages[iconFile];
  const alpha = 1;
  if (icon && icon.complete && icon.naturalWidth) {
    const max = clamp(14 + Math.log2(S.map.zoom + 3) * 3.2, 17, 34);
    const scale = max / Math.max(icon.naturalWidth, icon.naturalHeight);
    const dw = icon.naturalWidth * scale, dh = icon.naturalHeight * scale;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.shadowColor = 'rgba(0,0,0,.9)';
    ctx.shadowBlur = 4;
    ctx.drawImage(icon, x - dw / 2, y - dh / 2, dw, dh);
    ctx.restore();
    if (selected) markerRing(ctx, x, y, Math.max(dw, dh) / 2 + 5);
    return;
  }
  // Fallback for a category whose game texture is missing.
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = color;
  ctx.strokeStyle = 'rgba(5,8,10,.9)';
  ctx.lineWidth = Math.max(1, r * 0.28);
  ctx.beginPath();
  const kind = meta.kind;
  if (kind === 'shrine') {
    ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath();
  } else if (kind === 'lightroot') {
    ctx.arc(x, y - r * 0.12, r * 0.78, Math.PI, 0);
    ctx.lineTo(x, y + r);
    ctx.closePath();
  } else if (kind === 'korok') {
    ctx.ellipse(x, y, r * 0.78, r * 1.08, Math.PI / 4, 0, Math.PI * 2);
  } else if (kind === 'boss') {
    ctx.rect(x - r * 0.82, y - r * 0.82, r * 1.64, r * 1.64);
  } else if (kind === 'cave') {
    ctx.moveTo(x, y - r); ctx.lineTo(x + r, y + r * 0.75); ctx.lineTo(x - r, y + r * 0.75); ctx.closePath();
  } else if (kind === 'chasm') {
    ctx.moveTo(x, y + r); ctx.lineTo(x + r, y - r * 0.75); ctx.lineTo(x - r, y - r * 0.75); ctx.closePath();
  } else if (kind === 'well') {
    ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, r * 0.42, 0, Math.PI * 2);
  } else if (kind === 'treasure') {
    const spikes = 5, outer = r, inner = r * 0.46;
    for (let i = 0; i < spikes * 2; i++) {
      const rr = i % 2 === 0 ? outer : inner;
      const a = -Math.PI / 2 + i * Math.PI / spikes;
      const px = x + Math.cos(a) * rr, py = y + Math.sin(a) * rr;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
  } else {
    ctx.moveTo(x, y - r * 0.8); ctx.lineTo(x + r * 0.72, y); ctx.lineTo(x, y + r * 0.8); ctx.lineTo(x - r * 0.72, y); ctx.closePath();
  }
  ctx.fill();
  ctx.stroke();
  ctx.restore();
  if (selected) markerRing(ctx, x, y, r + 5);
}
function drawSources(ctx, w, h, pr) {
  if (!S.map.sources.length || !S.map.sourceMat) return;
  const iconKey = 'source:' + S.map.sourceMat;
  const icon = S.map.iconImages[iconKey];
  for (let i = 0; i < S.map.sources.length; i++) {
    const p = S.map.sources[i];
    if (p.layer !== S.map.layer) continue;
    const sx = S.map.tx + pr.x(p.x) * S.map.zoom;
    const sy = S.map.ty + pr.y(p.z) * S.map.zoom;
    if (sx < -30 || sy < -30 || sx > w + 30 || sy > h + 30) continue;
    drawSourceMarker(ctx, sx, sy, p, icon, i === S.map.sourceSel);
  }
}
function drawSourceMarker(ctx, x, y, point, icon, selected) {
  const color = point.kind === 'buy' ? '#e8c56a' : point.kind === 'drop' ? '#e98a7a' : '#8fd6a0';
  const r = clamp(5 + Math.log2(S.map.zoom + 3) * 1.6, 6, 16);
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(Math.PI / 4);
  ctx.fillStyle = 'rgba(6,10,8,.9)';
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.fillRect(-r, -r, r * 2, r * 2);
  ctx.strokeRect(-r, -r, r * 2, r * 2);
  if (selected) {
    ctx.strokeStyle = '#fff0c2';
    ctx.lineWidth = 2;
    ctx.strokeRect(-r - 4, -r - 4, (r + 4) * 2, (r + 4) * 2);
  }
  ctx.rotate(-Math.PI / 4);
  if (icon && icon.complete && icon.naturalWidth && S.map.zoom >= 0.18) {
    const size = r * 1.45;
    ctx.drawImage(icon, -size / 2, -size / 2, size, size);
  }
  ctx.restore();
}
function medallionLayer(y) {
  return y < -100 ? 'depths' : y > 1000 ? 'sky' : 'surface';
}

function drawMedallions(ctx, w, h, pr) {
  const list = dyn().travel_medallions || [];
  if (!S.map.medals || !list.length) return;
  const icon = S.map.iconImages.medallion;
  for (const m of list) {
    if (medallionLayer(m.y) !== S.map.layer) continue;
    const sx = S.map.tx + pr.x(m.x) * S.map.zoom;
    const sy = S.map.ty + pr.y(m.z) * S.map.zoom;
    if (sx < -30 || sy < -30 || sx > w + 30 || sy > h + 30) continue;
    const size = clamp(18 + Math.log2(S.map.zoom + 3) * 4, 20, 38);
    ctx.save();
    ctx.translate(sx, sy);
    if (icon && icon.complete && icon.naturalWidth) {
      ctx.shadowColor = 'rgba(120, 220, 255, 0.9)';
      ctx.shadowBlur = 11;
      ctx.drawImage(icon, -size / 2, -size / 2, size, size);
    } else {
      ctx.fillStyle = '#8fe7ff';
      ctx.strokeStyle = 'rgba(4, 10, 14, 0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, -size / 2);
      ctx.lineTo(size / 2, 0);
      ctx.lineTo(0, size / 2);
      ctx.lineTo(-size / 2, 0);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
  }
}

function drawPlayer(ctx, x, y) {
  const icon = S.map.iconImages && S.map.iconImages['mapicons/player.webp'];
  if (icon && icon.complete && icon.naturalWidth) {
    const size = clamp(16 + Math.log2(S.map.zoom + 3) * 2.6, 18, 34);
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,.9)';
    ctx.shadowBlur = 4;
    ctx.drawImage(icon, x - size / 2, y - size / 2, size, size);
    ctx.restore();
    return;
  }
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = '#fff0c2';
  ctx.strokeStyle = 'rgba(5,8,10,.95)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, -11); ctx.lineTo(8, 8); ctx.lineTo(0, 4); ctx.lineTo(-8, 8); ctx.closePath();
  ctx.fill(); ctx.stroke();
  ctx.restore();
}
function mapHitTest(clientX, clientY) {
  const vp = $('#map-viewport');
  const rect = vp.getBoundingClientRect();
  const mx = clientX - rect.left, my = clientY - rect.top;
  const pr = projection();
  let sbest = null, sbd = 18;
  for (let i = 0; i < S.map.sources.length; i++) {
    const p = S.map.sources[i];
    if (p.layer !== S.map.layer) continue;
    const sx = S.map.tx + pr.x(p.x) * S.map.zoom;
    const sy = S.map.ty + pr.y(p.z) * S.map.zoom;
    const d = Math.hypot(sx - mx, sy - my);
    if (d < sbd) { sbd = d; sbest = i; }
  }
  if (sbest !== null) {
    S.map.sourceSel = sbest;
    S.map.sel = null;
    renderMapDetail(); drawMap();
    return;
  }
  let best = null, bd = 15;
  for (const x of mapVisible(false)) {
    const sx = S.map.tx + pr.x(x.item.x) * S.map.zoom;
    const sy = S.map.ty + pr.y(x.item.z) * S.map.zoom;
    const d = Math.hypot(sx - mx, sy - my);
    if (d < bd) { bd = d; best = x; }
  }
  if (best) {
    S.map.sourceSel = null;
    S.map.sel = best.item.id;
    renderMapDetail(); renderNearby(); drawMap();
    return;
  }
  if (S.map.sel || S.map.sourceSel !== null) {
    S.map.sel = null;
    S.map.sourceSel = null;
    renderMapDetail(); renderNearby(); drawMap();
  }
}

function updateMapCoords(clientX, clientY) {
  const el = $('#map-coords');
  const vp = $('#map-viewport');
  const m = cat().map;
  if (!el || !vp || !m) return;
  const rect = vp.getBoundingClientRect();
  const px = (clientX - rect.left - S.map.tx) / S.map.zoom;
  const py = (clientY - rect.top - S.map.ty) / S.map.zoom;
  const x = m.world.x_min + (px / m.width) * (m.world.x_max - m.world.x_min);
  const z = m.world.z_min + (py / m.height) * (m.world.z_max - m.world.z_min);
  const y = heightAt(S.map.layer, x, z);
  el.hidden = false;
  el.textContent = `${layerLabel(S.map.layer)} · ${fmtXYZ(x, y === null ? 0 : y, z)}`;
}

/* ------------------------------------------------------------------ progress */

function renderProgress() {
  const comp = dyn().completion;
  const el = $('#progress-head');
  if (!comp) { el.innerHTML = ''; return; }
  const cats = comp.categories;
  const totals = comp.totals;
  const current = S.progress.cat;
  if (current === 'overview') {
    const overall = pct(totals.complete, totals.total);
    el.innerHTML = `<div><h2>Completion</h2><div class="sub">${totals.complete} complete · ${totals.started} started · ${totals.total - totals.complete - totals.started} missing</div></div>` +
      `<div class="big ring" style="--p:${overall}"><span>${overall}<small>%</small></span></div>`;
    $('#progress-cats').innerHTML = `<button class="fxchip" data-pcat="overview" aria-pressed="true">${micon('check-circle', '', 'sm')}<span>Overview</span><span class="c">${totals.total}</span></button>` +
      cats.map((c) => {
        const iconFile = (cat().map_icons || {})[c.key];
        const ico = iconFile ? `<img class="chipico" src="companion_data/${encodeURI(iconFile)}" alt="">` : '';
        return `<button class="fxchip" data-pcat="${c.key}" aria-pressed="false">${ico}<span>${esc(c.label)}</span><span class="c">${c.complete}/${c.total}</span></button>`;
      }).join('');
    $('#progress-mode').hidden = true;
    $('#progress-filter').hidden = true;
    $('#progress-list').innerHTML = `<div class="progress-grid">` + cats.map((c) => {
      const p = pct(c.complete, c.total);
      const meta = catMeta(c.key);
      const iconFile = (cat().map_icons || {})[c.key];
      const ico = iconFile ? `<img class="pcico" src="companion_data/${encodeURIComponent(iconFile)}" alt="">` : '';
      return `<button class="pcard" data-pcat="${c.key}" style="--c:${meta.color}"><div class="top"><span class="name">${ico}${esc(c.label)}</span><span class="num">${c.complete}/${c.total}</span></div>` +
        `<div class="bar"><i style="width:${p}%"></i></div><div class="foot"><span>${c.missing} missing</span><span>${c.started ? `${c.started} started` : `${p}%`}</span></div></button>`;
    }).join('') + `</div>`;
    return;
  }
  const c = cats.find((x) => x.key === current);
  if (!c) { S.progress.cat = 'overview'; renderProgress(); return; }
  const catIcon = (cat().map_icons || {})[c.key];
  const catIconHtml = catIcon ? `<img class="phead-ico" src="companion_data/${encodeURIComponent(catIcon)}" alt="">` : '';
  const catPct = pct(c.complete, c.total);
  el.innerHTML = `<div><button class="crumb" data-pcat="overview">← Overview</button><h2 style="margin-top:8px">${catIconHtml}${esc(c.label)}</h2>` +
    `<div class="sub">${c.complete} complete · ${c.started} started · ${c.missing} missing</div></div>` +
    `<div class="big ring" style="--p:${catPct}"><span>${catPct}<small>%</small></span></div>`;
  $('#progress-cats').innerHTML = `<button class="fxchip" data-pcat="overview" aria-pressed="false">${micon('check-circle', '', 'sm')}<span>Overview</span><span class="c">${totals.total}</span></button>` +
    cats.map((x) => {
      const iconFile = (cat().map_icons || {})[x.key];
      const ico = iconFile ? `<img class="chipico" src="companion_data/${encodeURI(iconFile)}" alt="">` : '';
      return `<button class="fxchip" data-pcat="${x.key}" aria-pressed="${x.key === current}">${ico}<span>${esc(x.label)}</span><span class="c">${x.complete}/${x.total}</span></button>`;
    }).join('');
  $('#progress-mode').hidden = false;
  $('#progress-mode').innerHTML = [['all', 'All'], ['missing', 'Missing'], ['found', 'Found']].map(([k, l]) =>
    `<button data-pmode="${k}" aria-pressed="${S.progress.mode === k}">${l}</button>`).join('');
  $('#progress-filter').hidden = false;
  $('#progress-filter').value = S.progress.filter;
  const f = S.progress.filter.trim().toLowerCase();
  const states = comp.states;
  const rows = [];
  for (let i = 0; i < cat().collectibles.length; i++) {
    const it = cat().collectibles[i];
    if (it.cat !== current) continue;
    const st = states[i] || 0;
    if (S.progress.mode === 'missing' && st !== 0) continue;
    if (S.progress.mode === 'found' && st === 0) continue;
    if (f && !it.name.toLowerCase().includes(f)) continue;
    rows.push({ item: it, index: i, state: st });
  }
  const p = playerPos();
  $('#progress-list').innerHTML = rows.length ? rows.map((x) => {
    const d = p ? dist3(p, x.item) : null;
    const meta = catMeta(x.item.cat);
    const state = x.state >= 2 ? 'Complete' : x.state === 1 ? 'Started' : 'Missing';
    const iconFile = mapIconFile(x.item.cat, x.state);
    return `<div class="prow${x.state >= 2 ? ' found' : x.state === 1 ? ' started' : ''}">` +
      (iconFile ? `<img class="pico" src="companion_data/${encodeURI(iconFile)}" alt="">` : '<span></span>') +
      `<span class="pi"><span class="pn">${esc(x.item.name)}</span><span class="pm">${layerLabel(x.item.layer)}${d !== null ? ` · ${fmtDist(d)}` : ''}</span></span>` +
      `<span class="pd">${state}</span><button class="go" data-midx="${x.index}">Map</button></div>`;
  }).join('') : `<div class="empty"><b>Nothing here</b>No places match this filter.</div>`;
}

/* ------------------------------------------------------------------ compendium */

function compGroups() {
  const groups = {};
  for (const c of (cat().compendium || [])) groups[c.group] = (groups[c.group] || 0) + 1;
  return groups;
}
function renderCompendium() {
  const groups = compGroups();
  if (S.comp.group && !(S.comp.group in groups)) S.comp.group = '';
  $('#comp-groups').innerHTML = `<button class="fxchip" data-cgroup="" aria-pressed="${S.comp.group === ''}"><span>All</span><span class="c">${(cat().compendium || []).length}</span></button>` +
    Object.keys(groups).sort().map((g) => `<button class="fxchip" data-cgroup="${esc(g)}" aria-pressed="${S.comp.group === g}"><span>${esc(g)}</span><span class="c">${groups[g]}</span></button>`).join('');
  $('#comp-states').innerHTML = [['', 'All'], ['Unopened', 'Unopened'], ['TakePhoto', 'Photographed'], ['Buy', 'Purchased']].map(([k, l]) =>
    `<button data-cstate="${k}" aria-pressed="${S.comp.state === k}">${l}</button>`).join('');
  $('#comp-filter').value = S.comp.filter;
  const f = S.comp.filter.trim().toLowerCase();
  const list = (cat().compendium || []).map((c, i) => ({ c: c, i: i, st: (dyn().compendium && dyn().compendium[i]) || { state: 'Unopened' } }))
    .filter((x) => (!S.comp.group || x.c.group === S.comp.group) &&
      (!S.comp.state || x.st.state === S.comp.state) &&
      (!f || x.c.name.toLowerCase().includes(f) || (x.c.caption || '').toLowerCase().includes(f)));
  const grid = $('#comp-grid');
  if (!list.length) {
    grid.innerHTML = `<div class="empty"><b>No entries match</b>Try another group or state.</div>`;
    $('#comp-detail').innerHTML = '';
    return;
  }
  if (!list.some((x) => x.c.actor === S.comp.sel)) S.comp.sel = list[0].c.actor;
  grid.innerHTML = list.map((x) => {
    const cls = x.st.state === 'Unopened' ? ' comp-cell unopened' : ' comp-cell';
    return `<button class="cell${cls}" role="option" aria-selected="${x.c.actor === S.comp.sel}" data-cactor="${esc(x.c.actor)}">` +
      `${art({ icon: x.c.icon, name: x.c.name }, 'g')}<span class="nm">${esc(x.c.name)}</span></button>`;
  }).join('');
  const chosen = list.find((x) => x.c.actor === S.comp.sel) || list[0];
  renderCompDetail(chosen);
}
function renderCompDetail(x) {
  if (!x) { $('#comp-detail').innerHTML = ''; return; }
  const st = x.st;
  const state = st.state === 'TakePhoto' ? 'Photographed' : st.state === 'Buy' ? 'Purchased' : 'Not in the compendium';
  $('#comp-detail').innerHTML = `<div class="in"><div class="d-head">${art({ icon: x.c.icon }, 'hero')}<div><h2 class="d-name">${esc(x.c.name)}</h2>` +
    `<div class="d-sub">${esc(x.c.group)} entry</div></div></div>` +
    `<div class="tagrow"><span class="tag${st.state !== 'Unopened' ? ' gold' : ''}">${state}</span>${st.new ? '<span class="tag">New</span>' : ''}</div>` +
    (x.c.caption ? `<p class="cap">${esc(x.c.caption)}</p>` : '') + `</div>`;
}

/* ------------------------------------------------------------------ cooking */

const COOK_SORTS = [['hearts', 'Hearts'], ['time', 'Time'], ['name', 'Name'], ['effect', 'Effect']];
const heartScore = (d) => (d.extra ? 100 + d.extra : d.hearts);
const byName = (a, b) => a.name.localeCompare(b.name);
const SORT_FN = {
  hearts: (a, b) => heartScore(b) - heartScore(a) || byName(a, b),
  time: (a, b) => (b.seconds || 0) - (a.seconds || 0) || heartScore(b) - heartScore(a) || byName(a, b),
  name: byName,
  effect: (a, b) => (!a.effect_name - !b.effect_name) || (a.effect_name || '').localeCompare(b.effect_name || '') || heartScore(b) - heartScore(a) || byName(a, b),
};
const fxKey = (d) => d.effect || 'none';
function cookBaseRows() {
  const dishes = (dyn().cooking && dyn().cooking.dishes) || [];
  if (S.cook.all && S.cook.allRows) return S.cook.allRows;
  return dishes;
}
function cookEffects() {
  const m = new Map();
  for (const d of cookBaseRows()) {
    const k = fxKey(d);
    if (!m.has(k)) m.set(k, { key: k, name: k === 'none' ? 'No effect' : d.effect_name, effect: d.effect, count: 0 });
    m.get(k).count++;
  }
  return [...m.values()].sort((a, b) => (a.key === 'none') - (b.key === 'none') || a.name.localeCompare(b.name));
}
function cookItems() {
  const f = S.cook.filter.trim().toLowerCase();
  let list = cookBaseRows();
  if (S.cook.fx) list = list.filter((d) => fxKey(d) === S.cook.fx);
  list = [...list].sort(SORT_FN[S.cook.sort] || SORT_FN.hearts);
  if (f) list = list.filter((d) => [d.name, d.effect_name].concat((d.pot || []).map((p) => p.name), d.req || []).some((v) => v && v.toLowerCase().includes(f)));
  return list;
}
async function ensureAllRecipes() {
  if (S.cook.allRows && S.cook.allFor === S.dataVersion) return S.cook.allRows;
  const rows = await call('all_recipes');
  S.cook.allRows = Array.isArray(rows) ? rows : [];
  S.cook.allFor = S.dataVersion;
  return S.cook.allRows;
}
function staminaRecoveryHTML(it) {
  if (it.effect !== 'StaminaRecover') return '';
  const level = Math.min(15, Number(it.level) || 0);
  return `<div class="gauge">${staminaWheel(clamp(level / 15, 0, 1))}</div>` +
    `<div class="h-text">${level} of 15 stamina segments, ${Math.round(clamp(level / 15, 0, 1) * 100)}% of a wheel</div>`;
}
function extraStaminaHTML(it) {
  if (it.effect !== 'ExStaminaMaxUp') return '';
  const wheels = Math.min(2, (Number(it.level) || 0) / 10);
  return `<div class="gauge">${staminaGauge(wheels)}</div>` +
    `<div class="h-text">Adds ${wheels.toFixed(1)} extra stamina wheels</div>`;
}
function renderCooking() {
  if (S.cook.all && !S.cook.allRows) ensureAllRecipes().then(() => renderCooking());
  const rows = cookBaseRows();
  const effects = cookEffects();
  if (S.cook.fx && !effects.some((e) => e.key === S.cook.fx)) S.cook.fx = '';
  if (!SORT_FN[S.cook.sort]) S.cook.sort = 'hearts';
  $('#cook-fx').innerHTML = `<button class="fxchip" data-cfx="" aria-pressed="${S.cook.fx === ''}"><span>All</span><span class="c">${rows.length}</span></button>` +
    effects.map((e) => `<button class="fxchip" data-cfx="${esc(e.key)}" aria-pressed="${S.cook.fx === e.key}">${e.effect ? sigil(e.effect) : ''}<span>${esc(e.name)}</span><span class="c">${e.count}</span></button>`).join('');
  const allSwitch = $('#cook-all');
  if (allSwitch) allSwitch.setAttribute('aria-checked', String(S.cook.all));
  $('#cook-sort').innerHTML = COOK_SORTS.map(([k, l]) => `<button data-csort="${k}" aria-pressed="${S.cook.sort === k}">${l}</button>`).join('');
  $('#cook-filter').value = S.cook.filter;
  const list = cookItems();
  const grid = $('#cook-grid');
  if (!list.length) {
    grid.innerHTML = `<div class="empty"><b>${S.cook.all ? 'No recipes match' : 'Nothing to cook yet'}</b>${rows.length ? 'No dish matches this filter.' : (S.cook.all ? 'The recipe table is empty.' : 'The pouch holds no combination that makes a dish.')}</div>`;
    $('#cook-detail').innerHTML = '';
    return;
  }
  if (!list.some((d) => d.id === S.cook.sel)) S.cook.sel = list[0].id;
  grid.innerHTML = list.map((d) => {
    const badge = d.extra ? `<span class="badge">${heart(4, true)}+${fmtHearts(d.extra)}</span>` : d.hearts > 0 ? `<span class="badge">${heart(4)}${fmtHearts(d.hearts)}</span>` : '';
    return `<button class="cell${d.all && !d.cookable ? ' dim' : ''}" role="option" aria-selected="${d.id === S.cook.sel}" data-cdish="${esc(d.id)}">${sigil(d.effect)}${badge}${art(d)}<span class="nm">${esc(d.name)}</span></button>`;
  }).join('');
  renderCookDetail(list.find((d) => d.id === S.cook.sel) || list[0]);
}
function renderCookDetail(it) {
  const el = $('#cook-detail');
  if (!it) { el.innerHTML = ''; return; }
  let h;
  if (it.extra) h = `<div class="hearts">${hearts(it.extra, true)}</div><div class="h-text">Full recovery, plus ${fmtHearts(it.extra)} extra ${it.extra === 1 ? 'heart' : 'hearts'}</div>`;
  else if (it.hearts > 0) h = `<div class="hearts">${hearts(it.hearts)}</div><div class="h-text">Restores ${fmtHearts(it.hearts)} ${it.hearts === 1 ? 'heart' : 'hearts'}</div>`;
  else h = `<div class="h-text dimmed">No hearts restored</div>`;
  let fx;
  if (it.effect && it.effect !== 'LifeMaxUp') {
    const level = Math.min(EFFECT_MAX_LEVEL[it.effect] || 3, Number(it.level) || 1);
    const amount = effectAmount(it.effect, level);
    const gearLevel = gearEffectLevels()[it.effect] || 0;
    const totalLevel = Math.min(EFFECT_MAX_LEVEL[it.effect] || 3, gearLevel + level);
    const totalAmount = effectAmount(it.effect, totalLevel);
    fx = `<div class="effect">${sigil(it.effect)}<span>${esc(it.effect_name)}</span>${it.seconds ? `<span class="time">${fmtTime(it.seconds)}</span>` : ''}</div>` +
      (amount ? `<div class="fx-amount">Lv. ${level}: ${esc(amount)}</div>` : '') +
      (gearLevel ? `<div class="fx-total">With current armor and set bonuses: Lv. ${totalLevel}, ${esc(totalAmount || amount)}</div>` : '') +
      staminaRecoveryHTML(it) + extraStaminaHTML(it);
  }
  else if (it.mixed) fx = `<div class="effect none">Mixed effects cancel out, so this cooks with none.</div>`;
  else fx = it.effect === 'LifeMaxUp' ? '' : `<div class="effect none">No effect</div>`;
  const pot = (it.pot || []).map((p) => `<li><button data-invactor="${esc(p.actor)}"><span class="mini">${art(p, 'i')}</span><span class="pn">${esc(p.name)}</span><span class="pc">×${p.n}</span></button></li>`).join('');
  const req = (it.req || []).map((r, i) => {
    const rep = (it.pot || [])[i];
    return `<li><span class="mini">${rep ? art(rep, 'i') : ''}</span><span class="pn">${esc(r)}</span></li>`;
  }).join('');
  const reqBlock = it.all
    ? `<h3 class="label">Recipe</h3><ul class="pot">${req}</ul>` +
      `<div class="tagrow"><span class="tag ${it.cookable ? 'gold' : ''}">${it.cookable ? 'Can cook now' : 'Missing ingredients'}</span>` +
      (it.missing && it.missing.length ? `<span class="tag">Missing: ${esc(it.missing.join(', '))}</span>` : '') + `</div>`
    : `<h3 class="label">In the pot</h3><ul class="pot">${pot}</ul>`;
  el.innerHTML = `<div class="in"><div class="d-head">${art(it, 'hero')}<div><h2 class="d-name">${esc(it.name)}</h2><div class="d-sub">${it.all ? 'Recipe' : plural(it.size, 'ingredient', 'ingredients')}</div></div></div>` +
    h + fx + `<div class="ornament"></div>` + reqBlock +
    `<p class="note">${it.all ? 'Cook this recipe with any ingredient that matches each slot.' : 'An estimate. A critical cook can add hearts or time.'}</p></div>`;
}

/* ------------------------------------------------------------------ settings */

function openSettings(on) {
  S.modal = on;
  $('#settings').hidden = !on;
  $('#btn-settings').setAttribute('aria-pressed', String(on));
  if (on) renderSettings();
}
function pollSelect() {
  const current = Math.round(Number((dyn().save && dyn().save.poll_s) || S.settings.poll_s || 15));
  const values = [5, 10, 15, 30, 60];
  if (!values.includes(current)) values.push(current);
  values.sort((a, b) => a - b);
  return `<select id="poll-interval" class="select" style="max-width:130px" aria-label="Refresh interval">` +
    values.map((v) => `<option value="${v}"${v === current ? ' selected' : ''}>${v} seconds</option>`).join('') +
    `</select>`;
}
function rebuildStatusText() {
  const rb = dyn().save && dyn().save.rebuild;
  if (!rb) return 'Rebuild icons, maps, and item data from the game files. This can take several minutes.';
  if (S.rebuildStarted && !rb.running && !rb.done && !rb.error) return 'Starting rebuild...';
  if (rb.running) {
    const elapsed = Math.max(0, Math.floor(Date.now() / 1000 - (rb.started || 0)));
    return `Rebuilding. ${elapsed}s elapsed. This can take several minutes.`;
  }
  if (rb.error) return `Build failed: ${rb.message || rb.error}`;
  if (rb.done) return rb.message || 'Data rebuilt.';
  return 'Rebuild icons, maps, and item data from the game files. This can take several minutes.';
}
function renderSettings() {
  const meta = (cat().meta && cat().meta.counts) || {};
  const st = S.settings;
  const built = cat().meta && cat().meta.built ? new Date(cat().meta.built * 1000).toLocaleString() : 'unknown';
  $('#settings').innerHTML = `<div class="modal-card"><h2>Settings</h2><div class="sub">TotK Companion reads the newest save. It never writes to the save or to the game.</div>` +
    `<div class="row"><span class="t">Always on top</span><button class="switch" data-setkey="on_top" role="switch" aria-checked="${!!st.on_top}"></button><span class="s">Keeps the window above the game in borderless fullscreen.</span></div>` +
    `<div class="row"><span class="t">Start minimized</span><button class="switch" data-setkey="start_hidden" role="switch" aria-checked="${!!st.start_hidden}"></button><span class="s">Applies the next time the companion starts.</span></div>` +
    `<div class="row"><span class="t">Save slot</span><select id="save-slot" class="select" style="max-width:230px" aria-label="Save slot"></select><span class="s">Auto shows the newest save. Pick a slot to keep the companion on one character.</span></div>` +
    `<div class="row"><span class="t">Refresh interval</span>${pollSelect()}<span class="s">The window checks for a newer save on this interval. Use Refresh now to check immediately.</span></div>` +
    `<div class="row"><span class="t">Rebuild data</span><button class="btn" data-act="rebuild"${(dyn().save && dyn().save.rebuild && dyn().save.rebuild.running) ? ' disabled' : ''}>${(dyn().save && dyn().save.rebuild && dyn().save.rebuild.running) ? 'Rebuilding...' : 'Rebuild now'}</button><span class="s" id="rebuild-status">${esc(rebuildStatusText())}</span></div>` +
    `<div class="row"><span class="t">Data</span><span class="s" style="grid-column:auto;color:var(--text)">${meta.actors || 0} actors · ${meta.armor || 0} armor · ${meta.compendium || 0} compendium · ${meta.collectibles || 0} collectibles</span><span class="s">Built from your game on ${esc(built)}. Rebuild after a game update or to refresh icons, maps, and item data.</span></div>` +
    `<div class="row"><span class="t">Shortcuts</span><span class="s"><span class="kbd">/</span> filter · <span class="kbd">r</span> refresh · <span class="kbd">1</span>-<span class="kbd">7</span> sections · <span class="kbd">Esc</span> clear</span></div>` +
    `<div class="actions"><button class="btn" data-act="reset-filters">Reset filters</button>` +
    `<button class="btn" data-act="refresh">Check save now</button><button class="btn" data-act="close-settings">Done</button></div></div>`;
  renderSaves();
  const poll = $('#poll-interval');
  if (poll) poll.addEventListener('change', (e) => call('set_setting', 'poll_s', Number(e.target.value)));
}
function renderRebuildStatus() {
  const el = $('#rebuild-status');
  if (!el) return;
  el.textContent = rebuildStatusText();
  const rb = dyn().save && dyn().save.rebuild;
  const btn = $('[data-act="rebuild"]');
  if (btn && rb) {
    const pending = S.rebuildStarted && !rb.running && !rb.done && !rb.error;
    btn.disabled = !!rb.running || pending;
    btn.textContent = (rb.running || pending) ? 'Rebuilding...' : 'Rebuild now';
  }
}

/* ------------------------------------------------------------------ status line */

function renderStatusLine() {
  const el = $('#save'), hint = $('#hint');
  const d = dyn();
  if (!d || !d.save) { el.textContent = 'Looking for a save'; return; }
  const sv = d.save;
  const rb = sv.rebuild;
  if (rb && rb.running) {
    const elapsed = Math.max(0, Math.floor(Date.now() / 1000 - (rb.started || 0)));
    el.innerHTML = `<span class="spin"></span>Rebuilding data, ${elapsed}s elapsed…`;
  } else if (rb && rb.error) {
    el.innerHTML = `<span class="warn">Rebuild failed: ${esc(rb.message || rb.error)}</span>`;
  } else if (sv.error === 'nosave') {
    el.innerHTML = '<span class="warn">No save yet.</span> Save once in the game and the companion fills in.';
  } else if (sv.checking) {
    el.innerHTML = '<span class="spin"></span>Scanning save…';
  } else if (sv.error) {
    el.innerHTML = `<span class="warn">The game is writing the save. Trying again.</span>`;
  } else {
    const next = sv.next_scan ? Math.max(0, Math.ceil(sv.next_scan - Date.now() / 1000)) : null;
    const slot = sv.slot ? sv.slot.replace('_', ' ') : 'save';
    el.innerHTML = `${esc(slot)}, saved ${ago(sv.mtime)}${next !== null ? ` · next check in ${next}s` : ''}`;
  }
  hint.textContent = 'Read-only save mode · refreshes when the game saves';
}

/* ------------------------------------------------------------------ static events */

function attachStatic() {
  $('#inv-filter').addEventListener('input', (e) => { S.inv.filter = e.target.value; renderInventory(); });
  $('#armor-filter').addEventListener('input', (e) => { S.armor.filter = e.target.value; renderArmor(); });
  $('#armor-set').addEventListener('change', (e) => { S.armor.set = e.target.value; renderArmor(); });
  $('#armor-owned').addEventListener('click', () => { S.armor.owned = !S.armor.owned; renderArmor(); });
  const cookAll = $('#cook-all');
  if (cookAll) cookAll.addEventListener('click', async () => {
    S.cook.all = !S.cook.all;
    saveUiStateSoon();
    if (S.cook.all && !S.cook.allRows) await ensureAllRecipes();
    renderCooking();
  });
  $('#map-search').addEventListener('input', (e) => {
    S.map.search = e.target.value;
    updateSearchClear();
    renderNearby();
    drawMap();
  });
  const clearSearch = $('#map-search-clear');
  if (clearSearch) clearSearch.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    S.map.search = '';
    $('#map-search').value = '';
    updateSearchClear();
    renderNearby();
    drawMap();
  });
  const revealMap = $('#map-reveal');
  if (revealMap) revealMap.addEventListener('change', (e) => {
    S.map.reveal = !!e.target.checked;
    renderNearby();
    drawMap();
    requestMinimapDraw();
  });
  const pathMap = $('#map-path');
  if (pathMap) pathMap.addEventListener('change', async (e) => {
    S.map.path = !!e.target.checked;
    saveUiStateSoon();
    if (S.map.path) await ensureHeroPath();
    renderMapPathNote();
    drawMap();
  });
  $('#progress-filter').addEventListener('input', (e) => { S.progress.filter = e.target.value; renderProgress(); });
  $('#comp-filter').addEventListener('input', (e) => { S.comp.filter = e.target.value; renderCompendium(); });
  $('#cook-filter').addEventListener('input', (e) => { S.cook.filter = e.target.value; renderCooking(); });
  document.addEventListener('change', (e) => {
    if (e.target && e.target.id === 'save-slot') {
      S.selectedSave = e.target.value;
      call('select_save', e.target.value).then(() => poll(true));
    }
  });
  $('#btn-refresh').addEventListener('click', () => call('refresh'));
  $('#btn-min').addEventListener('click', () => call('hide'));
  $('#btn-close').addEventListener('click', () => call('close'));
  $('#btn-settings').addEventListener('click', () => openSettings(!S.modal));
  const sourcesModal = $('#sources');
  if (sourcesModal) sourcesModal.addEventListener('click', (e) => { if (e.target === sourcesModal) closeSources(); });

  const vp = $('#map-viewport');
  const ignoreMapDrag = (target) => target && target !== vp && target.closest &&
    !!target.closest('.map-zoom, .minimap, button, input, select, label');
  vp.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 || ignoreMapDrag(e.target)) return;
    S.map.drag = { x: e.clientX, y: e.clientY, tx: S.map.tx, ty: S.map.ty, moved: false };
    vp.classList.add('grabbing');
    try { vp.setPointerCapture(e.pointerId); } catch (err) {}
  });
  vp.addEventListener('pointermove', (e) => {
    updateMapCoords(e.clientX, e.clientY);
    const d = S.map.drag;
    if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
    S.map.tx = d.tx + dx; S.map.ty = d.ty + dy;
    applyMap();
  });
  vp.addEventListener('pointerleave', () => {
    const el = $('#map-coords');
    if (el) el.hidden = true;
  });
  const endDrag = (e) => {
    const d = S.map.drag;
    S.map.drag = null;
    vp.classList.remove('grabbing');
    if (d && !d.moved) mapHitTest(e.clientX, e.clientY);
  };
  vp.addEventListener('pointerup', endDrag);
  vp.addEventListener('pointercancel', () => { S.map.drag = null; vp.classList.remove('grabbing'); });
  // Older WebKitGTK builds expose mouse events even when PointerEvent is
  // missing. Keep map panning and marker clicks working there too.
  if (!('PointerEvent' in window)) {
    vp.addEventListener('mousedown', (e) => {
      if (e.button !== 0 || ignoreMapDrag(e.target)) return;
      e.preventDefault();
      S.map.drag = { x: e.clientX, y: e.clientY, tx: S.map.tx, ty: S.map.ty, moved: false };
      vp.classList.add('grabbing');
    });
    window.addEventListener('mousemove', (e) => {
      if (vp.contains(e.target)) updateMapCoords(e.clientX, e.clientY);
      const d = S.map.drag;
      if (!d) return;
      const dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
      S.map.tx = d.tx + dx; S.map.ty = d.ty + dy;
      applyMap();
    });
    window.addEventListener('mouseup', endDrag);
  }
  vp.addEventListener('wheel', (e) => {
    e.preventDefault();
    zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX, e.clientY);
  }, { passive: false });
  vp.addEventListener('dblclick', (e) => { e.preventDefault(); zoomAt(1.6, e.clientX, e.clientY); });
  $('#map-zoomin').addEventListener('click', () => zoomAt(1.45));
  $('#map-zoomout').addEventListener('click', () => zoomAt(1 / 1.45));
  $('#map-fit').addEventListener('click', () => { if (fitMap()) S.map.fitted = true; });
  $('#map-me').addEventListener('click', centerOnPlayer);

  const mini = $('#minimap');
  if (mini) {
    mini.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      e.preventDefault(); e.stopPropagation();
      S.map.miniDrag = true;
      try { mini.setPointerCapture(e.pointerId); } catch (err) {}
      minimapGoto(e);
    });
    mini.addEventListener('pointermove', (e) => {
      if (!S.map.miniDrag) return;
      e.preventDefault(); e.stopPropagation();
      minimapGoto(e);
    });
    const miniEnd = (e) => { S.map.miniDrag = false; e.stopPropagation(); };
    mini.addEventListener('pointerup', miniEnd);
    mini.addEventListener('pointercancel', miniEnd);
    if (!('PointerEvent' in window)) {
      mini.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        e.preventDefault(); e.stopPropagation();
        S.map.miniDrag = true;
        minimapGoto(e);
      });
      window.addEventListener('mousemove', (e) => {
        if (!S.map.miniDrag) return;
        e.preventDefault(); e.stopPropagation();
        minimapGoto(e);
      });
      window.addEventListener('mouseup', () => { S.map.miniDrag = false; });
    }
  }
  window.addEventListener('resize', () => {
    S.map.fitted = false;
    if (S.page === 'map' && fitMap()) S.map.fitted = true;
  });
}

function closestButton(node) {
  while (node && node !== document) {
    if (node.nodeType === 1 && node.tagName === 'BUTTON') return node;
    node = node.parentNode;
  }
  return null;
}

document.addEventListener('click', (e) => {
  const t = closestButton(e.target);
  if (!t) return;
  if (t.dataset.page) { showPage(t.dataset.page); return; }
  if (t.dataset.pageGo) { showPage(t.dataset.pageGo); return; }
  if (t.dataset.invcat !== undefined) {
    if (t.dataset.invcat === 'armor') { showPage('armor'); return; }
    S.inv.cat = t.dataset.invcat;
    S.inv.sel = null;
    if (S.page !== 'inventory') showPage('inventory'); else renderInventory();
    return;
  }
  if (t.dataset.armorSearch !== undefined) {
    S.armor.filter = S.inv.filter;
    S.armor.slot = '';
    S.armor.set = '';
    S.armor.owned = false;
    showPage('armor');
    return;
  }
  if (t.dataset.invkey !== undefined) {
    S.inv.sel = t.dataset.invkey;
    $$('#inv-grid .cell').forEach((c) => c.setAttribute('aria-selected', String(c.dataset.invkey === S.inv.sel)));
    const it = (dyn().inventory || []).flatMap((c) => c.items)
      .find((x) => x.actor + ':' + (x.index === undefined ? 0 : x.index) === S.inv.sel);
    if (it) renderInvDetail(it);
    return;
  }
  if (t.dataset.invactor) { openInventoryActor(t.dataset.invactor); return; }
  if (t.dataset.slot !== undefined) { S.armor.slot = t.dataset.slot; renderArmor(); return; }
  if (t.dataset.armor) { S.armor.sel = t.dataset.armor; renderArmor(); return; }
  if (t.dataset.srcmat) { openSources(t.dataset.srcmat); return; }
  if (t.dataset.srcclose !== undefined) { closeSources(); return; }
  if (t.dataset.srcgroup) { showSourceGroup(S.sourceActor, t.dataset.srcgroup, t.dataset.srclabel || ''); return; }
  if (t.dataset.srcshow) { showMaterialSources(S.sourceActor, t.dataset.srcshow); return; }
  if (t.dataset.srcclear !== undefined) { clearSources(); return; }
  if (t.dataset.pcat) {
    S.progress.cat = t.dataset.pcat;
    if (S.page !== 'progress') showPage('progress'); else renderProgress();
    return;
  }
  if (t.dataset.pmode) { S.progress.mode = t.dataset.pmode; renderProgress(); return; }
  if (t.dataset.cgroup !== undefined) { S.comp.group = t.dataset.cgroup; renderCompendium(); return; }
  if (t.dataset.cstate !== undefined) { S.comp.state = t.dataset.cstate; renderCompendium(); return; }
  if (t.dataset.cactor) { S.comp.sel = t.dataset.cactor; renderCompendium(); return; }
  if (t.dataset.cfx !== undefined) { S.cook.fx = t.dataset.cfx; renderCooking(); return; }
  if (t.dataset.csort) { S.cook.sort = t.dataset.csort; renderCooking(); return; }
  if (t.dataset.cdish) { S.cook.sel = t.dataset.cdish; showPage('cook'); renderCooking(); return; }
  if (t.dataset.mcats) {
    const all = t.dataset.mcats === 'all';
    if (all) {
      for (const c of (cat().collectible_categories || [])) S.map.cats.add(c.key);
    } else {
      S.map.cats.clear();
    }
    S.map.medals = all;
    renderMapCats(); renderNearby(); drawMap(); return;
  }
  if (t.dataset.mcat) {
    if (S.map.cats.has(t.dataset.mcat)) S.map.cats.delete(t.dataset.mcat); else S.map.cats.add(t.dataset.mcat);
    renderMapCats(); renderNearby(); drawMap(); return;
  }
  if (t.dataset.mmedals !== undefined) {
    S.map.medals = !S.map.medals;
    renderMapCats(); drawMap(); return;
  }
  if (t.dataset.layer) { setMapLayer(t.dataset.layer); return; }
  if (t.dataset.found) { S.map.found = t.dataset.found; renderMapToolbar(); renderNearby(); drawMap(); return; }
  if (t.dataset.maprelax) {
    if (t.dataset.maprelax === 'found') S.map.found = 'all';
    else if (t.dataset.maprelax === 'reveal') S.map.reveal = true;
    renderMapToolbar(); renderNearby(); drawMap(); requestMinimapDraw();
    return;
  }
  if (t.dataset.midx !== undefined) {
    const it = cat().collectibles[Number(t.dataset.midx)];
    if (it) {
      if (!S.map.cats.has(it.cat)) S.map.cats.add(it.cat);
      S.map.pending = it;
      showPage('map');
      centerOnItem(it);
    }
    return;
  }
  if (t.dataset.mcenter) {
    const it = cat().collectibles.find((x) => x.id === t.dataset.mcenter);
    if (it) centerOnItem(it);
    return;
  }
  if (t.dataset.mprogress) { S.progress.cat = t.dataset.mprogress; S.progress.mode = 'all'; showPage('progress'); return; }
  if (t.dataset.setkey) {
    const k = t.dataset.setkey;
    const v = t.getAttribute('aria-checked') !== 'true';
    S.settings[k] = v;
    call('set_setting', k, v);
    renderSettings();
    return;
  }
  if (t.dataset.act === 'reset-filters') { resetFilters(); openSettings(false); return; }
  if (t.dataset.act === 'refresh') { call('refresh'); return; }
  if (t.dataset.act === 'rebuild') {
    S.rebuildStarted = true;
    t.disabled = true;
    t.textContent = 'Rebuilding...';
    const st = $('#rebuild-status');
    if (st) st.textContent = 'Rebuilding. This can take several minutes.';
    call('rebuild');
    return;
  }
  if (t.dataset.act === 'close-settings') { openSettings(false); return; }
});

function openInventoryActor(actor) {
  for (const c of (dyn().inventory || [])) {
    const it = c.items.find((x) => x.actor === actor);
    if (it) {
      if (c.key === 'armor') {
        S.armor.sel = it.base || it.actor;
        S.armor.slot = '';
        S.armor.set = '';
        S.armor.owned = true;
        showPage('armor');
        return;
      }
      S.inv.cat = c.key;
      S.inv.sel = it.actor + ':' + (it.index === undefined ? 0 : it.index);
      showPage('inventory');
      return;
    }
  }
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (S.sourceModal) { closeSources(); e.preventDefault(); return; }
    if (S.modal) { openSettings(false); e.preventDefault(); return; }
    const inp = document.activeElement;
    if (inp && inp.tagName === 'INPUT') { if (inp.value) { inp.value = ''; inp.dispatchEvent(new Event('input', { bubbles: true })); } else inp.blur(); }
    return;
  }
  if (e.target && e.target.tagName === 'INPUT') return;
  if (e.key === '/') {
    const sel = { status: null, inventory: '#inv-filter', armor: '#armor-filter', map: '#map-search', progress: '#progress-filter', compendium: '#comp-filter', cook: '#cook-filter' }[S.page];
    if (sel && $(sel)) { e.preventDefault(); $(sel).focus(); $(sel).select(); }
    return;
  }
  if (e.key === 'r' || e.key === 'R') { call('refresh'); return; }
  if (/^[1-7]$/.test(e.key)) { showPage(NAV[Number(e.key) - 1][0]); }
});

/* ------------------------------------------------------------------ boot */

window.addEventListener('pywebviewready', () => { if (!S.booted) { S.booted = true; start(); } });
if (window.pywebview && window.pywebview.api) { S.booted = true; start(); }
renderStatusLine();
