// Dependency-free checks of the actual page script and its user event handlers.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(){this.children=[];this.value='';this.disabled=false;this.textContent='';this.classList={toggle(){}};}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=items;if(items.length)this.value=String(items[0].value??'');}
  get options(){return this.children;}
  setAttribute(){} removeAttribute(){} remove(){} click(){}
}
function page() {
  const elements=new Map(),storage=new Map();
  const context={document:{getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement:()=>new Element(),createElementNS:()=>new Element(),body:new Element()},Option:class{constructor(text,value){this.textContent=text;this.value=value;}},localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},AbortController,console,setTimeout,Blob,URL,FormData};
  vm.createContext(context);
  const script=readFileSync('app/index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  context.document.getElementById('preference').value='minimize_changes';
  vm.runInContext(script,context);
  return {context,el:id=>context.document.getElementById(id),run:code=>vm.runInContext(code,context),storage};
}
const source={stage:{width:10,height:6},formations:[{name:'Opening',dancers:[{id:'A',x:2,y:2},{id:'B',x:5,y:2}]}]};
function load(p){p.context.input=structuredClone(source);p.run("loadRoutine(input,'Test routine')");}
function response(p,{valid=true,roster='normal'}={}) {
  const routine=structuredClone(source);routine.formations[0].dancers=roster==='wrong'?[{id:'Z',x:4,y:2}]:[{id:'B',x:4,y:2}];
  p.context.fetch=async()=>({ok:true,json:async()=>({routine,valid,errors:valid?[]:['Spacing violation'],changed_assignments:1,total_displacement:1})});
}
test('loaded routine populates selectors and malformed coordinates cannot replace it',async()=>{
  const p=page();load(p);assert.equal(p.el('missing').options.length,2);assert.equal(p.el('formation').options[0].textContent,'Opening');
  p.context.invalid=structuredClone(source);p.context.invalid.stage.width=-1;
  assert.throws(()=>p.run("loadRoutine(invalid,'Malformed PDF extraction')"),/positive finite/);
  assert.equal(p.el('missing').options.length,2);assert.equal(p.run('routine.stage.width'),10);
});
test('request sends selected absence, displays changes, and persists approval with proposal',async()=>{
  const p=page();load(p);response(p);const fetch=p.context.fetch;p.context.fetch=async(url,options)=>{assert.equal(url,'/api/repair');assert.equal(JSON.parse(options.body).missing,'A');return fetch();};
  await p.el('run').onclick();assert.equal(p.el('approve').disabled,false);assert.equal(p.el('changes').children.length,2);
  p.el('review-note').value='Ready for rehearsal';p.el('approve').onclick();
  const records=JSON.parse([...p.storage.values()][0]);assert.equal(records[0].decision,'approved');assert.equal(records[0].notes,'Ready for rehearsal');assert.ok(records[0].proposal);
  p.el('missing').value='B';p.el('missing').onchange();assert.equal(p.el('approve').disabled,true);assert.equal(p.el('changes').children.length,0);assert.match(p.el('review-status').textContent,/No review/);
});
test('invalid proposals can be rejected but cannot be approved',async()=>{
  const p=page();load(p);response(p,{valid:false});await p.el('run').onclick();assert.equal(p.el('approve').disabled,true);assert.equal(p.el('reject').disabled,false);
  p.el('reject').onclick();assert.equal(JSON.parse([...p.storage.values()][0])[0].decision,'rejected');
});
test('unexpected roster and server failures leave approval disabled and restore generate button',async()=>{
  const p=page();load(p);response(p,{roster:'wrong'});await p.el('run').onclick();assert.match(p.el('status').textContent,/unexpected dancer roster/);assert.equal(p.el('approve').disabled,true);
  p.context.fetch=async()=>({ok:false,json:async()=>({detail:['Dancers too close']})});await p.el('run').onclick();assert.match(p.el('status').textContent,/Dancers too close/);assert.equal(p.el('run').disabled,false);
});
test('late responses do not restore a proposal after the absence changes',async()=>{
  const p=page();load(p);response(p);const result=await p.context.fetch();let resolve;
  p.context.fetch=()=>new Promise(r=>resolve=r);const pending=p.el('run').onclick();
  p.el('missing').value='B';p.el('missing').onchange();resolve(result);await pending;
  assert.equal(p.el('approve').disabled,true);assert.match(p.el('summary').textContent,/No repair/);assert.match(p.el('status').textContent,/Selection changed/);
});
test('failed browser storage preserves an exportable decision',async()=>{
  const p=page();load(p);response(p);await p.el('run').onclick();p.context.localStorage.setItem=()=>{throw Error('quota');};p.el('approve').onclick();
  assert.match(p.el('review-status').textContent,/storage failed/);assert.equal(p.run('review.decision'),'approved');assert.equal(p.el('export-review').disabled,false);
});

