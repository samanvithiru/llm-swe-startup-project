// Dependency-free checks of the page structure and the UI feedback added on top of the workflow.
// workflow.test.cjs covers the repair workflow itself. Run from the repository root.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');

const html = readFileSync('app/index.html', 'utf8');
const [, css] = html.match(/<style>([\s\S]*?)<\/style>/);
const [, script] = html.match(/<script>([\s\S]*?)<\/script>/);
const markup = html.slice(0, html.indexOf('<script>')).replace(/<style>[\s\S]*?<\/style>/, '');

// Unlike the workflow adapter, this one records attributes, classes, and SVG children.
class Element {
  constructor() {
    this.children = []; this.attributes = {}; this.classes = new Set();
    this.value = ''; this.disabled = false; this.hidden = false; this.textContent = '';
    const classes = this.classes;
    this.classList = {toggle(name, on) { if (on) classes.add(name); else classes.delete(name); }};
  }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; if (items.length) this.value = String(items[0].value ?? ''); }
  get options() { return this.children; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  remove() {} click() {}
}
function page() {
  const elements = new Map(), storage = new Map();
  const context = {
    document: {
      getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
      createElement: () => new Element(), createElementNS: () => new Element(), body: new Element(),
    },
    Option: class { constructor(text, value) { this.textContent = text; this.value = value; } },
    localStorage: {getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value)},
    AbortController, console, setTimeout, Blob, URL, FormData,
  };
  vm.createContext(context);
  context.document.getElementById('preference').value = 'minimize_changes';
  vm.runInContext(script, context);
  return {context, el: id => context.document.getElementById(id), run: code => vm.runInContext(code, context), storage};
}

const source = {stage: {width: 10, height: 6}, formations: [{name: 'Opening', dancers: [{id: 'A', x: 2, y: 2}, {id: 'B', x: 5, y: 2}]}]};
function load(p, value = source) { p.context.input = structuredClone(value); p.run("loadRoutine(input,'Test routine')"); }
function repairResponse({valid = true, errors = [], note} = {}) {
  const routine = structuredClone(source);
  routine.formations[0].dancers = [{id: 'B', x: 4, y: 2}];
  return {routine, valid, errors, note, changed_assignments: 1, total_displacement: 1};
}
function respondWith(p, body, ok = true) { p.context.fetch = async () => ({ok, json: async () => body}); }
const stepId = ['step-load', 'step-absence', 'step-compare', 'step-review'];
const currentStep = p => stepId.filter(id => p.el(id).attributes['aria-current'] === 'step');
function nodes(root) { return root.children.flatMap(child => [child, ...nodes(child)]); }
function byClass(svg, name) { return nodes(svg).filter(node => (node.attributes.class || '').split(' ').includes(name)); }
function pdfDraft() {
  const routine = {stage: {width: 10, height: 6, units: 'ft'}, formations: [{name: 'Exit', dancers: [{id: 'Alpha', x: 12, y: 2}]}]};
  return {routine, pages: [{page: 1, name: 'Exit', importable: false, issues: ['Dancers outside stage']}], warnings: []};
}
const uploadPDF = p => p.el('pdf-upload').onchange({target: {files: [new File(['%PDF'], 'f.pdf')], value: 'f.pdf'}});

