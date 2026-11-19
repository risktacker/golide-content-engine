import { M, camFromKeys, idle, blinkAt, q, ramp, clamp, lerp } from './motion.js';

export const FPS = 30, TOTAL = 309;
const DECK = 0;

export const SHOTS = [
  { id: 'identity', a: 0, b: 44, light: 'day' },
  { id: 'money', a: 45, b: 99, light: 'golden' },
  { id: 'race', a: 100, b: 139, light: 'night' },
  { id: 'founder', a: 140, b: 199, light: 'night' },
  { id: 'openai', a: 200, b: 240, light: 'night' },
  { id: 'finish', a: 241, b: 308, light: 'golden' },
];
export const shotAt = (f) => SHOTS.find((s) => f >= s.a && f <= s.b) || SHOTS[SHOTS.length - 1];

export const LIGHTS = {
  day: {
    az: 135, el: 48, sky: '#c8dcf2', ground: '#747983', hemi: 1.15,
    sun: '#fff0d8', sunI: 2.55, fog: '#c9dbea', fogNear: 65, fogFar: 620,
    skyTop: '#4284cf', skyHor: '#c7def2', sat: 1.08, gain: '#ffffff', lift: '#000000',
    waterDeep: '#2f6f8f', waterShal: '#5fa8bf', glint: '#e9f6ff', vig: 0.2, shadowExt: 18,
  },
  golden: {
    az: 18, el: 18, sky: '#c9b2c4', ground: '#73584c', hemi: 1.05,
    sun: '#ffba72', sunI: 2.85, fog: '#eeb98f', fogNear: 58, fogFar: 580,
    skyTop: '#7774ad', skyHor: '#ffc58b', sunDisc: '#fff0c7', sunSize: 0.0035,
    sat: 1.12, gain: '#fff3e7', lift: '#080304', waterDeep: '#3c5c83', waterShal: '#d29872', glint: '#ffe6ba', vig: 0.25, shadowExt: 20,
  },
  night: {
    az: 120, el: 34, sky: '#7189b2', ground: '#25314a', hemi: 1.05,
    sun: '#b8ddff', sunI: 2.3, fog: '#263b62', fogNear: 55, fogFar: 470,
    skyTop: '#101a38', skyHor: '#405c85', sat: 1.14, gain: '#dcecff', lift: '#02050c',
    waterDeep: '#173e62', waterShal: '#337a9c', glint: '#bfeaff', vig: 0.28, shadowExt: 18,
  },
};
export const lightFor = (S, f) => ({ ...LIGHTS[S.light] });

const CAMS = {
  identity: [
    { f: 0, pos: [1.9, 2.0, 4.8], look: [0, 1.15, 0], fov: 32 },
    { f: 44, pos: [8.0, 7.4, 14.5], look: [0, 4.4, -2.4], fov: 46, roll: -1.5, ease: 'easeOut', path: [[4.0, 3.2, 7.5]] },
  ],
  money: [
    { f: 45, pos: [43.8, 0.85, 6.0], look: [40, 1.0, 0], fov: 39 },
    { f: 99, pos: [45.0, 6.5, 12.5], look: [40, 4.7, 0], fov: 43, roll: 2, ease: 'smooth', path: [[44.4, 3.2, 8.4]] },
  ],
  race: [
    { f: 100, pos: [72.5, 2.2, 8.4], look: [77.0, 0.75, 0], fov: 43 },
    { f: 139, pos: [84.5, 2.6, 9.3], look: [86.5, 0.72, 0], fov: 39, roll: -3, ease: 'easeOut' },
  ],
  founder: [
    { f: 140, pos: [123.5, 2.25, 7.3], look: [120, 1.0, -1.8], fov: 42 },
    { f: 199, pos: [130.5, 2.8, 10.5], look: [125.2, 1.0, 0], fov: 39, roll: 2, ease: 'easeOut', path: [[126.0, 2.3, 8.3]] },
  ],
  openai: [
    { f: 200, pos: [159.0, 0.68, 4.2], look: [159.5, 0.45, 0], fov: 31, roll: -3 },
    { f: 240, pos: [164.5, 4.1, 10.0], look: [160, 4.4, -5.2], fov: 35, roll: 3, ease: 'smooth' },
  ],
  finish: [
    { f: 241, pos: [197.0, 3.1, 10.5], look: [201, 0.85, 0], fov: 42 },
    { f: 308, pos: [217.5, 5.2, 16.0], look: [213, 1.2, 0], fov: 47, roll: -2, ease: 'easeOut', path: [[207, 3.6, 11.8]] },
  ],
};

