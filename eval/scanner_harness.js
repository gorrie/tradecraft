// Drive the SHIPPED capture scanner outside a browser.
//
//   node scanner_harness.js <capture-cats.js> <scanner.js>  < texts.json  > results.json
//
// stdin is a JSON array of strings; stdout is a JSON array of CaptureScanner.measure()
// results with the rendered HTML dropped. The vocabulary (capture-cats.js) and the two
// passes (scanner.js) are the site's own bytes -- this file copies no wordlist and no
// formula, which is the whole reason it exists: a Python re-implementation would be a
// third copy of the scanner, and the collector's copy already drifted once.
'use strict';
const fs = require('fs');
const path = require('path');

global.window = {};
global.document = { addEventListener() {}, getElementById() { return null; } };
require(path.resolve(process.argv[2]));   // sets window.CAPTURE_CATS
require(path.resolve(process.argv[3]));   // sets window.CaptureScanner
if (!global.window.CaptureScanner) {
  process.stderr.write('scanner.js did not export window.CaptureScanner\n');
  process.exit(2);
}
const texts = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = texts.map(function (t) {
  const m = global.window.CaptureScanner.measure(String(t));
  delete m.html;
  return m;
});
process.stdout.write(JSON.stringify(out));
