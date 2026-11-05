// PDF-first UI acceptance tests, introduced in the red phase before implementation.
// Their original assertions are retained as regression requirements.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {page,descendants,draft,upload,confirm}=require('./helpers/page.cjs');
const html=fs.readFileSync('app/index.html','utf8');
const markup=html.slice(0,html.indexOf('<script>')).replace(/<style>[\s\S]*?<\/style>/g,'');

test('example routine picker is removed from the page',()=>{
  assert.doesNotMatch(markup,/\bid=["']example["']/,'Remove the example routine selector');
});
test('load-demo button is removed from the page',()=>{
  assert.doesNotMatch(markup,/\bid=["']demo["']/,'Remove the load-demo button');
});
test('JSON upload and format instructions are removed; PDF upload remains',()=>{
  assert.doesNotMatch(markup,/\bid=["']upload["']|JSON format|Advanced:\s*import routine JSON|Routine JSON file/i);
  assert.match(markup,/\bid=["']pdf-upload["']/);
  // The request was to remove JSON input/help, not downloadable review records.
  assert.match(markup,/\bid=["']export-review["']/);
});
test('a PDF-first session starts empty with repair disabled',()=>{
  const p=page();
  assert.equal(p.el('missing').options.length,0,'Do not silently preload demo dancers');
  assert.equal(p.el('formation').options.length,0,'Do not silently preload demo formations');
  assert.equal(p.el('run').disabled,true);assert.equal(p.el('ai-run').disabled,true);
});
test('the palette is controlled through shared theme variables',()=>{
  const css=html.match(/<style>([\s\S]*?)<\/style>/)[1];
  // Contract for the redesign; exact color values remain a design decision.
  for(const token of ['--page-bg','--surface','--text','--accent','--grid-line']){
    assert.match(css,new RegExp(`${token}\\s*:`),`Define ${token}`);
    assert.ok(css.includes(`var(${token})`),`Use ${token} rather than leaving it unused`);
  }
});

function assertGrid(svg,stage){
  const nodes=descendants(svg);
  const border=nodes.find(n=>n.tagName==='rect' && Number(n.getAttribute('width'))>0 && Number(n.getAttribute('height'))>0);
  assert.ok(border,'A stage boundary must remain visible');
  const w=Number(border.getAttribute('width')),h=Number(border.getAttribute('height'));
  const lines=nodes.filter(n=>n.tagName==='line');
  const near=(a,b)=>Math.abs(Number(a)-b)<.01;
  for(const x of stage.grid.x.slice(1,-1))assert.ok(lines.some(n=>near(n.getAttribute('x1'),x/stage.width*w)&&near(n.getAttribute('x2'),x/stage.width*w)&&near(n.getAttribute('y1'),0)&&near(n.getAttribute('y2'),h)),`Missing vertical PDF grid division at ${x} ft`);
  for(const y of stage.grid.y.slice(1,-1))assert.ok(lines.some(n=>near(n.getAttribute('y1'),y/stage.height*h)&&near(n.getAttribute('y2'),y/stage.height*h)&&near(n.getAttribute('x1'),0)&&near(n.getAttribute('x2'),w)),`Missing horizontal PDF grid division at ${y} ft`);
  const gridLines=lines.filter(n=>near(n.getAttribute('x1'),n.getAttribute('x2'))||near(n.getAttribute('y1'),n.getAttribute('y2')));
  const dancer=nodes.findIndex(n=>n.tagName==='circle');
  assert.ok(dancer>=0,'Dancer markers remain visible');
  for(const line of gridLines){
    assert.ok(nodes.indexOf(line)<dancer,'Grid is behind dancers');
    for(const key of ['x1','x2'])assert.ok(Number(line.getAttribute(key))>=-.01&&Number(line.getAttribute(key))<=w+.01);
    for(const key of ['y1','y2'])assert.ok(Number(line.getAttribute(key))>=-.01&&Number(line.getAttribute(key))<=h+.01);
  }
  return gridLines.map(n=>['x1','y1','x2','y2'].map(k=>Number(n.getAttribute(k))));
}
for(const rows of [4,3])test(`preview grid follows the PDF's ${rows} depth divisions, with offstage dancers preserved`,async()=>{
  const p=page(),data=draft({rows});
  // An exit marker must not stretch or renormalize the grid to the preview bounds.
  data.routine.formations[0].dancers[0].x=-2;data.pages[0].importable=false;data.pages[0].issues=['Dancer outside stage'];
  await upload(p,data);assertGrid(p.el('pdf-stage'),data.routine.stage);
  assert.equal(p.el('pdf-include').disabled,true);
});
test('original and repaired grids align without changing request coordinates',async()=>{
  const p=page(),data=draft();await confirm(p,data);
  let payload;
  p.context.fetch=async(url,options)=>{
    assert.equal(url,'/api/repair');payload=JSON.parse(options.body);
    return {ok:true,json:async()=>({routine:{stage:data.routine.stage,formations:data.routine.formations.map(f=>({...f,dancers:f.dancers.filter(d=>d.id!==payload.missing)}))},valid:true,errors:[]})};
  };
  await p.el('run').onclick();
  assert.deepEqual(payload.routine,data.routine,'Grid rendering must not alter dancer coordinates or source stage metadata');
  assert.deepEqual(assertGrid(p.el('original'),data.routine.stage),assertGrid(p.el('repaired'),data.routine.stage));
});


test('black background, white text, and purple marker styling share the theme',()=>{
  const css=html.match(/<style>([\s\S]*?)<\/style>/)[1];
  const color=name=>{const match=css.match(new RegExp(`${name}\\s*:\\s*(#[0-9a-f]{6})`,'i'));assert.ok(match,`Missing color ${name}`);return match[1].toLowerCase();};
  assert.equal(color('--page-bg'),'#000000');assert.equal(color('--text'),'#ffffff');
  const purple=color('--marker');const [r,g,b]=[1,3,5].map(i=>parseInt(purple.slice(i,i+2),16));
  assert.ok(r>g && b>r,'Formation markers should be purple');
  assert.match(css,/\.dancer-marker\s*\{[^}]*fill:\s*var\(--marker\)/);
  assert.match(css,/\.dancer-label[^}]*fill:\s*var\(--text\)/);
});

test('a formation-specific grid is retained in repaired view when the server omits display metadata',async()=>{
  const p=page(),data=draft();
  data.routine.formations[1].grid={x:data.routine.stage.grid.x,y:[0,28/3,56/3,28]};
  await confirm(p,data);p.el('formation').value='1';p.el('formation').onchange();
  p.context.fetch=async(_,options)=>{
    const body=JSON.parse(options.body);
    return {ok:true,json:async()=>({routine:{stage:data.routine.stage,formations:data.routine.formations.map(f=>({name:f.name,dancers:f.dancers.filter(d=>d.id!==body.missing)}))},valid:true,errors:[]})};
  };
  await p.el('run').onclick();
  const stage={...data.routine.stage,grid:data.routine.formations[1].grid};
  assert.deepEqual(assertGrid(p.el('original'),stage),assertGrid(p.el('repaired'),stage));
});