// --- Page structure ---
test('every element the script looks up exists exactly once in the markup', () => {
  const used = new Set([...script.matchAll(/\$\('([\w-]+)'\)/g)].map(m => m[1]));
  for (const [, id] of script.matchAll(/'((?:step|ai|run)[\w-]*)'/g)) if (/^(step-|run$|ai-run$)/.test(id)) used.add(id);
  const declared = [...markup.matchAll(/\sid="([\w-]+)"/g)].map(m => m[1]);
  assert.deepEqual(declared.filter((id, i) => declared.indexOf(id) !== i), [], 'duplicate ids');
  assert.deepEqual([...used].filter(id => !declared.includes(id)), [], 'ids missing from the markup');
});
test('every form control has an associated label', () => {
  const labels = [...markup.matchAll(/<label\b[^>]*>[\s\S]*?<\/label>/g)].map(m => m[0]);
  const controls = [...markup.matchAll(/<(?:input|select|textarea)\b[^>]*\sid="([\w-]+)"/g)].map(m => m[1]);
  assert.ok(controls.length >= 10);
  for (const id of controls) assert.ok(labels.some(l => l.includes(`id="${id}"`) || l.includes(`for="${id}"`)), `${id} has no label`);
});
test('headings form an outline and each workflow section is named and numbered', () => {
  const levels = [...markup.matchAll(/<h([1-6])\b/g)].map(m => Number(m[1]));
  assert.equal(levels.filter(level => level === 1).length, 1);
  levels.forEach((level, i) => { if (i) assert.ok(level <= levels[i - 1] + 1, `heading jumps to h${level}`); });
  for (const section of markup.match(/<section\b[^>]*>/g)) assert.match(section, /aria-labelledby=/);
  const numbered = [...markup.matchAll(/<h2[^>]*>(\d)\./g)].map(m => m[1]);
  assert.deepEqual(numbered, ['1', '2', '3', '4']);
});
test('progress links point at sections that exist', () => {
  const targets = [...markup.matchAll(/href="#([\w-]+)"/g)].map(m => m[1]);
  assert.equal(targets.length, stepId.length);
  for (const id of targets) assert.match(markup, new RegExp(`<section[^>]*id="${id}"`));
});
test('the page stays a single self-contained file served by the existing route', () => {
  assert.doesNotMatch(html, /<script\s+src|rel="stylesheet"|@import/);
  assert.doesNotMatch(html, /https?:\/\/(?!www\.w3\.org\/2000\/svg)/);
  assert.doesNotMatch(markup, /\sstyle="/);
});
test('the page calls only routes the backend defines', () => {
  const routes = [...readFileSync('app/server.py', 'utf8').matchAll(/@app\.post\("([^"]+)"\)/g)].map(m => m[1]);
  const called = [...new Set([...script.matchAll(/'(\/api\/[^']+)'/g)].map(m => m[1]))];
  assert.equal(called.length, 3);
  for (const url of called) assert.ok(routes.includes(url), `${url} is not a backend route`);
});
test('colors come from CSS tokens rather than the script', () => {
  assert.deepEqual(script.match(/#[0-9a-fA-F]{6}\b/g), null);
  const defined = new Set([...css.matchAll(/(--[\w-]+):/g)].map(m => m[1]));
  for (const [, name] of css.matchAll(/var\((--[\w-]+)\)/g)) assert.ok(defined.has(name), `${name} is undefined`);
});

// --- Progress and feedback ---
test('progress follows the workflow from absence to compare to review', async () => {
  const p = page(); load(p);
  assert.deepEqual(currentStep(p), ['step-absence']); assert.ok(p.el('step-load').classes.has('done'));
  respondWith(p, repairResponse()); await p.el('run').onclick();
  assert.deepEqual(currentStep(p), ['step-compare']);
  p.el('approve').onclick();
  assert.deepEqual(currentStep(p), ['step-review']); assert.ok(p.el('step-compare').classes.has('done'));
  p.el('missing').value = 'B'; p.el('missing').onchange();
  assert.deepEqual(currentStep(p), ['step-absence']); assert.ok(!p.el('step-compare').classes.has('done'));
});
test('progress returns to Load while a PDF preview is awaiting confirmation', async () => {
  const p = page(); load(p); respondWith(p, pdfDraft()); await uploadPDF(p);
  assert.deepEqual(currentStep(p), ['step-load']);
  p.el('pdf-cancel').onclick(); assert.deepEqual(currentStep(p), ['step-absence']);
});
test('validity badge reports no proposal, passed, and failed states', async () => {
  const p = page(); load(p); const badge = p.el('validity');
  assert.match(badge.textContent, /No proposal/); assert.equal(badge.classes.size, 0);
  respondWith(p, repairResponse()); await p.el('run').onclick();
  assert.match(badge.textContent, /passed/); assert.ok(badge.classes.has('ok'));
  respondWith(p, repairResponse({valid: false, errors: ['Spacing violation']})); await p.el('run').onclick();
  assert.match(badge.textContent, /Failed/); assert.ok(badge.classes.has('bad')); assert.ok(!badge.classes.has('ok'));
  p.el('missing').value = 'B'; p.el('missing').onchange();
  assert.match(badge.textContent, /No proposal/); assert.equal(badge.classes.size, 0);
});
test('validation errors and backend notes appear beside the comparison', async () => {
  const p = page(); load(p); const detail = p.el('result-detail');
  respondWith(p, repairResponse({note: 'Captain review required.'})); await p.el('run').onclick();
  assert.equal(detail.hidden, false); assert.equal(detail.textContent, 'Captain review required.'); assert.ok(!detail.classes.has('error'));
  respondWith(p, repairResponse({valid: false, errors: ['Spacing violation']})); await p.el('run').onclick();
  assert.equal(detail.textContent, 'Spacing violation'); assert.ok(detail.classes.has('error'));
  respondWith(p, repairResponse()); await p.el('run').onclick();
  assert.equal(detail.hidden, true);
});
test('a successful repair status has no blank lines and does not repeat the backend note', async () => {
  const p = page(); load(p); respondWith(p, repairResponse({note: 'Captain review required.'})); await p.el('run').onclick();
  assert.equal(p.el('status').textContent, 'Geometry checks passed.');
});
test('the empty-table hint disappears once a proposal exists', async () => {
  const p = page(); load(p); assert.equal(p.el('changes-empty').hidden, false);
  respondWith(p, repairResponse()); await p.el('run').onclick();
  assert.equal(p.el('changes-empty').hidden, true);
  p.el('missing').value = 'B'; p.el('missing').onchange();
  assert.equal(p.el('changes-empty').hidden, false);
});
test('only the clicked button is busy, and busy clears on completion and cancellation', async () => {
  const p = page(); load(p); let resolve;
  p.context.fetch = () => new Promise(r => resolve = r);
  const pending = p.el('run').onclick();
  assert.equal(p.el('run').attributes['aria-busy'], 'true'); assert.equal(p.el('ai-run').attributes['aria-busy'], 'false');
  resolve({ok: true, json: async () => repairResponse()}); await pending;
  assert.equal(p.el('run').attributes['aria-busy'], 'false');
  p.el('run').onclick(); p.el('missing').value = 'B'; p.el('missing').onchange();
  assert.equal(p.el('run').attributes['aria-busy'], 'false');
});
test('the page scrolls to the comparison after success but not after failure', async () => {
  const p = page(); load(p); let scrolls = 0; p.el('compare-panel').scrollIntoView = () => scrolls++;
  respondWith(p, {detail: 'Dancers too close'}, false); await p.el('run').onclick(); assert.equal(scrolls, 0);
  respondWith(p, repairResponse()); await p.el('run').onclick(); assert.equal(scrolls, 1);
});
test('a PDF preview scrolls into view and its instructions point down the page to it', async () => {
  const p = page(); load(p); let scrolls = 0; p.el('pdf-preview').scrollIntoView = () => scrolls++;
  respondWith(p, {detail: 'Scanned images are not supported.'}, false); await uploadPDF(p); assert.equal(scrolls, 0);
  respondWith(p, pdfDraft()); await uploadPDF(p); assert.equal(scrolls, 1);
  assert.ok(markup.indexOf('id="absence-panel"') < markup.indexOf('id="pdf-preview"'), 'preview sits below step 2');
  for (const id of ['absence-source', 'status']) assert.match(p.el(id).textContent, /below/);
});
test('PDF and AI failures are flagged as errors and clear on the next attempt', async () => {
  const p = page(); load(p);
  respondWith(p, {detail: 'Scanned images are not supported.'}, false); await uploadPDF(p);
  assert.ok(p.el('pdf-status').classes.has('error'));
  respondWith(p, pdfDraft()); await uploadPDF(p);
  assert.ok(!p.el('pdf-status').classes.has('error')); p.el('pdf-cancel').onclick();
  await p.el('ai-run').onclick(); assert.ok(p.el('ai-status').classes.has('error'), 'empty instruction');
  p.el('ai-instruction').value = 'Keep center'; p.el('ai-instruction').oninput();
  assert.ok(!p.el('ai-status').classes.has('error'));
  respondWith(p, {detail: 'AI service is currently unavailable.'}, false); await p.el('ai-run').onclick();
  assert.ok(p.el('ai-status').classes.has('error'));
});
test('the example picker keeps showing the example that was loaded', () => {
  const p = page(); p.el('example').value = 'Kuthu (14 performers)'; p.el('example').onchange();
  assert.equal(p.el('example').value, 'Kuthu (14 performers)');
  p.el('demo').onclick(); assert.equal(p.el('example').value, '');
});

// --- Stage diagrams ---
test('stage markers put short IDs inside and full names above, so similar names stay distinct', () => {
  const p = page();
  load(p, {stage: {width: 10, height: 6}, formations: [{name: 'Opening', dancers: [
    {id: 'Om', x: 1, y: 2}, {id: 'Haarika', x: 3, y: 2}, {id: 'Haasini', x: 5, y: 2}, {id: 'Bartholomew Jones', x: 7, y: 2},
  ]}]});
  const svg = p.el('original');
  assert.deepEqual(byClass(svg, 'dancer-id').map(n => n.textContent), ['Om']);
  assert.deepEqual(byClass(svg, 'dancer-name').map(n => n.textContent), ['Haarika', 'Haasini', 'Bartholomew…']);
  assert.match(nodes(svg).filter(n => /^Bartholomew Jones:/.test(n.textContent))[0].textContent, /\(7, 2\)/);
});
test('marker states are carried by classes for unavailable and moved dancers', async () => {
  const p = page(); load(p); assert.equal(byClass(p.el('original'), 'unavailable').length, 1);
  respondWith(p, repairResponse()); await p.el('run').onclick();
  const repaired = p.el('repaired');
  assert.equal(byClass(repaired, 'moved').length, 1); assert.equal(byClass(repaired, 'travel').length, 1); assert.equal(byClass(repaired, 'previous').length, 1);
});
test('the empty proposal stage says so, and the placeholder goes away with a proposal', async () => {
  const p = page(); load(p); assert.equal(byClass(p.el('repaired'), 'stage-empty').length, 1);
  respondWith(p, repairResponse()); await p.el('run').onclick();
  assert.equal(byClass(p.el('repaired'), 'stage-empty').length, 0);
});
test('offstage PDF dancers are labelled offstage, not unavailable', async () => {
  const p = page(); load(p); respondWith(p, pdfDraft()); await uploadPDF(p);
  const svg = p.el('pdf-stage');
  assert.equal(byClass(svg, 'offstage').length, 1);
  assert.equal(nodes(svg).filter(n => /unavailable/.test(n.textContent)).length, 0);
  assert.equal(nodes(svg).filter(n => /— offstage/.test(n.textContent)).length, 1);
});
test('diagrams describe their contents to screen readers', async () => {
  const p = page(); load(p);
  assert.equal(p.el('original').attributes['aria-label'], 'Original formation Opening: 2 dancers, A unavailable.');
  assert.match(p.el('repaired').attributes['aria-label'], /no repair generated/);
  respondWith(p, repairResponse()); await p.el('run').onclick();
  assert.equal(p.el('repaired').attributes['aria-label'], 'Proposed formation Opening: 1 dancer, 1 moved.');
  respondWith(p, pdfDraft()); await uploadPDF(p);
  assert.match(p.el('pdf-stage').attributes['aria-label'], /Exit: 1 dancer;/);
});

// --- Review history ---
test('history shows readable dates and tolerates a malformed saved date', async () => {
  const p = page(); load(p); respondWith(p, repairResponse()); await p.el('run').onclick();
  p.el('approve').onclick();
  const shown = p.el('history').children[0].textContent;
  assert.doesNotMatch(shown, /\d{4}-\d{2}-\d{2}T/); assert.match(shown, /approved · unavailable dancer A/);
  assert.equal(p.run("formatWhen('not a date')"), 'not a date');
});
