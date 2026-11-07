'use strict';

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
const MARK_SPEED = ['M8.6 9l3 3-3 3M12.2 9l3 3-3 3', 0];
const MARKS = {
  AllSpeed: MARK_SPEED, SwimSpeedUp: MARK_SPEED, ClimbSpeedUp: MARK_SPEED, SnowMoveUp: MARK_SPEED,
  SandMoveUp: MARK_SPEED, DivingMobilityUp: MARK_SPEED,
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
const PAD = [
  ['lstick', 'LS click'], ['rstick', 'RS click'], ['lb', 'LB'], ['rb', 'RB'], ['lt', 'LT'], ['rt', 'RT'],
  ['back', 'View'], ['start', 'Menu'], ['guide', 'Guide'], ['a', 'A'], ['b', 'B'], ['x', 'X'], ['y', 'Y'],
  ['dpad_up', 'D-pad up'], ['dpad_down', 'D-pad down'], ['dpad_left', 'D-pad left'], ['dpad_right', 'D-pad right'],
];
const PAD_SHORT = { lstick: 'LS', rstick: 'RS', back: 'View', start: 'Menu', dpad_up: 'Up', dpad_down: 'Down', dpad_left: 'Left', dpad_right: 'Right' };

const S = {
  version: -1, d: null, tab: 'dishes', sel: { dishes: null, materials: null }, lastDetail: { dishes: null, materials: null }, filter: '',
  settings: false, editCombo: false, capturing: false, booted: false,
};
const $ = (q) => document.querySelector(q);
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const api = () => (window.pywebview && window.pywebview.api) || null;
const call = (name, ...a) => { const x = api(); return x && x[name] ? x[name](...a) : Promise.resolve(null); };

function icon(name, cls = 'g', color) {
  const st = color ? ` style="--fxc:${color}"` : '';
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"${st}>${ICONS[name] || ICONS.pouch}</svg>`;
}
// The game's own icon when build_icons.py found one, the drawn glyph otherwise.
function art(it, cls = 'g') {
  if (it.icon) return `<img class="${cls} art" src="icons/${encodeURI(it.icon)}" alt="" draggable="false" decoding="async">`;
  return icon(it.glyph, cls, FX[it.effect]);
}
function sigil(effect, cls = 'sig') {
  const c = FX[effect];
  if (!c) return '';
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" style="stroke:${c}"><path d="M12 2.5l9.5 9.5-9.5 9.5L2.5 12z" stroke-width="2"/>${mark(effect, c)}</svg>`;
}
function mark(effect, c) {
  const m = MARKS[effect];
  if (!m) return `<path d="M12 8l4 4-4 4-4-4z" fill="${c}" stroke="none"/>`;
  return m[1] ? `<path d="${m[0]}" fill="${c}" stroke="none"/>` : `<path d="${m[0]}" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>`;
}
function heart(q, yellow) {
  const fill = q >= 4 ? `<path class="hf" d="${HEART}"/>` : q > 0 ? `<path class="hf" d="${HEART}" clip-path="url(#q${q})"/>` : '';
  return `<svg class="heart${yellow ? ' y' : ''}" viewBox="0 0 24 24" aria-hidden="true"><path class="hb" d="${HEART}"/>${fill}<path class="ho" d="${HEART}"/></svg>`;
}
function hearts(h, yellow, max = 40) {
  let quarters = Math.round(h * 4), out = '', n = 0;
  while (quarters > 0 && n < max) { out += heart(Math.min(4, quarters), yellow); quarters -= 4; n++; }
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
function plural(n, one, many) { return `${n} ${n === 1 ? one : many}`; }
function comboHTML(list) {
  if (!list || !list.length) return '<span class="dimmed">none</span>';
  return list.map((b) => `<span class="chip">${esc(PAD_SHORT[b] || (PAD.find((p) => p[0] === b) || [b, b])[1])}</span>`).join('<span class="plus">+</span>');
}
function keyLabel(spec) {
  if (!spec) return 'None';
  return spec.split('+').map((p) => p.length === 1 ? p.toUpperCase() : p[0].toUpperCase() + p.slice(1)).join(' + ');
}

/* ---------- data ---------- */
/* ---------- dish sort and effect filter ---------- */
const SORTS = [['hearts', 'Hearts'], ['time', 'Time'], ['name', 'Name'], ['effect', 'Effect']];
const heartScore = (d) => (d.extra ? 100 + d.extra : d.hearts);
const byName = (a, b) => a.name.localeCompare(b.name);
const SORT_FN = {
  hearts: (a, b) => heartScore(b) - heartScore(a) || byName(a, b),
  time: (a, b) => (b.seconds || 0) - (a.seconds || 0) || heartScore(b) - heartScore(a) || byName(a, b),
  name: byName,
  effect: (a, b) => (!a.effect_name - !b.effect_name) || (a.effect_name || '').localeCompare(b.effect_name || '')
    || heartScore(b) - heartScore(a) || byName(a, b),
};
const fxKey = (d) => d.effect || 'none';
// effect key -> {name, count, effect}, effects A to Z with "No effect" last
function dishEffects() {
  const m = new Map();
  for (const d of S.d.dishes) {
    const k = fxKey(d);
    if (!m.has(k)) m.set(k, { key: k, name: k === 'none' ? 'No effect' : d.effect_name, effect: d.effect, count: 0 });
    m.get(k).count++;
  }
  return [...m.values()].sort((a, b) => (a.key === 'none') - (b.key === 'none') || a.name.localeCompare(b.name));
}
// the saved effect, or '' when no dish on the list has it right now
function activeEffect() {
  const k = (S.d && S.d.settings.dish_effect) || '';
  return k && S.d.dishes.some((d) => fxKey(d) === k) ? k : '';
}
function dishSort() {
  const k = S.d && S.d.settings.dish_sort;
  return SORT_FN[k] ? k : 'hearts';
}
function dishOpt(key, value) {
  if (!S.d) return;
  S.d.settings[key] = value;
  call('set_setting', key, value);
  renderGrid(true);
  $('#gridwrap').scrollTop = 0;
}
function cycleSort() {
  const i = SORTS.findIndex(([k]) => k === dishSort());
  dishOpt('dish_sort', SORTS[(i + 1) % SORTS.length][0]);
}
function cycleEffect() {
  const keys = ['', ...dishEffects().map((e) => e.key)];
  dishOpt('dish_effect', keys[(keys.indexOf(activeEffect()) + 1) % keys.length]);
}
function renderTools() {
  const el = $('#tools'), sb = $('#sortbox');
  if (S.tab !== 'dishes' || !S.d || !S.d.dishes.length) { el.hidden = true; sb.hidden = true; return; }
  el.hidden = false; sb.hidden = false;
  const fx = activeEffect(), sort = dishSort();
  const chip = (k, label, n, effect) => `<button class="fxchip" data-fx="${esc(k)}" aria-pressed="${fx === k}">${effect ? sigil(effect) : ''}<span>${esc(label)}</span><span class="c">${n}</span></button>`;
  const chips = [chip('', 'All', S.d.dishes.length)].concat(dishEffects().map((e) => chip(e.key, e.name, e.count, e.effect))).join('');
  const seg = SORTS.map(([k, label]) => `<button data-sort="${k}" aria-pressed="${sort === k}">${label}</button>`).join('');
  const scroll = el.querySelector('.chips') ? el.querySelector('.chips').scrollLeft : 0;
  el.innerHTML = `<div class="chips" role="group" aria-label="Show dishes with this effect">${chips}</div>`;
  sb.innerHTML = `<span class="lbl">Sort</span><div class="seg" role="group" aria-label="Sort dishes">${seg}</div>`;
  el.querySelector('.chips').scrollLeft = scroll;
}

function items() {
  if (!S.d) return [];
  const f = S.filter.trim().toLowerCase();
  let all = S.tab === 'dishes' ? S.d.dishes : S.d.materials;
  if (S.tab === 'dishes') {
    const fx = activeEffect();
    if (fx) all = all.filter((d) => fxKey(d) === fx);
    all = [...all].sort(SORT_FN[dishSort()]);
  }
  if (!f) return all;
  return all.filter((it) => {
    const hay = S.tab === 'dishes'
      ? [it.name, it.effect_name, ...it.pot.map((p) => p.name)]
      : [it.name, it.effect_name, ...it.kinds];
    return hay.some((v) => v && v.toLowerCase().includes(f));
  });
}
function selected(list) {
  list = list || items();
  const id = S.sel[S.tab];
  return list.find((x) => x.id === id) || list[0] || null;
}

/* ---------- render ---------- */
function renderTabs() {
  for (const t of ['dishes', 'materials']) {
    const b = $('#tab-' + t);
    b.setAttribute('aria-selected', String(S.tab === t));
    $('#n-' + t).textContent = S.d ? S.d[t].length : '';
  }
  $('#grid').setAttribute('aria-label', S.tab === 'dishes' ? 'Dishes' : 'Materials');
  $('#filter').placeholder = S.tab === 'dishes' ? 'Filter by dish, effect or ingredient' : 'Filter by material, effect or kind';
}

function cellHTML(it, isSel) {
  const sel = `aria-selected="${isSel}"`;
  if (S.tab === 'dishes') {
    const badge = it.extra
      ? `<span class="badge">${heart(4, true)}+${fmtHearts(it.extra)}</span>`
      : it.hearts > 0 ? `<span class="badge">${heart(4)}${fmtHearts(it.hearts)}</span>` : '';
    return `<button class="cell" role="option" ${sel} data-id="${esc(it.id)}" aria-label="${esc(it.name)}">${sigil(it.effect)}${badge}${art(it)}<span class="nm">${esc(it.name)}</span></button>`;
  }
  const dim = it.used_in.length ? '' : ' dim';
  return `<button class="cell${dim}" role="option" ${sel} data-id="${esc(it.id)}" aria-label="${esc(it.name)}, ${it.count}">${sigil(it.effect)}<span class="badge count">×${it.count}</span>${art(it)}<span class="nm">${esc(it.name)}</span></button>`;
}

function staleInfo(it) {
  if (!it) return null;
  if (S.tab === 'materials') return { text: 'This material is no longer in your pouch.', missing: [] };
  const have = new Map((S.d && S.d.materials ? S.d.materials : []).map((m) => [m.id, m.count]));
  const missing = it.pot
    .map((p) => ({ actor: p.actor, name: p.name, need: p.n, have: have.get(p.actor) || 0 }))
    .filter((p) => p.have < p.need);
  return {
    text: missing.length ? 'Not enough materials for this recipe after the last save.'
      : 'This recipe is no longer available with the current pouch.',
    missing,
  };
}

function renderGrid(snap, keepScroll = false) {
  renderTools();
  const grid = $('#grid');
  const wrap = $('#gridwrap');
  const scroll = keepScroll ? wrap.scrollTop : 0;
  if (!S.d) {
    grid.innerHTML = `<div class="empty"><b>Reading your save</b>The list fills in a moment after the helper finds it.</div>`;
    renderDetail(null);
    wrap.scrollTop = scroll;
    return;
  }
  const list = items();
  const wanted = S.sel[S.tab];
  const available = S.tab === 'dishes' ? S.d.dishes : S.d.materials;
  const visible = wanted ? list.find((x) => x.id === wanted) : null;
  const existing = wanted ? available.find((x) => x.id === wanted) : null;
  let chosen = visible;

  if (!list.length) {
    let msg;
    if (S.filter.trim()) msg = `<b>Nothing matches "${esc(S.filter.trim())}"</b>Clear the filter with Esc${S.tab === 'dishes' && activeEffect() ? ', or pick All above' : ''}.`;
    else if (S.tab === 'dishes') msg = '<b>Nothing to cook yet</b>The pouch holds no combination that makes a dish. Meat, fish, fruit and mushrooms are the usual start.';
    else msg = '<b>The material pouch is empty</b>It fills in after the game saves with materials in it.';
    grid.innerHTML = `<div class="empty">${msg}</div>`;
  } else {
    if (!chosen && !wanted) {
      chosen = list[0];
      S.sel[S.tab] = chosen.id;
    }
    grid.innerHTML = list.map((it) => cellHTML(it, chosen && it.id === chosen.id)).join('') + '<div class="cursor snap" id="cursor"></div>';
    placeCursor(true);
  }

  if (chosen) renderDetail(chosen);
  else if (existing) renderDetail(existing);
  else if (wanted) {
    const stale = S.lastDetail[S.tab];
    if (stale && stale.id === wanted) renderDetail(stale, staleInfo(stale));
    else renderDetail(null);
  } else renderDetail(null);
  wrap.scrollTop = scroll;
}
function placeCursor(snap) {
  const c = $('#cursor');
  const cell = $('#grid .cell[aria-selected="true"]');
  if (!c || !cell) return;
  if (snap) c.classList.add('snap'); else c.classList.remove('snap');
  c.style.width = cell.offsetWidth + 'px';
  c.style.height = cell.offsetHeight + 'px';
  c.style.transform = `translate(${cell.offsetLeft}px, ${cell.offsetTop}px)`;
  if (snap) requestAnimationFrame(() => c.classList.remove('snap'));
}

function select(id, scroll = true) {
  if (S.sel[S.tab] === id && $('#grid .cell[aria-selected="true"]')) return;
  S.sel[S.tab] = id;
  for (const el of document.querySelectorAll('#grid .cell')) el.setAttribute('aria-selected', String(el.dataset.id === id));
  const cell = $('#grid .cell[aria-selected="true"]');
  if (cell && scroll) cell.scrollIntoView({ block: 'nearest' });
  placeCursor(false);
  renderDetail(selected());
}

function renderDetail(it, stale = null) {
  const el = $('#detail');
  el.classList.toggle('stale', !!stale);
  if (!it) { el.innerHTML = ''; return; }
  if (!stale) S.lastDetail[S.tab] = it;
  let banner = '';
  const missingActors = new Set();
  if (stale) {
    if (stale.missing) for (const m of stale.missing) missingActors.add(m.actor);
    const detail = stale.missing && stale.missing.length
      ? ` Missing: ${stale.missing.map((m) => `${esc(m.name)} (need ${m.need}, have ${m.have})`).join(', ')}.`
      : '';
    banner = `<div class="missing"><b>${esc(stale.text)}</b>${detail}</div>`;
  }
  if (S.tab === 'dishes') {
    let h;
    if (it.extra) {
      h = `<div class="hearts">${hearts(it.extra, true)}</div><div class="h-text">Full recovery, plus ${fmtHearts(it.extra)} extra ${it.extra === 1 ? 'heart' : 'hearts'}</div>`;
    } else if (it.hearts > 0) {
      h = `<div class="hearts">${hearts(it.hearts)}</div><div class="h-text">Restores ${fmtHearts(it.hearts)} ${it.hearts === 1 ? 'heart' : 'hearts'}</div>`;
    } else {
      h = `<div class="h-text dimmed">No hearts restored</div>`;
    }
    let fx;
    if (it.effect && it.effect !== 'LifeMaxUp') {
      fx = `<div class="effect">${sigil(it.effect)}<span>${esc(it.effect_name)}</span>${it.seconds ? `<span class="time">${fmtTime(it.seconds)}</span>` : ''}</div>`;
    } else if (it.mixed) {
      fx = `<div class="effect none">Mixed effects cancel out, so this cooks with none.</div>`;
    } else fx = it.effect === 'LifeMaxUp' ? '' : `<div class="effect none">No effect</div>`;
    const pot = it.pot.map((p) => `<li${missingActors.has(p.actor) ? ' class="miss"' : ''}><button data-mat="${esc(p.actor)}" aria-label="${esc(p.name)} ×${p.n}, show in Materials"><span class="mini">${art(p, 'i')}</span><span class="pn">${esc(p.name)}</span><span class="pc">×${p.n}</span></button></li>`).join('');
    el.innerHTML = banner + `<div class="in"><div class="d-head">${art(it, 'hero')}<div><h2 class="d-name">${esc(it.name)}</h2><div class="d-sub">${plural(it.size, 'ingredient', 'ingredients')}</div></div></div>${h}${fx}<div class="ornament"></div><h3 class="label">In the pot</h3><ul class="pot">${pot}</ul><p class="note">An estimate. A critical cook can add hearts or time.</p></div>`;
  } else {
    const kinds = it.kinds.length ? esc(it.kinds.join(', ')) : 'Not used in cooking';
    const fx = it.effect_name ? `<div class="effect">${sigil(it.effect)}<span>${esc(it.effect_name)}</span></div>` : '';
    const h = it.hearts > 0 ? `<div class="hearts">${hearts(it.hearts)}</div><div class="h-text">${fmtHearts(it.hearts)} ${it.hearts === 1 ? 'heart' : 'hearts'} each when cooked</div>` : '';
    const used = it.used_in.length
      ? `<div class="used">${it.used_in.map((u) => `<button data-dish="${esc(u.id)}">${esc(u.name)}</button>`).join('')}</div>`
      : `<p class="note">None of the dishes on the list use it right now.</p>`;
    el.innerHTML = banner + `<div class="in"><div class="d-head">${art(it, 'hero')}<div><h2 class="d-name">${esc(it.name)}</h2><div class="d-sub">You have ${it.count}</div></div></div><dl class="kv"><dt>Kind</dt><dd>${kinds}</dd></dl>${h}${fx}<div class="ornament"></div><h3 class="label">Used in</h3>${used}</div>`;
  }
}

function ago(mtime) {
  const s = Date.now() / 1000 - mtime;
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(mtime * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
function renderStatus() {
  const el = $('#save');
  if (!S.d) { el.textContent = 'Looking for a save'; return; }
  const sv = S.d.save;
  if (S.d.platform === 'linux') {
    const next = sv.next_scan ? Math.max(0, Math.ceil(sv.next_scan - Date.now() / 1000)) : null;
    const slot = sv.slot ? sv.slot.replace('_', ' ') : null;
    let text;
    if (sv.checking) text = '<span class="spin"></span>Scanning save…';
    else if (sv.error === 'nosave') text = '<span class="warn">No save yet.</span> Save once in the game and the list fills in.';
    else if (sv.error && slot) text = `${esc(slot)}, saved ${ago(sv.mtime)} <span class="warn">· the game is writing a new save</span>`;
    else if (sv.error) text = '<span class="warn">The game is writing the save. Trying again.</span>';
    else text = `${esc(slot)}, saved ${ago(sv.mtime)}`;
    if (next !== null) text += ` · next check in ${next}s`;
    el.innerHTML = text;
    $('#hint').textContent = 'Save mode · reads the newest save';
    return;
  }
  if (sv.error === 'nosave') el.innerHTML = '<span class="warn">No save yet. Save once in the game and the list fills in.</span>';
  else if (sv.error && sv.slot) el.innerHTML = `${esc(sv.slot.replace('_', ' '))}, saved ${ago(sv.mtime)} <span class="warn">· the game is writing a new save</span>`;
  else if (sv.error) el.innerHTML = '<span class="warn">The game is writing the save. Trying again.</span>';
  else if (sv.live === 'on') el.innerHTML = `<span class="live">Live from the game</span> · ${esc(sv.slot.replace('_', ' '))}, saved ${ago(sv.mtime)}`;
  else if (sv.live === 'scanning') el.textContent = `${sv.slot.replace('_', ' ')}, saved ${ago(sv.mtime)} · finding the pouch in the game`;
  else el.textContent = `${sv.slot.replace('_', ' ')}, saved ${ago(sv.mtime)}`;
  const st = S.d.settings;
  if (S.d.platform === 'linux') { $('#hint').textContent = 'Save mode · reads the newest save'; return; }
  const parts = [];
  if (st.combo && st.combo.length) parts.push(comboHTML(st.combo));
  if (st.hotkey) parts.push(`<span class="chip">${esc(keyLabel(st.hotkey))}</span>`);
  $('#hint').innerHTML = parts.length ? `Hide or show ${parts.join(' <span>or</span> ')}` : '';
}

/* ---------- settings ---------- */
function sw(key, on) { return `<button class="switch" role="switch" aria-checked="${!!on}" data-set="${key}"></button>`; }
function seg(key, value, opts) {
  return `<div class="seg" role="group">${opts.map(([v, l]) => `<button data-seg="${key}" data-v='${JSON.stringify(v)}' aria-pressed="${value === v}">${l}</button>`).join('')}</div>`;
}
function monitorsHTML(mons, here) {
  if (!mons.length) return '';
  const minX = Math.min(...mons.map((m) => m.x)), minY = Math.min(...mons.map((m) => m.y));
  const maxX = Math.max(...mons.map((m) => m.x + m.w)), maxY = Math.max(...mons.map((m) => m.y + m.h));
  const k = Math.min(300 / (maxX - minX), 96 / (maxY - minY));
  return `<div class="mons" style="width:${Math.round((maxX - minX) * k)}px;height:${Math.round((maxY - minY) * k)}px">${mons.map((m, i) =>
    `<button class="mon${i === here ? ' here' : ''}" data-mon="${i}" title="${i === here ? 'The helper is here' : 'Move the helper here'}" style="left:${Math.round((m.x - minX) * k)}px;top:${Math.round((m.y - minY) * k)}px;width:${Math.round(m.w * k) - 4}px;height:${Math.round(m.h * k) - 4}px"><span>${i + 1}${m.primary ? ' · main' : ''}<small>${i === here ? 'here' : 'move here'}</small></span></button>`).join('')}</div>`;
}
function renderSettings() {
  const el = $('#settings');
  if (!S.settings || !S.d) return;
  const st = S.d.settings, pad = S.d.pad;
  const linux = S.d.platform === 'linux';
  const padState = !pad.available ? '<span class="s warn">Controller input is not available in this build.</span>'
    : pad.connected ? `<span class="s">${plural(pad.connected, 'controller', 'controllers')} connected. Xbox pads, and others mapped through Steam Input.</span>`
      : '<span class="s warn">No XInput controller found. Xbox pads work directly; PlayStation and Switch pads need Steam Input.</span>';
  const rec = pad.recording;
  const padgrid = S.editCombo ? `<div class="padgrid">${PAD.map(([k, l]) => `<button data-padbtn="${k}" aria-pressed="${st.combo.includes(k)}">${l}</button>`).join('')}</div>` : '';
  const single = st.combo.length === 1 && st.combo[0] !== 'guide';
  const showHide = linux ? `
      <div class="row stack">
        <span class="s">Linux save mode reads the newest save every couple of seconds. The controller combo, keyboard hotkey, live memory and controller navigation are not available here; use the window controls.</span>
      </div>` : `
      <div class="row stack">
        <span class="t">Controller combo</span>
        <div class="combo">${comboHTML(st.combo)}
          <span style="flex:1"></span>
          <button class="btn${rec ? ' live' : ''}" data-act="record">${rec ? 'Hold the buttons, then let go' : 'Record'}</button>
          <button class="btn" data-act="edit">${S.editCombo ? 'Done' : 'Pick buttons'}</button>
        </div>
        ${padgrid}
        ${pad.note ? `<span class="s warn">${esc(pad.note)}</span>` : single ? '<span class="s warn">One button alone also does something in the game. Pick two or more.</span>' : ''}
        ${padState}
        <span class="s">The game still sees these buttons. Clicking both sticks only makes Link crouch for a moment. Guide never reaches the game, though Steam or Game Bar may open on it.</span>
      </div>
      <div class="row"><span class="t">Hold for</span>${seg('hold_ms', st.hold_ms, [[0, 'Tap'], [300, '0.3 s'], [600, '0.6 s'], [1000, '1 s']])}</div>
      <div class="row">
        <span class="t">Keyboard hotkey</span>
        <button class="keycap${S.capturing ? ' live' : ''}" data-act="key">${S.capturing ? 'Press the keys' : esc(keyLabel(st.hotkey))}</button>
        ${S.d.hotkey_error ? `<span class="s warn">That hotkey is ${esc(S.d.hotkey_error)}. Pick another.</span>` : S.capturing ? '<span class="s">Esc cancels. Backspace clears the hotkey.</span>' : ''}
      </div>
      <div class="row"><span class="t">When hidden</span>${seg('hide_mode', st.hide_mode, [['minimize', 'Minimize'], ['hide', 'Hide fully']])}
        <span class="s">${st.hide_mode === 'minimize' ? 'Stays in Alt-Tab and the taskbar, so Alt-Tab also brings it back.' : 'Gone from Alt-Tab and the taskbar until the combo or hotkey shows it.'}</span></div>
      <div class="row"><span class="t">Take focus when shown</span>${sw('take_focus', st.take_focus)}
        <span class="s">Off keeps the game in control while the helper is up. On lets you type in the filter straight away.</span></div>`;
  const windowExtra = linux ? '' : `
      <div class="row stack"><span class="t">Monitor</span>${monitorsHTML(S.d.monitors, S.d.monitor)}<span class="s">Click a screen to move the helper there. Drag the top bar to place it anywhere; it remembers where you left it.</span></div>
      <div class="row"><span class="t">Start hidden</span>${sw('start_hidden', st.start_hidden)}<span class="s">Opens minimized when the game starts, ready for the combo.</span></div>
      <h3 class="label" style="margin-top:22px">Controller in the helper</h3>
      <div class="row"><span class="t">Navigate with the pad</span>${sw('pad_nav', st.pad_nav)}<span class="s">While the helper has focus: D-pad moves the cursor, LB and RB switch lists, Y and X step through the dish effects and sort orders, B hides it.</span></div>`;
  el.innerHTML = `
  <h2>Settings</h2>
  <div class="cols">
    <section>
      <h3 class="label">Show and hide</h3>
      ${showHide}
    </section>
    <section>
      <h3 class="label">Window</h3>
      <div class="row"><span class="t">Always on top</span>${sw('on_top', st.on_top)}<span class="s">Keeps it over the game in borderless fullscreen.</span></div>
      ${windowExtra}
    </section>
  </div>`;
}
function setSetting(key, value) {
  if (S.d) S.d.settings[key] = value;
  call('set_setting', key, value);
  renderSettings(); renderStatus();
}
function openSettings(on) {
  S.settings = on; S.editCombo = false; S.capturing = false;
  $('#frame').classList.toggle('settings-open', on);
  $('#settings').hidden = !on;
  $('#btn-settings').setAttribute('aria-pressed', String(on));
  if (on) renderSettings(); else { call('record_combo', false); requestAnimationFrame(() => placeCursor(true)); }
}

/* ---------- navigation ---------- */
function setTab(t) {
  if (S.tab === t) return;
  S.tab = t;
  call('set_setting', 'tab', t);
  renderTabs(); renderGrid(true);
  $('#gridwrap').scrollTop = 0;
  const c = $('#grid .cell[aria-selected="true"]'); if (c) c.scrollIntoView({ block: 'nearest' });
}
function move(dir) {
  const cells = [...document.querySelectorAll('#grid .cell')];
  if (!cells.length) return;
  let i = cells.findIndex((c) => c.getAttribute('aria-selected') === 'true');
  if (i < 0) i = 0;
  const top = cells[0].offsetTop;
  let cols = cells.findIndex((c) => c.offsetTop !== top); if (cols < 0) cols = cells.length;
  const n = { left: i - 1, right: i + 1, up: i - cols, down: i + cols }[dir];
  if (n >= 0 && n < cells.length) select(cells[n].dataset.id);
}
window.padNav = (action) => {
  if (S.settings) { if (action === 'prev_tab' || action === 'next_tab') openSettings(false); return; }
  if (action === 'prev_tab' || action === 'next_tab') setTab(S.tab === 'dishes' ? 'materials' : 'dishes');
  else if (action === 'filter') { if (S.tab === 'dishes') cycleEffect(); }
  else if (action === 'sort') { if (S.tab === 'dishes') cycleSort(); }
  else move(action);
};

const CODE_KEYS = { Space: 'space', PageUp: 'pageup', PageDown: 'pagedown', Home: 'home', End: 'end', Insert: 'insert',
  Delete: 'delete', Pause: 'pause', ScrollLock: 'scrolllock', Backquote: 'backquote', Minus: 'minus', Equal: 'equal',
  BracketLeft: 'bracketleft', BracketRight: 'bracketright', Backslash: 'backslash', Semicolon: 'semicolon',
  Quote: 'quote', Comma: 'comma', Period: 'period', Slash: 'slash', Tab: 'tab' };
function keySpec(e) {
  let k = null; const c = e.code;
  if (/^Key[A-Z]$/.test(c)) k = c.slice(3).toLowerCase();
  else if (/^Digit\d$/.test(c)) k = c.slice(5);
  else if (/^F\d{1,2}$/.test(c)) k = c.toLowerCase();
  else if (/^Numpad\d$/.test(c)) k = 'num' + c.slice(6);
  else if (CODE_KEYS[c]) k = CODE_KEYS[c];
  if (!k) return null;
  const mods = [e.ctrlKey && 'ctrl', e.shiftKey && 'shift', e.altKey && 'alt', e.metaKey && 'win'].filter(Boolean);
  const standalone = /^f\d+$/.test(k) || ['pause', 'scrolllock', 'insert', 'home', 'end', 'pageup', 'pagedown'].includes(k) || k.startsWith('num');
  if (!mods.length && !standalone) return 'needmod';
  return [...mods, k].join('+');
}

document.addEventListener('keydown', (e) => {
  if (S.capturing) {
    e.preventDefault();
    if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return;
    if (e.key === 'Escape') { S.capturing = false; renderSettings(); return; }
    if (e.key === 'Backspace' && !e.ctrlKey && !e.altKey && !e.shiftKey) { S.capturing = false; setSetting('hotkey', ''); return; }
    const spec = keySpec(e);
    if (spec === 'needmod' || !spec) return;
    S.capturing = false; setSetting('hotkey', spec);
    return;
  }
  const inFilter = document.activeElement === $('#filter');
  if (e.key === 'Escape') {
    e.preventDefault();
    if (inFilter && S.filter) { $('#filter').value = ''; S.filter = ''; renderGrid(true); }
    else if (inFilter) $('#filter').blur();
    else if (S.settings) openSettings(false);
    else if (!S.d || S.d.platform !== 'linux') call('hide');
    return;
  }
  if ((e.key === '/' && !inFilter) || (e.ctrlKey && e.key.toLowerCase() === 'f')) { e.preventDefault(); $('#filter').focus(); $('#filter').select(); return; }
  if (S.settings) return;
  const arrows = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' };
  if (arrows[e.key] && (!inFilter || e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
    e.preventDefault(); if (inFilter) $('#filter').blur(); move(arrows[e.key]); $('#grid').focus({ preventScroll: true }); return;
  }
  if (!inFilter && S.tab === 'dishes' && !e.ctrlKey && !e.altKey && (e.key === 's' || e.key === 'f')) { e.key === 's' ? cycleSort() : cycleEffect(); return; }
  if (!inFilter && (e.key === 'q' || e.key === 'e' || e.key === '[' || e.key === ']')) setTab(e.key === 'q' || e.key === '[' ? 'dishes' : 'materials');
  if (inFilter && e.key === 'Enter') { $('#filter').blur(); $('#grid').focus({ preventScroll: true }); }
});

document.addEventListener('click', (e) => {
  const t = e.target.closest('button'); if (!t) return;
  if (t.classList.contains('cell')) { select(t.dataset.id, false); return; }
  if (t.dataset.sort) { dishOpt('dish_sort', t.dataset.sort); return; }
  if (t.dataset.fx !== undefined) { dishOpt('dish_effect', t.dataset.fx === activeEffect() ? '' : t.dataset.fx); return; }
  if (t.dataset.tab) { if (S.settings) openSettings(false); setTab(t.dataset.tab); return; }
  if (t.dataset.mat) { setTab('materials'); select(t.dataset.mat); return; }
  if (t.dataset.dish) { setTab('dishes'); select(t.dataset.dish); return; }
  if (t.id === 'btn-settings') { openSettings(!S.settings); return; }
  if (t.id === 'btn-hide') { call('hide'); return; }
  if (t.id === 'btn-close') { call('close'); return; }
  if (t.dataset.set) { setSetting(t.dataset.set, t.getAttribute('aria-checked') !== 'true'); return; }
  if (t.dataset.seg) { setSetting(t.dataset.seg, JSON.parse(t.dataset.v)); return; }
  if (t.dataset.mon) { call('move_to_monitor', Number(t.dataset.mon)); return; }
  if (t.dataset.padbtn) {
    const cur = new Set(S.d.settings.combo); const k = t.dataset.padbtn;
    cur.has(k) ? cur.delete(k) : cur.add(k);
    setSetting('combo', PAD.map((p) => p[0]).filter((x) => cur.has(x)));
    return;
  }
  if (t.dataset.act === 'edit') { S.editCombo = !S.editCombo; renderSettings(); return; }
  if (t.dataset.act === 'record') { call('record_combo', !S.d.pad.recording); S.d.pad.recording = !S.d.pad.recording; S.d.pad.note = null; renderSettings(); return; }
  if (t.dataset.act === 'key') { S.capturing = !S.capturing; renderSettings(); return; }
});

$('#tools').addEventListener('wheel', (e) => {
  const c = e.target.closest('.chips');
  if (c && Math.abs(e.deltaY) > Math.abs(e.deltaX)) { c.scrollLeft += e.deltaY; e.preventDefault(); }
}, { passive: false });
$('#filter').addEventListener('input', (e) => { S.filter = e.target.value; renderGrid(true); });

/* drag the bar to move, the edges to resize: native Windows move and size loops */
document.addEventListener('mousedown', (e) => {
  if (e.button !== 0) return;
  const edge = e.target.closest('.edge');
  if (edge) { e.preventDefault(); call('drag', edge.dataset.edge); return; }
  if (e.target.closest('#bar') && !e.target.closest('button')) { e.preventDefault(); call('drag', 'move'); }
});

window.addEventListener('resize', () => placeCursor(true));

/* ---------- icon cache and polling ---------- */
const ICON_CACHE = new Map();
function preloadIcons(p) {
  const urls = new Set();
  for (const item of [...p.dishes, ...p.materials]) {
    if (item.icon) urls.add('icons/' + encodeURIComponent(item.icon));
  }
  for (const url of urls) {
    if (ICON_CACHE.has(url)) continue;
    const img = new Image();
    img.decoding = 'async';
    img.src = url;
    ICON_CACHE.set(url, img);
  }
}

/* ---------- poll Python for state ---------- */
async function poll() {
  try {
    const p = await call('state', S.version);
    if (p) {
      const first = !S.d;
      const newData = p.data_version === undefined || p.data_version !== S.dataVersion;
      S.version = p.version; S.d = p;
      if (first && p.settings.tab) S.tab = p.settings.tab;
      if (p.platform) document.documentElement.dataset.platform = p.platform;
      if (p.platform === 'linux') {
        const hb = $('#btn-hide');
        if (hb) { hb.title = 'Minimize'; hb.setAttribute('aria-label', 'Minimize'); }
      }
      preloadIcons(p);
      renderTabs(); renderStatus();
      if (newData && S.settings && !S.capturing) renderSettings();
      if (newData) { S.dataVersion = p.data_version; renderGrid(true, true); }
    }
  } catch (err) { /* the window is closing */ }
  setTimeout(poll, 500);
}
setInterval(renderStatus, 500);
renderTabs(); renderGrid(true);
window.addEventListener('pywebviewready', () => { if (!S.booted) { S.booted = true; poll(); } });
if (window.pywebview && window.pywebview.api) { S.booted = true; poll(); }