const KICKS = [{ f: 167, a: 0.045 }, { f: 200, a: 0.055 }, { f: 276, a: 0.04 }, { f: 296, a: 0.035 }];
export const camAt = (f) => {
  const S = shotAt(f);
  const c = camFromKeys(CAMS[S.id], f, { kicks: KICKS });
  const cut = [45, 100, 140, 200, 241].find((v) => f >= v && f < v + 4);
  c.flash = cut === undefined ? 0 : 0.82 * (1 - (f - cut) / 4);
  c.shadowAt = c.look;
  return c;
};

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
export const dofAt = (f) => {
  const S = shotAt(f), C = camAt(f);
  const targets = {
    identity: [0, 1.35, 0], money: [40, 4.9, 0], race: [82, 0.9, 0],
    founder: [121, 1.1, 0], openai: [160, 2.8, -5.8], finish: [211, 0.9, 0],
  };
  const wide = S.id === 'finish' ? 3 : 0;
  return { focus: dist(C.pos, targets[S.id]), cinf: S.id === 'openai' ? 13 : S.id === 'race' ? 7 : wide || 9, near: 1 };
};

export const worldAt = (f) => {
  const S = shotAt(f);
  const zone = { identity: 0, money: 1, race: 2, founder: 3, openai: 4, finish: 5 }[S.id];
  return { zone, p: clamp((f - S.a) / Math.max(1, S.b - S.a)) };
};

const HERO = {
  tunic: '#252b36', sleeve: '#252b36', skin: '#e9b98f', hair: '#3a2b22', style: 'short',
  pants: '#263b58', shoes: '#17191f', hood: true,
};
const OPEN_DRIVER = {
  tunic: '#ece9e1', sleeve: '#ece9e1', skin: '#9b6749', hair: '#241b18', style: 'curly',
  pants: '#323a46', shoes: '#17191f', jacket: true, shirt: '#f6f3eb', tie: '#22262d',
};
const GOOGLE_DRIVER = {
  tunic: '#3478c8', sleeve: '#3478c8', skin: '#f0c29e', hair: '#5b3928', style: 'swoop',
  pants: '#243b61', shoes: '#15171b', jacket: true, shirt: '#f6f4ee', tie: '#d1443e',
};
const ANTH_DRIVER = {
  tunic: '#b9653f', sleeve: '#b9653f', skin: '#bf7e59', hair: '#241a17', style: 'bun',
  pants: '#3c3441', shoes: '#17151a', jacket: true, shirt: '#f2e7db', tie: '#242027',
};

const actor = (T, who, outfit, opts, pos, extra = {}) => ({
  key: who + JSON.stringify(opts),
  draw: (p) => T.modernFront(p, outfit, opts),
  x: pos[0], y: pos[1], z: pos[2], ...extra,
});
const alive = (f, seed, opts = {}) => ({ ...idle(f, seed), blink: blinkAt(f, seed), seed, ...opts });

