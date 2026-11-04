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
  setAttribute(){} remove(){} click(){}
}
function page() {
  const elements=new Map(),storage=new Map();
  const context={document:{getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement:()=>new Element(),createElementNS:()=>new Element(),body:new Element()},Option:class{constructor(text,value){this.textContent=text;this.value=value;}},localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},AbortController,console,setTimeout,Blob,URL};
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
test('imports populate selectors and malformed coordinates retain the loaded routine',async()=>{
  const p=page();load(p);assert.equal(p.el('missing').options.length,2);assert.equal(p.el('formation').options[0].textContent,'1. Opening');
  await p.el('upload').onchange({target:{files:[{name:'bad.json',text:async()=>JSON.stringify({...source,stage:{width:-1,height:6}})}],value:'bad.json'}});
  assert.match(p.el('status').textContent,/positive finite/);assert.equal(p.el('missing').options.length,2);
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
test('AI instruction is interpreted before repairing and unsupported output is rejected',async()=>{
  const p=page();load(p);response(p);const fetch=p.context.fetch,calls=[];
  p.el('ai-instruction').value='Keep center dancers';
  p.context.fetch=async(url,options)=>{
    calls.push([url,JSON.parse(options.body)]);
    return url==='/api/ai-preference'?{ok:true,json:async()=>({preference:'preserve_center'})}:fetch();
  };
  await p.el('ai-run').onclick();assert.equal(calls.length,2);assert.equal(calls[0][1].instruction,'Keep center dancers');assert.equal(calls[1][1].preference,'preserve_center');assert.equal(p.el('approve').disabled,false);
  p.context.fetch=async()=>({ok:true,json:async()=>({preference:'invented'})});await p.el('ai-run').onclick();
  assert.match(p.el('ai-status').textContent,/unsupported/);assert.equal(p.el('approve').disabled,true);assert.equal(p.el('ai-run').disabled,false);
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
test('roster mismatches are rejected on import and named choreography examples load',()=>{
  const p=page();load(p);
  p.context.bad=structuredClone(source);p.context.bad.formations.push({name:'Mismatch',dancers:[{id:'Z',x:1,y:1}]});assert.throws(()=>p.run("loadRoutine(bad,'Bad')"),/roster must match/);
  p.el('example').value='Ending Bhangra (12 performers)';p.el('example').onchange();assert.equal(p.el('missing').options.length,12);assert.equal(p.el('formation').options.length,4);assert.match(p.el('routine-info').textContent,/approximate reconstruction/);
});

// Real FastAPI integration: only the external Gemini preference call is stubbed.
const {spawnSync} = require('node:child_process');
function apiFetch(url,options) {
  const run=spawnSync('.venv/bin/python',['-B','tests/frontend/api_bridge.py'],{input:JSON.stringify({url,body:JSON.parse(options.body)}),encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  const output=JSON.parse(run.stdout);return Promise.resolve({ok:output.status<400,json:async()=>output.body});
}
test('actual backend alternatives integrate with named examples and selected-layout review',async()=>{
  const p=page();p.el('example').value='Ending Bhangra (12 performers)';p.el('example').onchange();
  p.context.fetch=apiFetch;await p.el('run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);assert.equal(p.el('layout').options.length,4);
  for(let i=0;i<p.el('layout').options.length;i++){
    p.el('layout').value=String(i);p.el('layout').onchange();assert.equal(p.run('result.routine.formations[0].dancers.length'),11);
    const actual=p.run('movementMetrics(result.routine).total_displacement');assert.equal(p.run('result.total_displacement'),actual);
  }
  p.el('reject').onclick();assert.equal(JSON.parse([...p.storage.values()][0])[0].proposal.routine.formations[0].dancers.length,11);
});
test('actual AI endpoint contract chains into actual repair and exposes backend validation errors',async()=>{
  const p=page();load(p);p.context.fetch=apiFetch;p.el('ai-instruction').value='Keep the center';
  await p.el('ai-run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);assert.equal(p.run('requestContext.preference'),'preserve_center');
  p.context.close=structuredClone(source);p.context.close.formations[0].dancers[1].x=2.1;
  p.run("loadRoutine(close,'Spacing violation')");await p.el('run').onclick();assert.match(p.el('status').textContent,/too close/);assert.equal(p.el('approve').disabled,true);
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
