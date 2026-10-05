/* GOLIDE loader: points of light gather into the GOLIDE mark (a G of points,
   the last one gold), the wordmark fades in, then everything dissolves and
   gathers again. Same motion language as the GOLIDE videos. No dependencies;
   reduced-motion users get a static, gently pulsing mark (CSS). */
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // The mark (64x64 design grid): 11 points on a 290-degree arc, growing,
  // a dim inner point and the gold point where the G's bar ends.
  var MARK = (function () {
    var dots = [];
    for (var i = 0; i < 11; i++) {
      var a = (-40 + i * 29) * Math.PI / 180;
      dots.push({ x: 32 + 22 * Math.cos(a), y: 32 + 22 * Math.sin(a), r: 1.6 + i * 0.22, kind: "ink", alpha: 1 });
    }
    dots.push({ x: 36, y: 32, r: 2.2, kind: "ink", alpha: 0.55 });
    dots.push({ x: 44, y: 32, r: 3.6, kind: "gold", alpha: 1 });
    return dots;
  })();

  function ease(x) { x = Math.max(0, Math.min(1, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
  function rand(seed) { return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
  function rgb(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(v);
    return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [233, 196, 106];
  }

  var GATHER = 1.4, SETTLE = 0.35, HOLD = 1.0, OUT = 0.8, CYCLE = GATHER + SETTLE + HOLD + OUT;

  function Field(canvas, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.loop = !!opts.loop;
    this.word = opts.word !== false;
    this.scale = opts.scale || 0.26;
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
    this.w = Math.max(1, rect.width); this.h = Math.max(1, rect.height);
    this.canvas.width = Math.round(this.w * dpr); this.canvas.height = Math.round(this.h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var size = Math.max(72, Math.min(this.w, this.h) * this.scale);
    this.unit = size / 64;
    this.ox = this.w / 2 - size / 2;
    this.oy = this.h / 2 - size / 2 - (this.word ? size * 0.22 : 0);
    this.wordY = this.oy + size + Math.max(22, size * 0.32);
    this.fontSize = Math.max(14, size * 0.17);
    var r = rand(11), reach = Math.max(this.w, this.h) * 0.6, cx = this.w / 2, cy = this.h / 2, parts = [];
    for (var j = 0; j < MARK.length; j++) {
      var d = MARK[j], k = Math.max(4, Math.round(d.r * d.r * 2.2));
      for (var i = 0; i < k; i++) {
        var a = r() * Math.PI * 2, dist = reach * (0.35 + r() * 0.65), ra = r() * Math.PI * 2, rr = Math.sqrt(r()) * d.r * 0.75;
        parts.push({
          tx: this.ox + (d.x + Math.cos(ra) * rr) * this.unit, ty: this.oy + (d.y + Math.sin(ra) * rr) * this.unit,
          sx: cx + Math.cos(a) * dist, sy: cy + Math.sin(a) * dist,
          bend: (r() - 0.5) * 0.5, delay: (d.kind === "gold" ? 0.35 : r() * 0.3), tw: r() * 6.283,
          size: 0.7 + r() * 0.8, gold: d.kind === "gold"
        });
      }
    }
    this.parts = parts;
    this.ink = rgb("--text", "#ecedef");
    this.gold = rgb("--gold", "#e9c46a");
  };

  Field.prototype.drawMark = function (alpha) {
    var ctx = this.ctx, u = this.unit;
    for (var j = 0; j < MARK.length; j++) {
      var d = MARK[j], c = d.kind === "gold" ? this.gold : this.ink;
      ctx.fillStyle = "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + (alpha * d.alpha).toFixed(3) + ")";
      ctx.beginPath(); ctx.arc(this.ox + d.x * u, this.oy + d.y * u, d.r * u, 0, 6.2832); ctx.fill();
    }
    if (d.kind === "gold" && alpha > 0) {
      var g = this.gold, gx = this.ox + 44 * u, gy = this.oy + 32 * u;
      ctx.fillStyle = "rgba(" + g[0] + "," + g[1] + "," + g[2] + "," + (alpha * 0.18).toFixed(3) + ")";
      ctx.beginPath(); ctx.arc(gx, gy, 3.6 * u * 2.6, 0, 6.2832); ctx.fill();
    }
  };

  Field.prototype.drawWord = function (alpha) {
    if (!this.word || alpha <= 0) return;
    var ctx = this.ctx, c = this.ink, word = "GOLIDE", sp = this.fontSize * 0.42, total = 0, i;
    ctx.font = "500 " + this.fontSize + "px Geist, ui-sans-serif, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    for (i = 0; i < word.length; i++) total += ctx.measureText(word[i]).width + (i < word.length - 1 ? sp : 0);
    var x = (this.w - total) / 2;
    ctx.fillStyle = "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + alpha.toFixed(3) + ")";
    for (i = 0; i < word.length; i++) { ctx.fillText(word[i], x, this.wordY); x += ctx.measureText(word[i]).width + sp; }
  };

  Field.prototype.frame = function (now) {
    if (!this.running) return;
    var t = (now - this.start) / 1000;
    var p = this.loop ? t % CYCLE : Math.min(t, GATHER + SETTLE + HOLD);
    var ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);
    var partAlpha = 1, markAlpha = 0, wordAlpha = 0, burst = 0;
    if (p < GATHER) { partAlpha = 1; }
    else if (p < GATHER + SETTLE) { var s = ease((p - GATHER) / SETTLE); markAlpha = s; partAlpha = 1 - s; wordAlpha = s * 0.6; }
    else if (p < GATHER + SETTLE + HOLD || !this.loop) { markAlpha = 1; partAlpha = 0; wordAlpha = Math.min(1, 0.6 + (p - GATHER - SETTLE) * 1.5); }
    else { burst = ease((p - GATHER - SETTLE - HOLD) / OUT); markAlpha = 1 - burst * 2; partAlpha = 1 - burst; wordAlpha = 1 - burst * 1.6; }

    if (partAlpha > 0.01) {
      for (var i = 0; i < this.parts.length; i++) {
        var q = this.parts[i], x, y, a;
        if (p < GATHER + SETTLE) {
          var k = ease((p / GATHER - q.delay) / (1 - q.delay));
          var dx = q.tx - q.sx, dy = q.ty - q.sy, arc = Math.sin(Math.PI * k) * q.bend;
          x = q.sx + dx * k - dy * arc; y = q.sy + dy * k + dx * arc; a = (0.25 + 0.75 * k) * partAlpha;
        } else {
          var ox = q.tx - this.w / 2, oy = q.ty - this.h / 2, len = Math.hypot(ox, oy) || 1;
          x = q.tx + (ox / len) * burst * 70 + Math.cos(q.tw) * burst * 26;
          y = q.ty + (oy / len) * burst * 70 + Math.sin(q.tw) * burst * 26; a = partAlpha;
        }
        var c = q.gold ? this.gold : this.ink;
        ctx.fillStyle = "rgba(" + this.gold[0] + "," + this.gold[1] + "," + this.gold[2] + "," + (a * 0.14).toFixed(3) + ")";
        ctx.beginPath(); ctx.arc(x, y, q.size * 3.2, 0, 6.2832); ctx.fill();
        ctx.fillStyle = "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a.toFixed(3) + ")";
        ctx.beginPath(); ctx.arc(x, y, q.size, 0, 6.2832); ctx.fill();
      }
    }
    if (markAlpha > 0.01) this.drawMark(Math.max(0, markAlpha));
    this.drawWord(Math.max(0, wordAlpha));

    var held = p >= GATHER + SETTLE && p < GATHER + SETTLE + HOLD;
    if (this.onHold && held) { var cb = this.onHold; this.onHold = null; cb(); }
    if (!this.loop && t > GATHER + SETTLE + 0.3) { this.stop(false); return; }
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
    splashField = new Field(canvas, { loop: true, scale: 0.22 });
  }

  // Close once the app has its data, at a moment the mark is fully formed,
  // and never before one full gather so it doesn't flash.
  function finishSplash() {
    var splash = document.getElementById("splash");
    if (!splash || splash.classList.contains("done")) return;
    function close() {
      splash.classList.add("done");
      setTimeout(function () { if (splashField) splashField.stop(true); splash.remove(); }, 600);
    }
    if (!splashField) { setTimeout(close, 300); return; }
    var elapsed = (performance.now() - splashStarted) / 1000, inCycle = elapsed % CYCLE;
    if (elapsed >= GATHER + SETTLE && inCycle >= GATHER + SETTLE && inCycle < GATHER + SETTLE + HOLD) close();
    else splashField.onHold = function () { setTimeout(close, 450); };
  }

  function formOnce(canvas) {
    if (!canvas || reduce) return null;
    return new Field(canvas, { loop: false, scale: 0.62, word: false });
  }

  window.GolideLoader = { finish: finishSplash, formOnce: formOnce };

  var fontReady = document.fonts && document.fonts.load ? document.fonts.load("500 40px Geist") : Promise.resolve();
  var started = false;
  function go() { if (!started) { started = true; startSplash(); } }
  fontReady.then(go, go);
  setTimeout(go, 400);
  setTimeout(finishSplash, 9000); // never trap the page behind the splash
})();