test('manual center preference is sent to repair and saved with the review',async()=>{
  const p=page();load(p);response(p);const fetch=p.context.fetch;let payload;
  p.context.fetch=async(url,options)=>{payload=JSON.parse(options.body);return fetch();};
  p.el('preference').value='preserve_center';await p.el('run').onclick();
  assert.equal(payload.preference,'preserve_center');p.el('approve').onclick();
  assert.equal(JSON.parse([...p.storage.values()][0])[0].request.preference,'preserve_center');
});
test('AI instructions use the advanced repair route and unsupported output is rejected',async()=>{
  const p=page();load(p);response(p);const fetch=p.context.fetch,calls=[];
  p.el('ai-instruction').value='Prioritize symmetry';
  p.context.fetch=async(url,options)=>{
    calls.push([url,JSON.parse(options.body)]);
    const old=await fetch();const body=await old.json();
    return {ok:true,json:async()=>({...body,requirements:{primary_priority:'symmetry',secondary_priorities:[],constraints:{}}})};
  };
  await p.el('ai-run').onclick();
  assert.equal(calls.length,1);
  assert.equal(calls[0][0],'/api/repair-ai');
  assert.equal(calls[0][1].instruction,'Prioritize symmetry');
  assert.equal(p.el('approve').disabled,false);
  p.context.fetch=async()=>({ok:false,json:async()=>({detail:'Unsupported AI requirement'})});
  await p.el('ai-run').onclick();
  assert.match(p.el('ai-status').textContent,/unsupported/i);
  assert.equal(p.el('approve').disabled,true);
  assert.equal(p.el('ai-run').disabled,false);
});
test('empty instructions and AI service failures do not trigger repair',async()=>{
  const p=page();load(p);let calls=0;
  p.context.fetch=async()=>{calls++;return {ok:false,json:async()=>({detail:'AI service is currently unavailable.'})};};
  await p.el('ai-run').onclick();assert.equal(calls,0);assert.match(p.el('ai-status').textContent,/Enter an instruction/);
  p.el('ai-instruction').value='Minimize movement';await p.el('ai-run').onclick();assert.equal(calls,1);assert.match(p.el('ai-status').textContent,/unavailable/);assert.equal(p.el('run').disabled,false);
});
test('changing inputs while AI is pending prevents the follow-up repair',async()=>{
  const p=page();load(p);let resolve,calls=0;p.el('ai-instruction').value='Keep center';
  p.context.fetch=()=>{calls++;return new Promise(r=>resolve=r);};
  const pending=p.el('ai-run').onclick();p.el('preference').onchange();resolve({ok:true,json:async()=>({preference:'preserve_center'})});await pending;
  assert.equal(calls,1);assert.equal(p.el('approve').disabled,true);assert.equal(p.el('ai-run').disabled,false);
});
test('alternative layouts recalculate metrics, reset approval, and record the selected proposal',async()=>{
  const p=page();load(p);response(p);const data=await (await p.context.fetch()).json();
  const alternate=structuredClone(data.routine);alternate.formations[0].dancers[0].x=3;
  const wrong=structuredClone(alternate);wrong.formations[0].dancers[0].id='Z';
  data.alternatives=[{label:'Balanced',formation_index:0,routine:alternate},{label:'Bad roster',formation_index:0,routine:wrong}];
  p.context.fetch=async()=>({ok:true,json:async()=>data});await p.el('run').onclick();
  assert.equal(p.el('layout').options.length,2);assert.match(p.el('layout-note').textContent,/omitted/);
  p.el('approve').onclick();p.el('layout').value='1';p.el('layout').onchange();assert.equal(p.run('review'),null);assert.equal(p.el('review-note').value,'');assert.match(p.el('summary').textContent,/total displacement: 2/);
  p.el('approve').onclick();const records=JSON.parse([...p.storage.values()][0]);assert.equal(records[1].proposal.routine.formations[0].dancers[0].x,3);assert.match(records[1].proposal.candidate_label,/Balanced/);
});
test('roster mismatches are rejected without replacing the active routine',()=>{
  const p=page();load(p);
  p.context.bad=structuredClone(source);p.context.bad.formations.push({name:'Mismatch',dancers:[{id:'Z',x:1,y:1}]});assert.throws(()=>p.run("loadRoutine(bad,'Bad')"),/roster must match/);
  assert.equal(p.el('missing').options.length,2);assert.equal(p.run('routine.formations.length'),1);
});

