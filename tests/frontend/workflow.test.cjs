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
