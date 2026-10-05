/* GOLIDE loader: points of light gather into the wordmark, hold, dissolve and
   gather again (the same motion language as the GOLIDE videos). Used full
   screen while Studio loads, and once (form and hold) in the dashboard hero.
   No dependencies. Respects prefers-reduced-motion (CSS shows a static word). */
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function ease(x) { x = Math.max(0, Math.min(1, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
  function rand(seed) { return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  function hexToRgb(hex) {
    var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
    return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [233, 196, 106];
  }

  // Points sampled from the wordmark drawn on an offscreen canvas.
  function wordPoints(width, height, count, fontSize) {
    var off = document.createElement("canvas");
    off.width = Math.ceil(width); off.height = Math.ceil(height);
    var c = off.getContext("2d");
    c.fillStyle = "#fff";
    c.textBaseline = "middle";
    c.font = "500 " + fontSize + "px Geist, ui-sans-serif, system-ui, sans-serif";
    var word = "GOLIDE", spacing = fontSize * 0.42;
    var total = 0, i;
    for (i = 0; i < word.length; i++) total += c.measureText(word[i]).width + (i < word.length - 1 ? spacing : 0);
    var x = (width - total) / 2, y = height / 2;
    for (i = 0; i < word.length; i++) { c.fillText(word[i], x, y); x += c.measureText(word[i]).width + spacing; }
    var data = c.getImageData(0, 0, off.width, off.height).data, pts = [];
    var step = Math.max(1, Math.round(fontSize / 22));
    for (var yy = 0; yy < off.height; yy += step) {
      for (var xx = 0; xx < off.width; xx += step) {
        if (data[(yy * off.width + xx) * 4 + 3] > 140) pts.push([xx, yy]);
      }
    }
    var r = rand(7), out = [];
    for (i = 0; i < count && pts.length; i++) out.push(pts[Math.floor(r() * pts.length)]);
    return out;
  }

  function Field(canvas, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.loop = !!opts.loop;
    this.density = opts.density || 1;
    this.fontScale = opts.fontScale || 0.16;
    this.start = performance.now();
    this.running = true;
    this.onHold = null;
    this.resize();
    var self = this;
    this._resize = function () { self.resize(); };
    window.addEventListener("resize", this._resize);
    this.frame = this.frame.bind(this);
    requestAnimationFrame(this.frame);
  }

  Field.prototype.resize = function () {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var rect = this.canvas.getBoundingClientRect();
    this.w = Math.max(1, rect.width); this.h = Math.max(1, rect.height); this.dpr = dpr;
    this.canvas.width = Math.round(this.w * dpr); this.canvas.height = Math.round(this.h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var fontSize = Math.max(22, Math.min(this.w * this.fontScale, this.h * 0.32, 96));
    var count = Math.round(Math.min(360, Math.max(160, this.w * 0.36)) * this.density);
    var targets = wordPoints(this.w, this.h, count, fontSize);
    var r = rand(11), cx = this.w / 2, cy = this.h / 2, reach = Math.max(this.w, this.h) * 0.62;
    this.parts = targets.map(function (t, i) {
      var a = r() * Math.PI * 2, d = reach * (0.35 + r() * 0.65);
      return {
        tx: t[0], ty: t[1],
        sx: cx + Math.cos(a) * d, sy: cy + Math.sin(a) * d,
        bend: (r() - 0.5) * 0.5, delay: r() * 0.35, tw: r() * Math.PI * 2, size: 0.8 + r() * 0.9,
        hot: i % 9 === 0
      };
    });
    this.gold = hexToRgb(cssVar("--gold", "#e9c46a"));
  };

  // One cycle: gather 1.5 s, hold 0.9 s, dissolve 0.9 s.
  var GATHER = 1.5, HOLD = 0.9, OUT = 0.9, CYCLE = GATHER + HOLD + OUT;

  Field.prototype.frame = function (now) {
    if (!this.running) return;
    var t = (now - this.start) / 1000, phaseT = this.loop ? t % CYCLE : Math.min(t, GATHER + HOLD);
    var ctx = this.ctx, g = this.gold;
    ctx.clearRect(0, 0, this.w, this.h);
    for (var i = 0; i < this.parts.length; i++) {
      var p = this.parts[i], x, y, alpha;
      if (phaseT < GATHER) {
        var k = ease((phaseT / GATHER - p.delay * 0.4) / (1 - p.delay * 0.4));
        var dx = p.tx - p.sx, dy = p.ty - p.sy, arc = Math.sin(Math.PI * k) * p.bend;
        x = p.sx + dx * k - dy * arc; y = p.sy + dy * k + dx * arc;
        alpha = 0.25 + 0.75 * k;
      } else if (phaseT < GATHER + HOLD || !this.loop) {
        x = p.tx; y = p.ty;
        alpha = 0.78 + 0.22 * Math.sin(t * 3 + p.tw);
      } else {
        var o = ease((phaseT - GATHER - HOLD) / OUT);
        var ox = p.tx - this.w / 2, oy = p.ty - this.h / 2, len = Math.hypot(ox, oy) || 1;
        x = p.tx + (ox / len) * o * 60 + Math.cos(p.tw) * o * 30;
        y = p.ty + (oy / len) * o * 60 + Math.sin(p.tw) * o * 30;
        alpha = 1 - o;
      }
      var s = p.size;
      ctx.fillStyle = "rgba(" + g[0] + "," + g[1] + "," + g[2] + "," + (alpha * 0.16).toFixed(3) + ")";
      ctx.beginPath(); ctx.arc(x, y, s * 3.4, 0, 6.2832); ctx.fill();
      ctx.fillStyle = p.hot ? "rgba(255,248,230," + alpha.toFixed(3) + ")"
                            : "rgba(" + g[0] + "," + g[1] + "," + g[2] + "," + alpha.toFixed(3) + ")";
      ctx.beginPath(); ctx.arc(x, y, s, 0, 6.2832); ctx.fill();
    }
    if (this.onHold && phaseT >= GATHER && phaseT < GATHER + HOLD) { var cb = this.onHold; this.onHold = null; cb(); }
    if (!this.loop && t > GATHER + HOLD + 0.2) { this.stop(false); return; }
    requestAnimationFrame(this.frame);
  };

  Field.prototype.stop = function (clear) {
    this.running = false;
    window.removeEventListener("resize", this._resize);
    if (clear) this.ctx.clearRect(0, 0, this.w, this.h);
  };

  var splashField = null, splashStarted = performance.now();

  function startSplash() {
    var canvas = document.getElementById("splash-canvas");
    if (!canvas || reduce) return;
    splashField = new Field(canvas, { loop: true, fontScale: 0.11 });
  }

  // Close the splash once the app has its data, at the moment the word is
  // fully formed, and never sooner than one gather so it doesn't flash.
  function finishSplash() {
    var splash = document.getElementById("splash");
    if (!splash) return;
    function close() {
      splash.classList.add("done");
      setTimeout(function () { if (splashField) splashField.stop(true); splash.remove(); }, 600);
    }
    if (!splashField) { setTimeout(close, 300); return; }
    var elapsed = (performance.now() - splashStarted) / 1000;
    var inCycle = elapsed % CYCLE;
    if (elapsed >= GATHER && inCycle >= GATHER && inCycle < GATHER + HOLD) close();
    else {
      splashField.onHold = function () { setTimeout(close, 350); };
      if (elapsed < GATHER) return;
    }
  }

  function formOnce(canvas) {
    if (!canvas || reduce) return null;
    return new Field(canvas, { loop: false, fontScale: 0.15, density: 1.6 });
  }

  window.GolideLoader = { finish: finishSplash, formOnce: formOnce };

  var fontReady = document.fonts && document.fonts.load ? document.fonts.load("500 40px Geist") : Promise.resolve();
  var started = false;
  function go() { if (!started) { started = true; startSplash(); } }
  fontReady.then(go, go);
  setTimeout(go, 400); // never wait long for the font
  setTimeout(finishSplash, 9000); // never trap the page behind the splash
})();
