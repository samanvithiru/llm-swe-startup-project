// Test adapter for the actual page script. Missing HTML IDs return null, like a
// browser; removed controls cannot be silently invented by this harness.
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag='div') {
    this.tagName=tag.toLowerCase();this.children=[];this.attributes={};this.value='';
    this.textContent='';this.disabled=false;this.hidden=false;this.checked=false;
    this.classes=new Set();
    this.classList={toggle:(name,on)=>{if(on)this.classes.add(name);else this.classes.delete(name);},contains:name=>this.classes.has(name)};
  }
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=[...items];if(this.tagName==='select')this.value=String(items[0]?.value??'');}
  setAttribute(key,value){this.attributes[key]=String(value);}
  getAttribute(key){return this.attributes[key]??null;}
  removeAttribute(key){delete this.attributes[key];}
  get options(){return this.children;}
  click(){this.onclick?.();} remove(){}
}
function page() {
  const html=fs.readFileSync('app/index.html','utf8');
  const markup=html.slice(0,html.indexOf('<script>'));
  const elements=new Map();
  for(const match of markup.matchAll(/<([\w-]+)\b([^>]*\bid=["']([^"']+)["'][^>]*)>/g)){
    const node=new Element(match[1]);
    for(const attr of match[2].matchAll(/([\w-]+)=["']([^"']*)["']/g))node.setAttribute(attr[1],attr[2]);
    node.disabled=/\sdisabled(?:\s|$)/.test(match[2]);node.hidden=/\shidden(?:\s|$)/.test(match[2]);
    elements.set(match[3],node);
  }
  for(const match of markup.matchAll(/<select\b[^>]*id=["']([^"']+)["'][^>]*>([\s\S]*?)<\/select>/g)){
    const node=elements.get(match[1]);
    for(const option of match[2].matchAll(/<option\b[^>]*value=["']([^"']*)["'][^>]*>([^<]*)<\/option>/g)){
      const item=new Element('option');item.value=option[1];item.textContent=option[2];node.append(item);
    }
    node.value=node.children[0]?.value??'';
  }
  const storage=new Map(),blobs=new Map();let serial=0;
  const context={document:{getElementById:id=>elements.get(id)??null,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag),body:new Element('body')},
    Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=String(value);}},
    localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},
    URL:{createObjectURL:blob=>{const url=`blob:test-${++serial}`;blobs.set(url,blob);return url;},revokeObjectURL:()=>{}},
    AbortController,Blob,FormData,setTimeout:()=>0,console};
  vm.createContext(context);
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context,{filename:'app/index.inline.js'});
  return {html,markup,context,elements,storage,blobs,el:id=>elements.get(id)};
}
function descendants(node){return (node?.children??[]).flatMap(child=>[child,...descendants(child)]);}
function draft({rows=4,names=['Rhea','Samanvi','Arun']}={}){
  const routine={stage:{width:38,height:28,units:'ft',grid:{x:Array.from({length:9},(_,i)=>i*38/8),y:Array.from({length:rows+1},(_,i)=>i*28/rows)}},
    formations:['F1','F7'].map((name,i)=>({name,source_page:i+1,dancers:names.map((id,j)=>({id,x:7+j*9,y:7+i*3+j}))}))};
  return {routine,pages:routine.formations.map((f,i)=>({page:i+1,name:f.name,dancer_count:names.length,importable:true,issues:[]})),warnings:[]};
}
async function upload(p,data=draft()){
  p.context.fetch=async(url,options)=>{
    if(url!=='/api/import/sway-pdf')throw Error(`Unexpected request: ${url}`);
    if(!(options.body instanceof FormData))throw Error('PDF must use multipart upload');
    return {ok:true,json:async()=>structuredClone(data)};
  };
  await p.el('pdf-upload').onchange({target:{files:[new File(['%PDF-fixture'],'routine.pdf',{type:'application/pdf'})],value:'routine.pdf'}});
}
async function confirm(p,data=draft()){await upload(p,data);p.el('pdf-confirm').onclick();}
module.exports={page,descendants,draft,upload,confirm};
