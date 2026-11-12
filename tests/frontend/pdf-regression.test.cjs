// GREEN safety net: PDF workflows that must survive removal of demo/JSON UI.
// These tests operate through PDF controls, never the example/demo/JSON inputs.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const {page,draft,upload,confirm}=require('./helpers/page.cjs');
function repairReply(data,missing,valid=true){
  return {routine:{stage:data.routine.stage,formations:data.routine.formations.map(f=>({...f,dancers:f.dancers.filter(p=>p.id!==missing).map(p=>({...p,x:p.x+.5}))}))},valid,errors:valid?[]:['Spacing violation']};
}
test('PDF confirmation replaces names/labels and preserves order and coordinates',async()=>{
  const p=page(),data=draft();await upload(p,data);
  assert.equal(p.el('pdf-preview').hidden,false);assert.equal(p.el('run').disabled,true);
  p.el('pdf-confirm').onclick();
  assert.deepEqual(p.el('missing').options.map(o=>o.value),['Rhea','Samanvi','Arun']);
  assert.deepEqual(p.el('formation').options.map(o=>o.textContent),['F1','F7']);
  assert.equal(p.el('run').disabled,false);
  let sent;
  p.context.fetch=async(url,options)=>{sent=JSON.parse(options.body);return {ok:true,json:async()=>repairReply(data,sent.missing)};};
  p.el('missing').value='Samanvi';await p.el('run').onclick();
  assert.deepEqual(sent,{routine:data.routine,missing:'Samanvi',preference:'minimize_changes'});
  assert.equal(p.el('approve').disabled,false);
});
test('failed/cancelled PDF replacement retains the last confirmed routine',async()=>{
  const p=page();await confirm(p);
  await upload(p,draft({names:['New A','New B','New C']}));p.el('pdf-cancel').onclick();
  assert.equal(p.el('missing').options[0].value,'Rhea');
  p.context.fetch=async()=>({ok:false,json:async()=>({detail:'Unsupported PDF layout'})});
  await p.el('pdf-upload').onchange({target:{files:[new File(['%PDF-bad'],'bad.pdf',{type:'application/pdf'})],value:'bad.pdf'}});
  assert.match(p.el('pdf-status').textContent,/Unsupported PDF layout/);
  assert.equal(p.el('missing').options[0].value,'Rhea');assert.equal(p.el('run').disabled,false);
});
test('advanced AI route and service-error recovery survive the restyle',async()=>{
  const p=page(),data=draft();await confirm(p,data);const requests=[];
  p.el('ai-instruction').value='Prioritize symmetry';
  p.context.fetch=async(url,options)=>{
    const body=JSON.parse(options.body);requests.push({url,body});
    return {ok:true,json:async()=>({...repairReply(data,body.missing),requirements:{primary_priority:'symmetry',secondary_priorities:[],constraints:{}}})};
  };
  await p.el('ai-run').onclick();
  assert.deepEqual(requests.map(r=>r.url),['/api/repair-ai']);
  assert.equal(requests[0].body.instruction,'Prioritize symmetry');
  assert.equal(p.el('approve').disabled,false);
  p.context.fetch=async()=>({ok:false,json:async()=>({detail:'AI service is currently unavailable.'})});
  await p.el('ai-run').onclick();
  assert.match(p.el('ai-status').textContent,/unavailable/);
  assert.equal(p.el('run').disabled,false);
  assert.equal(p.el('approve').disabled,true);
});
test('invalid geometry cannot be approved and invalid rosters are rejected',async()=>{
  const p=page(),data=draft();await confirm(p,data);
  p.context.fetch=async()=>({ok:true,json:async()=>repairReply(data,'Rhea',false)});
  await p.el('run').onclick();assert.equal(p.el('approve').disabled,true);assert.equal(p.el('reject').disabled,false);
  p.el('reject').onclick();assert.equal(JSON.parse([...p.storage.values()][0])[0].decision,'rejected');
  const bad=repairReply(data,'Rhea');bad.routine.formations[0].dancers[0].id='Invented';
  p.context.fetch=async()=>({ok:true,json:async()=>bad});await p.el('run').onclick();
  assert.equal(p.el('approve').disabled,true);assert.match(p.el('status').textContent,/roster/);
});
test('layout switching clears the current approval and records the selected alternative',async()=>{
  const p=page(),data=draft();await confirm(p,data);
  const result=repairReply(data,'Rhea');const alternative=structuredClone(result.routine);
  alternative.formations[1].dancers[0].x+=1;
  result.alternatives=[{label:'Balanced',formation_index:1,routine:alternative}];
  p.context.fetch=async()=>({ok:true,json:async()=>result});await p.el('run').onclick();
  p.el('review-note').value='Primary';p.el('approve').onclick();
  p.el('layout').value='1';p.el('layout').onchange();assert.equal(p.el('review-note').value,'');
  assert.match(p.el('review-status').textContent,/No review/);p.el('approve').onclick();
  const records=JSON.parse([...p.storage.values()][0]);assert.equal(records.length,2);
  assert.deepEqual(records[1].proposal.routine,alternative);
});

