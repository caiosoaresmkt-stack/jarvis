// Extrai strings visíveis ao usuário do frontend (AST via @babel/parser).
// uso: node extract_strings.mjs <frontend/src> <saida.json>
import {createRequire} from 'module'; import fs from 'fs'; import path from 'path';
const root=path.resolve(process.argv[2]); const require=createRequire(path.join(root,'../package.json'));
const parser=require('@babel/parser'); const traverse=require('@babel/traverse').default;
const out=new Map();
const ATTR=new Set(['placeholder','title','aria-label','label','description','alt','tooltip','helperText','emptyText','subtitle','heading','text','message']);
const KEYS=new Set(['label','title','description','placeholder','message','subtitle','heading','text','hint','tagline','summary','detail','emptyText','error','helper']);
function add(t,f){t=t.replace(/\s+/g,' ').trim(); if(!/[A-Za-z]{2}/.test(t))return;
  if(/^(https?:|\/|\.|#)/.test(t))return; if(!/\s/.test(t)&&/^[a-z0-9_.:\-\/\[\]@]+$/.test(t)&&t.length>2&&!/^(done|cancel|save|close|delete|edit|search|loading|error|settings|chat|agents|logs|dashboard|memory|tools|model|models|name|email|status|actions|type|enabled|disabled|online|offline|connect|disconnect|refresh|retry|submit|back|next|none|all|copy|copied|running|stopped|paused|idle|active|pending|failed|success|general|advanced|appearance|theme|light|dark|system|cloud|local|upload|download|reset|apply|confirm|remove|add|create|update|run|stop|start|pause|resume|details|history|cost|energy|savings|data|sources|skills|channels|logs|traces|agent|tool|input|output|result|results|source|summary|overview)$/.test(t))return;
  if(!out.has(t))out.set(t,path.relative(root,f));}
function collect(e,f){ if(!e)return;
 switch(e.type){
  case 'StringLiteral': add(e.value,f);break;
  case 'TemplateLiteral': add(e.quasis.map(q=>q.value.cooked).join('{}'),f);break;
  case 'ConditionalExpression': collect(e.consequent,f);collect(e.alternate,f);break;
  case 'LogicalExpression': collect(e.left,f);collect(e.right,f);break;
  case 'ParenthesizedExpression': case 'TSAsExpression': collect(e.expression,f);break;}}
function walk(d){for(const x of fs.readdirSync(d)){const p=path.join(d,x);
  if(fs.statSync(p).isDirectory())walk(p); else if(/\.tsx?$/.test(x)&&!/\.test\./.test(x))proc(p);}}
function proc(f){const code=fs.readFileSync(f,'utf8');
 const ast=parser.parse(code,{sourceType:'module',plugins:['typescript','jsx']});
 traverse(ast,{
  JSXText(p){add(p.node.value,f)},
  JSXAttribute(p){const n=p.node.name.name; if(!ATTR.has(n))return; const v=p.node.value; if(!v)return;
    if(v.type==='StringLiteral')add(v.value,f); else if(v.type==='JSXExpressionContainer')collect(v.expression,f);},
  JSXExpressionContainer(p){ if(p.parent.type==='JSXElement'||p.parent.type==='JSXFragment')collect(p.node.expression,f);},
  CallExpression(p){const c=p.node.callee; let name=''; if(c.type==='Identifier')name=c.name; else if(c.type==='MemberExpression'&&c.object.type==='Identifier')name=c.object.name+'.'+(c.property.name||'');
    if(/^toast(\.|$)/.test(name)||/^(alert|confirm)$/.test(name)||/^set(Error|Status|Message|Notice|Toast)\w*$/.test(name))p.node.arguments.forEach(a=>collect(a,f));},
  ObjectProperty(p){const k=p.node.key.name||p.node.key.value; if(KEYS.has(k))collect(p.node.value,f);},
 });}
walk(root);
const arr=[...out.entries()].sort((a,b)=>a[0].localeCompare(b[0]));
fs.writeFileSync(process.argv[3],JSON.stringify(arr,null,1)); console.log(arr.length,'strings');
