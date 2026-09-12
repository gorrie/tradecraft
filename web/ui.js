/* TRADECRAFT — the page's UI. It grades NOTHING.
 *
 * Every score on this page comes from window.Instrument (instrument/engine.js) run over the
 * payload export_web.py emits (instrument/instrument.json). This file carries no cue, no
 * weight, no threshold and no grading arithmetic of its own.
 *
 * Why that matters: until 2026-09-07 this page shipped its OWN grade() with its OWN inline
 * LENSES snapshot, extracted from the taxonomies by a second exporter. It skipped word
 * boundaries, ignored cue exclusions, scored five lenses the taxonomies declare not
 * cue-matchable, and was never under the parity gate. Two front-ends, two graders, drifting --
 * the exact defect tradecraft/README.md "The bug that made the parity check non-negotiable"
 * describes, rebuilt on the page that describes it.
 *
 * Standalone demo (web/demo.html) and the site page (/tech/tradecraft/) run this same file:
 * the demo inlines engine.js and the payload as window.TRADECRAFT_PAYLOAD; the site loads
 * engine.js and fetches the payload. tradecraft/tools/test_engine_parity.py asserts both.
 */
(function () {
  'use strict';

  var P = null;          // the payload; null until loaded
  var PARITY = null;     // Instrument.selfTest(P) result

  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* Tier position 0/1/2 drives the stripe colour. Derived from the lens's own tier table,
   * not from hard-coded cut points, so a taxonomy that moves its tiers moves the colour. */
  function tierPos(tax, tierLabel) {
    var tiers = (tax.config && tax.config.tiers || []).slice()
      .sort(function (a, b) { return a.min - b.min; });
    var i = -1;
    tiers.forEach(function (t, k) { if (t.label === tierLabel) i = k; });
    if (i < 0) return 0;
    return Math.min(2, Math.max(0, i + (3 - Math.min(3, tiers.length))));
  }

  function detectionOf(tax, detectionId) {
    for (var mi = 0; mi < tax.markers.length; mi++) {
      var m = tax.markers[mi];
      for (var di = 0; di < m.detections.length; di++) {
        if (m.detections[di].id === detectionId) return { marker: m, det: m.detections[di] };
      }
    }
    return null;
  }

  /* The ruler. The payload's own note: "the page must not render an index without the floor
   * beside it." Same selection rule as instrument/ui.js -- the statistic must match the
   * lens's STATE, or an index lens prints a firing-rate MDE as if it qualified the index. */
  function ruler(lensId) {
    var R = P.resolution;
    if (!R || !R.lenses || !R.lenses[lensId]) return '';
    var info = R.lenses[lensId], floors = info.floors || [];
    function pick(statistic) {
      var m = floors.filter(function (f) {
        return f.statistic === statistic && f.publishable_mde && f.mde != null;
      });
      return m.length ? m[0] : null;
    }
    var label, detail;
    if (info.state === 'index') {
      var idx = pick('index-points');
      label = 'index-bearing';
      detail = idx ? 'resolves a difference of ' + idx.mde + ' index points'
                   : 'floor measured over a corpus a reader cannot rebuild; no MDE is published';
    } else {
      var rate = pick('firing-rate');
      label = info.state === 'graph' ? 'graph lens' : 'receipts-only';
      detail = rate ? 'no index. A corpus of ' + (rate.n || 100) + ' documents can show this firing ' +
                      'above background at a true rate of ' + rate.mde
                    : 'no index. Firings are receipts, not a score';
    }
    /* The length-invariant unit (issue #7): occurrences per 1,000 background words, with the
     * exact interval and the length-homogeneity verdict. "no power" is printed as no power;
     * a lens the test could not check never reads as checked. */
    var occ = info.occurrence_rate, occTxt = '';
    if (occ && occ.rate_per_1k != null) {
      occTxt = '<span class="ruler-occ">background ' + occ.rate_per_1k + ' per 1,000 words' +
        (occ.ci95 ? ' [' + occ.ci95[0] + ', ' + occ.ci95[1] + ']' : '') +
        ' over ' + occ.kwords + 'k words · length-invariant: ' + esc(occ.length_invariance) +
        ' · pool includes vendored news a reader cannot rebuild</span>';
    }
    return '<div class="ruler"><b>' + label + '</b> — ' + esc(detail) + occTxt + '</div>';
  }

  function snippet(text, hit) {
    var a = Math.max(0, hit.char_start - 42), b = Math.min(text.length, hit.char_end + 42);
    return (a > 0 ? '…' : '') + esc(text.slice(a, hit.char_start)) +
      '<mark>' + esc(text.slice(hit.char_start, hit.char_end)) + '</mark>' +
      esc(text.slice(hit.char_end, b)) + (b < text.length ? '…' : '');
  }

  function renderLens(row, text) {
    var r = row.result, tax = row.tax, q = tierPos(tax, r.tier);
    var pct = function (x) { return Math.round(x * 100) + '%'; };
    var fired = row.hits.length > 0;
    var indexHtml = PARITY && PARITY.pass === PARITY.total
      ? r.index.toFixed(0)
      : '<span title="engine drift: scores suppressed">—</span>';
    var h = '<div class="lens q' + q + (fired ? '' : ' quiet') + '" data-id="' + esc(tax.id) + '">' +
      '<div class="lhead">' +
        '<div class="lname"><h3>' + esc(tax.name) + '</h3><div class="d">' + esc(tax.description) + '</div></div>' +
        '<span class="tier t' + q + '">' + esc(r.tier) + '</span>' +
        '<div class="score">' + indexHtml + '</div>' +
      '</div>' +
      '<div class="bars">' +
        '<div class="b">breadth ' + r.markers_present.length + '/' + tax.markers.length +
          '<div class="track"><div class="fill" style="width:' + pct(r.breadth) + '"></div></div></div>' +
        '<div class="b">intensity<div class="track"><div class="fill" style="width:' + pct(r.intensity) + '"></div></div></div>' +
        '<div class="b">density<div class="track"><div class="fill" style="width:' + pct(r.density) + '"></div></div></div>' +
      '</div>' +
      ruler(tax.id);
    if (fired) {
      h += '<div class="receipts">';
      row.hits.forEach(function (hit) {
        var d = detectionOf(tax, hit.detection_id);
        var gold = d && d.det.gold && d.det.gold.length ? d.det.gold[0] : null;
        h += '<div class="receipt">' +
          '<div class="m">' + esc(d ? d.marker.name : hit.marker_id) +
            ' <code>' + esc(hit.detection_id) + '</code></div>' +
          '<div class="snip">' + snippet(text, hit) + '</div>' +
          (d && d.det.definition ? '<div class="def">' + esc(d.det.definition) + '</div>' : '') +
          (gold ? '<div class="gold">gold exemplar: ' + esc(gold.text) +
                  (gold.source ? ' <span class="src">— ' + esc(gold.source) + '</span>' : '') + '</div>' : '') +
        '</div>';
      });
      h += '</div>';
    }
    return h + '</div>';
  }

  function render(text) {
    var out = el('out');
    if (!text.trim()) { out.innerHTML = '<div class="empty">Paste some text and hit Detect.</div>'; return; }
    var rows = window.Instrument.runAll(text, P);
    var words = window.Instrument.tokenCount(text);
    var scored = rows.filter(function (r) { return r.result; });
    var skipped = rows.filter(function (r) { return r.skipped; });
    var fired = scored.filter(function (r) { return r.hits.length; });
    var quiet = scored.filter(function (r) { return !r.hits.length; });

    var h = '<div class="summary">' + words + ' words · ' + fired.length + ' of ' + scored.length +
      ' cue-scored lenses fired · <b>method flagged, not judged</b> — expand a lens to read the receipts.</div>';
    if (PARITY && PARITY.pass !== PARITY.total) {
      h += '<div class="drift"><b>Engine drift.</b> ' + PARITY.pass + ' of ' + PARITY.total +
        ' exported fixtures reproduce here. Indices are suppressed until the browser engine and the ' +
        'Python detector agree again; the receipts below are still the literal matches.</div>';
    }
    if (!fired.length) {
      h += '<div class="empty">No markers fired at the cue floor. That is not a clean bill of health — ' +
        'the full engine reads context the cue floor cannot. It just means this text does not trip the literal markers.</div>';
    }
    fired.forEach(function (r) { h += renderLens(r, text); });
    quiet.forEach(function (r) { h += renderLens(r, text); });
    if (skipped.length) {
      h += '<div class="skipped"><b>Not measurable here:</b> ' +
        skipped.map(function (r) { return esc(r.tax.name); }).join(', ') +
        ' — these lenses are declared not cue-matchable in their own taxonomy. They need a model to ' +
        'judge context, so they are listed, not scored.</div>';
    }
    h += '<div class="verdictbar"><b>No verdict.</b> Tradecraft shows you the method and the exact words ' +
      'that fired it. Whether that is a problem is your call, not the tool’s — that is the whole design. ' +
      'The cue floor over-fires; the full engine verifies each hit in context before it stands.</div>';
    out.innerHTML = h;
  }

  /* Sample buttons come from the exported FIXTURES -- texts the Python detector has already
   * graded, with its expected result shipped beside them -- so the page carries no hand-typed
   * sample either. One per lens, the fixture with the highest expected index, for the first
   * four cue-scored lenses in this preference order that have a fixture at all. */
  var PREFER = ['institutional_permeation', 'adept_speech', 'sourcing_asymmetry',
                'reference_capture', 'narrative_management', 'militant_mobilization',
                'subculture_register'];

  function samples() {
    var best = {};
    (P.fixtures || []).forEach(function (f) {
      var tax = P.taxonomies[f.lens];
      if (!tax || tax.llm_only) return;
      if (!best[f.lens] || f.expect.index > best[f.lens].expect.index) best[f.lens] = f;
    });
    var picked = [];
    PREFER.forEach(function (lid) { if (best[lid] && picked.length < 4) picked.push(best[lid]); });
    return picked;
  }

  function mountSamples() {
    var box = document.querySelector('.samples');
    if (!box) return;
    var h = '<span>try:</span>';
    samples().forEach(function (f) {
      h += '<button type="button" data-fixture="' + esc(f.id) + '" title="fixture ' + esc(f.id) +
        ' — Python expects index ' + esc(f.expect.index) + '">' + esc(P.taxonomies[f.lens].name) + '</button>';
    });
    h += '<button type="button" data-fixture="clear">clear</button>';
    box.innerHTML = h;
    box.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      var ta = el('in');
      if (b.dataset.fixture === 'clear') { ta.value = ''; el('out').innerHTML = ''; return; }
      var f = (P.fixtures || []).filter(function (x) { return x.id === b.dataset.fixture; })[0];
      if (!f) return;
      ta.value = f.text; render(ta.value);
    });
  }

  function boot() {
    PARITY = window.Instrument.selfTest(P);
    /* Three kinds of lens in the payload, counted from the payload: model-only (declared
     * `cue_matching` unusable), cue-bearing (what this page can fire), and lenses with no
     * text cues at all (revolving_door is a network lens). "11 of 16 run here" would count
     * that last one as runnable; it is loaded and can never fire. */
    var ids = Object.keys(P.taxonomies), nModel = 0, nCue = 0, nNoCue = 0;
    ids.forEach(function (k) {
      var t = P.taxonomies[k];
      if (t.llm_only) { nModel++; return; }
      var cues = 0;
      t.markers.forEach(function (m) { m.detections.forEach(function (d) { cues += d.cues.length; }); });
      if (cues) nCue++; else nNoCue++;
    });
    var status = el('tc-status');
    if (status) {
      status.innerHTML = (PARITY.pass === PARITY.total
        ? '<b>' + PARITY.pass + '/' + PARITY.total + ' fixtures</b> reproduce the Python detector in this browser'
        : '<b class="bad">' + PARITY.pass + '/' + PARITY.total + ' fixtures</b> — engine drift, indices suppressed') +
        ' · ' + ids.length + ' lenses in the payload: ' + nCue + ' carry text cues and run here, ' +
        nModel + ' need a model' + (nNoCue ? ', ' + nNoCue + ' ' + (nNoCue === 1 ? 'has' : 'have') + ' no text cues' : '');
    }
    mountSamples();
    el('run').addEventListener('click', function () { render(el('in').value); });
    el('out').addEventListener('click', function (e) {
      var h = e.target.closest('.lhead'); if (!h) return;
      h.parentElement.classList.toggle('open');
    });
  }

  function fail(msg) {
    var out = el('out');
    out.innerHTML = '<div class="drift"><b>Payload failed to load.</b> This page carries no marker ' +
      'definitions of its own, by design, so there is no degraded mode: ' + esc(msg) + '</div>';
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!window.Instrument) { fail('engine.js is not loaded'); return; }
    if (window.TRADECRAFT_PAYLOAD) { P = window.TRADECRAFT_PAYLOAD; boot(); return; }
    fetch('/tech/instrument/instrument.json')
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { P = j; boot(); })
      .catch(function (e) { fail(e.message); });
  });
})();