export const actorsAt = (f, T) => {
  const S = shotAt(f), out = [], p = clamp((f - S.a) / Math.max(1, S.b - S.a));
  if (S.id === 'identity') {
    out.push(actor(T, 'hero', HERO, alive(f, 3, {
      expr: f > 25 ? 'stern' : 'neutral', look: 0.2, facing: 0, L: 'hang', R: f > 20 ? 'up' : 'hang',
    }), [0, DECK, 0.4]));
  }
  if (S.id === 'money') {
    const balance = Math.sin((f - 45) * 0.2) * 2.5;
    out.push(actor(T, 'heroMoney', HERO, alive(f, 3, {
      expr: f < 70 ? 'grin' : 'nervous', L: 'up', R: 'up', tilt: q(balance, 1), headTilt: q(-balance * 0.5, 1),
    }), [40, 4.56, 0], { ground: 4.56 }));
  }
  if (S.id === 'race') {
    const darkX = 74 + p * 7.0, openX = 73 + p * 12.5;
    out.push(actor(T, 'heroRace', HERO, alive(f, 3, {
      expr: 'nervous', seated: true, L: 'reach', R: 'reach', facing: 1, look: 0.8, lift: 0.15,
    }), [darkX - 0.3, DECK + 0.3, 1.45], { blob: false }));
    out.push(actor(T, 'openDriver', OPEN_DRIVER, alive(f, 17, {
      expr: 'stern', seated: true, L: 'reach', R: 'reach', facing: 1, look: 0.5,
    }), [openX - 0.3, DECK + 0.3, -1.25], { blob: false }));
  }
  if (S.id === 'founder') {
    const proud = f < 167;
    out.push(actor(T, 'heroFounder', HERO, alive(f, 3, {
      expr: proud ? 'grin' : 'shock', L: 'reach', R: 'reach', facing: 1,
      lift: q(M.smooth(ramp(f, 146, 166)), 2), tilt: proud ? -3 : 5,
    }), [118.0, DECK, 0.15]));
  }
  if (S.id === 'openai') {
    out.push(actor(T, 'heroReveal', HERO, alive(f, 3, {
      expr: 'shock', L: 'up', R: 'up', facing: -1, look: -0.5, headTilt: -4,
    }), [157.3, DECK, -1.5], { s: 0.92 }));
  }
  if (S.id === 'finish') {
    const gx = 198 + p * 17.5, ax = 197.5 + p * 18.0, hx = 195 + p * 10.5;
    out.push(actor(T, 'googleDriver', GOOGLE_DRIVER, alive(f, 21, {
      expr: 'grin', seated: true, L: 'reach', R: 'reach', facing: 1,
    }), [gx - 0.3, DECK + 0.3, -1.7], { blob: false }));
    out.push(actor(T, 'anthDriver', ANTH_DRIVER, alive(f, 22, {
      expr: 'grin', seated: true, L: 'reach', R: 'reach', facing: 1,
    }), [ax - 0.3, DECK + 0.3, 1.25], { blob: false }));
    out.push(actor(T, 'heroFinal', HERO, alive(f, 3, {
      expr: f > 284 ? 'pained' : 'nervous', seated: true, L: 'reach', R: 'reach', facing: 1, look: 0.9,
    }), [hx - 0.3, DECK + 0.3, 3.45], { blob: false }));
  }
  return out;
};

const FX = (key, draw, pos, s, extra = {}) => ({
  key, draw, x: pos[0], y: pos[1], z: pos[2], s, blob: false, shadow: false, order: 6, ...extra,
});

export const fxAt = (f, T) => {
  const S = shotAt(f), out = [];
  if (S.id === 'money') {
    for (let i = 0; i < 11; i++) {
      const t = ((f - 45) * 0.018 + i / 11) % 1;
      const x = 36.7 + i * 0.66 + Math.sin(i * 2.1 + f * 0.08) * 0.35;
      const y = 6.3 - t * 6.0;
      const z = -1.8 + (i % 5) * 0.8;
      out.push(FX('bill' + i + q(t, 1), (pen) => T.billFx(pen, t * 5 + i, 0.82 + 0.18 * Math.sin(t * Math.PI)), [x, y, z], 0.18, { roll: t * 4 }));
    }
  }
  return out;
};