// Real FastAPI integration: only the external Gemini preference call is stubbed.
const {spawnSync} = require('node:child_process');
async function apiFetch(url,options) {
  const body=options.body instanceof FormData
    ? {pdf_base64:Buffer.from(await options.body.get('file').arrayBuffer()).toString('base64')}
    : JSON.parse(options.body);
  const run=spawnSync('.venv/bin/python',['-B','tests/frontend/api_bridge.py'],{input:JSON.stringify({url,body}),encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  const output=JSON.parse(run.stdout);return Promise.resolve({ok:output.status<400,json:async()=>output.body});
}
test('actual backend alternatives integrate with a three-column fixture and selected-layout review',async()=>{
  const p=page();
  // Test data remains local to tests, independent of removed example controls.
  p.context.columns={stage:{width:12,height:8},formations:[{name:'F14',dancers:Array.from({length:12},(_,i)=>({id:String.fromCharCode(65+i),x:[4.5,6,7.5][Math.floor(i/4)],y:[1.9,3.2,4.5,5.8][i%4]}))}]};
  p.run("loadRoutine(columns,'Three-column PDF fixture')");
  p.context.fetch=apiFetch;await p.el('run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);assert.equal(p.el('layout').options.length,4);
  for(let i=0;i<p.el('layout').options.length;i++){
    p.el('layout').value=String(i);p.el('layout').onchange();assert.equal(p.run('result.routine.formations[0].dancers.length'),11);
    const actual=p.run('movementMetrics(result.routine).total_displacement');assert.equal(p.run('result.total_displacement'),actual);
  }
  p.el('reject').onclick();assert.equal(JSON.parse([...p.storage.values()][0])[0].proposal.routine.formations[0].dancers.length,11);
});
test('actual advanced AI endpoint reaches repair and exposes validation errors',async()=>{
  const p=page();load(p);p.context.fetch=apiFetch;p.el('ai-instruction').value='Keep the center';
  await p.el('ai-run').onclick();
  assert.equal(p.el('approve').disabled,false,p.el('status').textContent);
  assert.equal(p.run('requestContext.requirements.primary_priority'),'preserve_center');
  p.context.close=structuredClone(source);p.context.close.formations[0].dancers[1].x=2.1;
  p.run("loadRoutine(close,'Spacing violation')");await p.el('run').onclick();
  assert.match(p.el('status').textContent,/too close/);assert.equal(p.el('approve').disabled,true);
});
test('invalid geometry alternatives are omitted and changed stage responses cannot be approved',async()=>{
  const p=page();load(p);response(p);const data=await (await p.context.fetch()).json();
  const colliding={stage:{width:10,height:6},formations:[{name:'Opening',dancers:[{id:'B',x:4,y:2},{id:'C',x:4.1,y:2}]}]};
  p.context.three=structuredClone(source);p.context.three.formations[0].dancers.push({id:'C',x:8,y:2});p.run("loadRoutine(three,'Three')");
  data.routine.formations[0].dancers.push({id:'C',x:8,y:2});
  data.alternatives=[{label:'Collision',formation_index:0,routine:colliding}];
  p.context.fetch=async()=>({ok:true,json:async()=>data});await p.el('run').onclick();assert.equal(p.el('layout').options.length,1);assert.match(p.el('layout-note').textContent,/omitted/);
  data.routine.stage.width=12;await p.el('run').onclick();assert.match(p.el('status').textContent,/changed the stage/);assert.equal(p.el('approve').disabled,true);
});
test('a single-dancer routine accepts the empty repaired formation',async()=>{
  const p=page();p.context.single=structuredClone(source);p.context.single.formations[0].dancers.pop();p.run("loadRoutine(single,'Solo')");
  p.context.fetch=async()=>({ok:true,json:async()=>({routine:{stage:{width:10,height:6},formations:[{name:'Opening',dancers:[]}]},valid:true,errors:[]})});
  await p.el('run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);assert.equal(p.run('result.changed_assignments'),0);
});


function pdfDraftResponse() {
  const draft=structuredClone(source);
  draft.stage.units='ft';
  draft.formations.push({name:'Exit',dancers:[{id:'A',x:-2,y:2},{id:'B',x:12,y:2}]});
  return {routine:draft,pages:[{page:1,name:'Opening',importable:true,issues:[]},{page:2,name:'Exit',importable:false,issues:['Dancers outside stage']}],warnings:['Check extracted positions.']};
}
function pdfUpload(p,name='formations.pdf') {
  return p.el('pdf-upload').onchange({target:{files:[new File(['%PDF-test'],name,{type:'application/pdf'})],value:name}});
}
test('PDF preview preserves the current routine until confirmation and excludes offstage pages',async()=>{
  const p=page();load(p);const data=pdfDraftResponse();
  p.context.fetch=async(url,options)=>{assert.equal(url,'/api/import/sway-pdf');assert.ok(options.body instanceof FormData);assert.equal(options.headers,undefined);return {ok:true,json:async()=>data};};
  await pdfUpload(p);assert.equal(p.el('pdf-preview').hidden,false);assert.equal(p.run('routine.formations.length'),1);
  assert.match(p.el('pdf-selection').textContent,/1 of 2/);assert.match(p.el('pdf-selection').textContent,/Excluded: Exit/);
  p.el('pdf-formation').value='1';p.el('pdf-formation').onchange();assert.equal(p.el('pdf-include').disabled,true);assert.match(p.el('pdf-page-status').textContent,/outside stage/);assert.match(p.el('pdf-source').href,/#page=2/);
  p.el('pdf-confirm').onclick();assert.equal(p.el('pdf-preview').hidden,true);assert.equal(p.run('routine.stage.units'),'ft');assert.equal(p.run('routine.formations.length'),1);assert.match(p.el('routine-info').textContent,/formations.pdf/);
});
test('PDF selection, cancellation, and import errors leave the prior routine usable',async()=>{
  const p=page();load(p);p.context.fetch=async()=>({ok:true,json:async()=>pdfDraftResponse()});await pdfUpload(p);
  p.el('pdf-include').checked=false;p.el('pdf-include').onchange();assert.equal(p.el('pdf-confirm').disabled,true);p.el('pdf-confirm').onclick();assert.equal(p.run('routine.stage.units'),undefined);
  p.el('pdf-cancel').onclick();assert.equal(p.el('pdf-preview').hidden,true);assert.equal(p.el('run').disabled,false);
  p.context.fetch=async()=>({ok:false,json:async()=>({detail:'Scanned images are not supported.'})});await pdfUpload(p);assert.match(p.el('pdf-status').textContent,/Scanned images/);assert.equal(p.run('routine.formations.length'),1);assert.equal(p.el('ai-run').disabled,false);
});
test('PDF responses cannot overwrite a newer confirmed PDF',async()=>{
  const p=page();load(p);let resolve;p.context.fetch=()=>new Promise(r=>resolve=r);
  const pending=pdfUpload(p,'old.pdf');
  const next=pdfDraftResponse();next.routine.formations[0].name='F99';next.pages[0].name='F99';
  p.context.fetch=async()=>({ok:true,json:async()=>next});await pdfUpload(p,'new.pdf');p.el('pdf-confirm').onclick();
  resolve({ok:true,json:async()=>pdfDraftResponse()});await pending;
  assert.equal(p.el('pdf-preview').hidden,true);assert.equal(p.run('routine.formations[0].name'),'F99');assert.match(p.el('routine-info').textContent,/new.pdf/);
});
test('actual Sway PDF upload, confirmation, and repair work together',async()=>{
  const p=page();
  const fixture=spawnSync('.venv/bin/python',['-B','-c',"import runpy,base64; print(base64.b64encode(runpy.run_path('tests/test_pdf_import.py')['sway_pdf'](ghost=True,offstage=True)).decode())"],{encoding:'utf8'});
  assert.equal(fixture.status,0,fixture.stderr);
  p.context.fetch=apiFetch;
  const file=new File([Buffer.from(fixture.stdout.trim(),'base64')],'sway.pdf',{type:'application/pdf'});
  await p.el('pdf-upload').onchange({target:{files:[file],value:'sway.pdf'}});
  assert.equal(p.el('pdf-preview').hidden,false,p.el('pdf-status').textContent);assert.match(p.el('pdf-selection').textContent,/1 of 2/);
  p.el('pdf-confirm').onclick();assert.equal(p.run('routine.formations.length'),1);assert.equal(p.el('missing').options[0].textContent,'Alpha');
  await p.el('run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);assert.equal(p.run('result.routine.formations[0].dancers[0].id'),'Beta');
});


test('confirmed PDF names and exact nonconsecutive formation labels replace the demo selectors',async()=>{
  const p=page();
  const imported={stage:{width:38,height:28,units:'ft'},formations:['F1','F3','F7'].map(name=>({name,dancers:[{id:'Rhea',x:4,y:3},{id:'Samanvi',x:8,y:6}]}))};
  const draft={routine:imported,pages:imported.formations.map((f,i)=>({page:i+1,name:f.name,importable:true,issues:[]})),warnings:[]};
  p.context.fetch=async()=>({ok:true,json:async()=>draft});await pdfUpload(p,'kuthu.pdf');
  assert.equal(p.el('missing').disabled,true);assert.equal(p.el('formation').disabled,true);assert.equal(p.el('run').disabled,true);assert.match(p.el('absence-source').textContent,/Load selected formations/);
  // Omit F3; F7 must retain its original label rather than becoming F2.
  p.el('pdf-formation').value='1';p.el('pdf-formation').onchange();p.el('pdf-include').checked=false;p.el('pdf-include').onchange();
  p.el('pdf-confirm').onclick();
  assert.deepEqual(p.el('missing').options.map(o=>o.textContent),['Rhea','Samanvi']);
  assert.deepEqual(p.el('formation').options.map(o=>o.textContent),['F1','F7']);
  assert.equal(p.el('missing').disabled,false);assert.equal(p.el('formation').disabled,false);assert.equal(p.el('run').disabled,false);assert.match(p.el('absence-source').textContent,/kuthu.pdf/);
  p.el('missing').value='Samanvi';p.el('formation').value='1';p.el('formation').onchange();
  assert.equal(p.run('routine.formations[Number($("formation").value)].name'),'F7');
  p.context.fetch=async(url,options)=>{
    const body=JSON.parse(options.body);assert.equal(body.missing,'Samanvi');assert.deepEqual(body.routine.formations.map(f=>f.name),['F1','F7']);
    return {ok:true,json:async()=>({routine:{...body.routine,formations:body.routine.formations.map(f=>({...f,dancers:f.dancers.filter(d=>d.id!==body.missing)}))},valid:true,errors:[]})};
  };
  await p.el('run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);
});