test('review export keeps source coordinates, selected proposal, notes, and decision', async () => {
  const p = page();
  const data = draft();

  await confirm(p, data);

  p.context.fetch = async () => ({
    ok: true,
    json: async () => repairReply(data, 'Rhea')
  });

  await p.el('run').onclick();

  // Case 1: Approve the repair
  p.el('review-note').value = 'Ready';
  p.el('approve').onclick();
  p.el('export-review').onclick();

  let exported = JSON.parse(
    await [...p.blobs.values()].at(-1).text()
  );

  assert.deepEqual(exported.original, data.routine);
  assert.equal(exported.review.decision, 'approved');
  assert.equal(exported.review.notes, 'Ready');
  assert.equal(exported.missing, 'Rhea');

  assert.ok(
    exported.proposal.routine.formations.every(
      f => f.dancers.every(d => d.id !== 'Rhea')
    )
  );

  // Case 2: Reject the same repair after further review
  p.el('review-note').value = 'Needs more adjustments';
  p.el('reject').onclick();
  p.el('export-review').onclick();

  exported = JSON.parse(
    await [...p.blobs.values()].at(-1).text()
  );

  assert.equal(exported.review.decision, 'rejected');
  assert.equal(
    exported.review.notes,
    'Needs more adjustments'
  );

  // Original data must remain unchanged
  assert.deepEqual(exported.original, data.routine);

  // Both review decisions should be recorded
  const records = JSON.parse(
    [...p.storage.values()][0]
  );

  assert.equal(records.length, 2);
  assert.equal(records[0].decision, 'approved');
  assert.equal(records[1].decision, 'rejected');
});

test('a late repair cannot overwrite the next confirmed PDF',async()=>{
  const p=page(),data=draft();await confirm(p,data);let resolve;
  p.context.fetch=()=>new Promise(r=>resolve=r);const pending=p.el('run').onclick();
  const next=draft({names:['Next A','Next B','Next C']});await confirm(p,next);
  resolve({ok:true,json:async()=>repairReply(data,'Rhea')});await pending;
  assert.equal(p.el('missing').options[0].value,'Next A');assert.equal(p.el('approve').disabled,true);
});
test('real FastAPI multipart import and repair contracts remain compatible',async()=>{
  const fixture=spawnSync('.venv/bin/python',['-B','-c',"import runpy,base64; print(base64.b64encode(runpy.run_path('tests/test_pdf_import.py')['sway_pdf'](ghost=True,offstage=True)).decode())"],{encoding:'utf8'});
  assert.equal(fixture.status,0,fixture.stderr);const p=page();
  p.context.fetch=async(url,options)=>{
    const body=options.body instanceof FormData?{pdf_base64:Buffer.from(await options.body.get('file').arrayBuffer()).toString('base64')}:JSON.parse(options.body);
    const run=spawnSync('.venv/bin/python',['-B','tests/frontend/api_bridge.py'],{input:JSON.stringify({url,body}),encoding:'utf8'});
    assert.equal(run.status,0,run.stderr);const reply=JSON.parse(run.stdout);
    return {ok:reply.status<400,json:async()=>reply.body};
  };
  await p.el('pdf-upload').onchange({target:{files:[new File([Buffer.from(fixture.stdout.trim(),'base64')],'actual.pdf',{type:'application/pdf'})],value:'actual.pdf'}});
  assert.match(p.el('pdf-selection').textContent,/1 of 2/);p.el('pdf-confirm').onclick();
  assert.deepEqual(p.el('formation').options.map(o=>o.textContent),['F1']);
  await p.el('run').onclick();assert.equal(p.el('approve').disabled,false,p.el('status').textContent);
});
