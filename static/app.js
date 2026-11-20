const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let T=localStorage.t||'',S,ES,Q=[],AC,snd=0,cur=null,mode='home',CH=[],CHT=0,VOL=+(localStorage.vol??60);
const IC=p=>`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
const P={set:'<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
 clk:'<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',typ:'<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/>',
 out:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',vol:'<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>',
 trash:'<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',send:'<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',moon:'<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>'};
const ST={avail:['#22c55e','Available'],consult:['#3b82f6','In consultation'],rest:['#ef4444','Resting'],na:['#cbd5e1','Not set']};
if(localStorage.big=='1')document.body.classList.add('big');
async function api(p,b){const r=await fetch('/api/'+p,{method:b?'POST':'GET',headers:{'X-Token':T,'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined});
 if(r.status==401&&T){logout();throw 0}const j=await r.json();if(j.error&&r.status!=401)alert(j.error);return j}
function logout(){localStorage.t='';T='';ES&&ES.close();Q=[];show();$('#app').style.display='none';$('#login').style.display='block';loginView()}
function beep(u,l){if(!VOL)return;try{AC=AC||new AudioContext();AC.resume();const g0=VOL/100*(u?.9:.7);for(let i=0;i<(u?3:1);i++){const o=AC.createOscillator(),g=AC.createGain();o.type=u?'square':'sine';o.frequency.value=u?1250:l?1000:880;o.connect(g);g.connect(AC.destination);const t=AC.currentTime+i*.28;g.gain.setValueAtTime(g0,t);g.gain.exponentialRampToValueAtTime(.001,t+.22);o.start(t);o.stop(t+.25)}}catch(e){}}
function toast(t){const d=document.createElement('div');d.className='toast';d.textContent=t;$('#pops').appendChild(d);setTimeout(()=>d.remove(),4500)}
function off(x){$('#off').style.display=x?'block':'none'}
setInterval(()=>{document.title=Q.length?(document.title.startsWith('●')?'Clinic Connect':'● New alert'):'Clinic Connect'},900);
setInterval(()=>{if(mode=='chat'&&$('#msgs'))paint()},10000);
async function loginView(){const u=await (await fetch('/api/users')).json(),g={};u.forEach(x=>(g[x.role]=g[x.role]||[]).push(x));sel=null;
 $('#login').innerHTML=`<div class="card" style="padding:28px"><div class="logo">+</div><h1>Clinic Connect</h1><p class="s">Select your name, then enter your password</p>`+
 Object.entries(g).map(([r,a])=>`<div class="cap" style="margin:16px 0 8px">${esc(r)}</div><div class="row">`+a.map(x=>`<button data-u="${esc(x.id)}">${esc(x.name)}</button>`).join('')+`</div>`).join('')+
 `<input id="pw" type="password" placeholder="Password" style="width:100%;margin-top:18px"><p id="er" class="s" style="color:#dc2626;min-height:18px"></p><button class="p" id="go" style="width:100%;padding:12px">Sign in</button></div>`;
 document.querySelectorAll('[data-u]').forEach(b=>b.onclick=()=>{sel=b.dataset.u;document.querySelectorAll('[data-u]').forEach(x=>x.classList.toggle('on',x==b));$('#pw').focus()});
 const go=async()=>{if(!sel)return $('#er').textContent='Select your name first';beep(0,0);
  const r=await (await fetch('/api/login',{method:'POST',body:JSON.stringify({id:sel,pw:$('#pw').value})})).json();if(r.token){T=localStorage.t=r.token;start()}else $('#er').textContent=r.error};
 $('#go').onclick=go;$('#pw').onkeydown=e=>{if(e.key=='Enter')go()}}
let sel=null;
async function start(){S=await api('state');$('#login').style.display='none';$('#app').style.display='flex';mode='home';cur=null;draw();
 ES&&ES.close();ES=new EventSource('/api/stream?t='+T);ES.onopen=()=>off(0);ES.onerror=()=>off(1);
 ES.onmessage=async e=>{const m=JSON.parse(e.data);
  if(m.t=='msg'){if(!Q.find(x=>x.id==m.id)){Q.push(m);notify(m)}show();loop()}
  else if(m.t=='info'){Q.push({id:'i'+Date.now(),info:1,icon:'!',color:'#d97706',label:'No reply',from_name:'No reply yet',text:m.text,ts:new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}),frm:''});show();loop()}
  else if(m.t=='close'){Q=Q.filter(x=>x.id!=m.id);if(m.note)toast(m.note);show()}
  else if(m.t=='esc'){const x=Q.find(y=>y.id==m.id);if(x){x.esc=1;show()}}
  else if(m.t=='toast')toast(m.text);
  S=await api('state');if(mode=='admin'||mode=='hist')return;if($('#board'))$('#board').innerHTML=board();list();if(mode=='chat'&&cur)reloadMsgs()};
 if(window.Notification&&Notification.permission=='default')Notification.requestPermission()}
function notify(m){if(window.Notification&&Notification.permission=='granted'){try{new Notification(m.from_name,{body:m.text,requireInteraction:true})}catch(e){}}}
function loop(){if(snd)return;const f=()=>{if(!Q.length){snd=0;return}const m=Q[0];if(!m.info||!m.beeped){beep(m.urgent,m.esc);m.beeped=1}snd=setTimeout(f,m.esc?2000:3000+Math.random()*2000)};f()}
function show(){const o=$('#ov');if(!Q.length){o.style.display='none';return}const m=Q[0],info=m.info,col=m.urgent?'#dc2626':(m.color||'#0f766e');o.style.display='block';
 o.innerHTML=`<div class="bc" style="--c:${esc(col)}">${m.esc?'<div class="esc">No response for 2 minutes</div>':''}<div class="bh"><div class="bi">${esc(m.icon)}</div><div style="flex:1"><div class="bl">${m.urgent?'URGENT · ':''}${esc(m.label)}</div><div class="bn">${esc(m.from_name)}</div></div>${Q.length>1?`<span class="s">+${Q.length-1} more</span>`:''}</div>
 <div class="bt">${esc(m.text)}</div><div class="s">${esc(m.ts)}</div>
 ${info?'':`<div class="qr">${['OK','Coming in 5 min','Wait please'].map(x=>`<button data-q="${x}">${x}</button>`).join('')}</div><div class="rr"><input id="rp" placeholder="Type a reply…"><button class="p" id="rb">Send</button></div>`}
 ${m.claim?'<button class="claim" id="cl">I\'ll take it</button>':''}<button class="gok" id="ok">${info?'OK':'Understood'}</button></div>`;
 const end=p=>{Q=Q.filter(x=>x.id!=m.id);if(!info)api(p,{id:m.id});show()};$('#ok').onclick=()=>end('ack');if($('#cl'))$('#cl').onclick=()=>end('claim');
 o.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{api('send',{to:m.frm,text:b.dataset.q});end('ack')});
 if($('#rp')){const r=()=>{if($('#rp').value.trim()){api('send',{to:m.frm,text:$('#rp').value});end('ack')}};$('#rb').onclick=r;$('#rp').onkeydown=e=>{if(e.key=='Enter')r()}}}
const board=()=>S.board.map(d=>`<span class="bd"><i class="dt" style="background:${ST[d.s][0]}"></i><b>${esc(d.name)}</b><span class="s">${ST[d.s][1]}</span></span>`).join('')||'<span class="s">No doctors yet</span>';
const AVC=['#0f766e','#2563eb','#d97706','#7c3aed','#db2777','#0891b2'];
const av=(n,id)=>`<div class="av" style="background:${AVC[[...String(id)].reduce((a,c)=>a+c.charCodeAt(0),0)%6]}">${esc(String(n).split(/\s+/).filter(w=>w).slice(0,2).map(w=>w[0]).join('').toUpperCase())}</div>`;
const tk=m=>m.st=='read'?'<b class="tkb" title="Understood">✓✓</b>':m.st=='delivered'?'<span class="tkg" title="Delivered">✓✓</span>':m.st=='sent'?'<span class="tkg" title="Sent">✓</span>':'';
function draw(){const adm=S.me.role=='admin';
 $('#app').innerHTML=`<div id="side"><div class="sh">${av(S.me.name,S.me.id)}<div class="who"><b>${esc(S.me.name)}</b><span class="s">${esc(S.roles[S.me.role]||'')}</span></div><div class="ib2">${adm?`<button id="ad" title="Admin">${IC(P.set)}</button><button id="hs" title="History">${IC(P.clk)}</button>`:''}<button id="bg" title="Larger text">${IC(P.typ)}</button><button id="lo" title="Sign out">${IC(P.out)}</button></div></div>
 <div class="ctl"><label class="sw" title="Away from desk: you get no pop-ups and others see you are unavailable (urgent still comes through)"><input type="checkbox" id="dnd" ${S.me.dnd?'checked':''}><i></i><span>Do not disturb</span></label>
 <div class="vl" title="Alert volume">${IC(P.vol)}<input type="range" id="vol" min="0" max="100" value="${VOL}"><button class="lk" id="vt">Test</button></div></div>
 <div class="dst"><div class="cap">Doctors</div><div id="board">${board()}</div>${S.can_status?`<div class="seg">`+['avail','consult','rest'].map(k=>`<button class="${S.my_status==k?'on':''}" data-s="${k}"><i class="dt" style="background:${ST[k][0]}"></i>${ST[k][1]}</button>`).join('')+'</div>':''}</div>
 <input id="sq" class="sq" placeholder="Search"><div id="cl"></div></div><div id="main"></div>`;
 $('#lo').onclick=logout;$('#bg').onclick=()=>{localStorage.big=localStorage.big=='1'?'0':'1';document.body.classList.toggle('big')};
 if($('#ad')){$('#ad').onclick=()=>admPane('Admin',admin,'admin');$('#hs').onclick=()=>admPane('History',hist,'hist')}
 $('#dnd').onchange=async e=>{await api('dnd',{on:e.target.checked});S=await api('state');list();toast(e.target.checked?'Do not disturb is ON - no pop-ups':'Do not disturb is OFF')};
 $('#vol').oninput=e=>{VOL=+e.target.value;localStorage.vol=VOL};$('#vol').onchange=()=>beep(0,0);$('#vt').onclick=()=>beep(0,0);
 document.querySelectorAll('[data-s]').forEach(b=>b.onclick=async()=>{await api('status',{s:b.dataset.s});S=await api('state');draw()});
 $('#sq').oninput=list;list();pane()}
function list(){const q=($('#sq')?.value||'').toLowerCase();$('#cl').innerHTML=S.people.filter(p=>p.name.toLowerCase().includes(q)).map(p=>`<div class="ct${p.id==cur&&mode=='chat'?' act':''}" data-c="${p.id}">${av(p.name,p.id)}<div class="ci"><div class="r1"><b>${esc(p.name)}${p.dnd?` <span class="dn" title="Do not disturb">${IC(P.moon)}</span>`:''}</b><span class="s">${esc(p.lts)}</span></div><div class="r2"><span class="pv">${p.lmine?tk({st:p.lst})+' ':''}${esc(p.last||S.roles[p.role]||'')}</span>${p.unread?`<span class="bdg">${p.unread}</span>`:''}</div></div>${p.online?'<i class="on"></i>':''}</div>`).join('')||'<p class="s" style="padding:16px">No contacts</p>';
 document.querySelectorAll('[data-c]').forEach(e=>e.onclick=()=>{cur=e.dataset.c;mode='chat';openChat()})}
function back(){mode='home';cur=null;list();pane()}
function pane(){if(mode=='chat'&&cur)return openChat();$('#app').classList.remove('inchat');const A=S.role.actions;
 $('#main').innerHTML=`<div class="wl"><div class="logo">+</div><h1>Clinic Connect</h1><p class="s">Select a conversation to see messages.${A.length?'<br>Or send a quick alert to everyone:':''}</p>`+(A.length?`<div class="row" style="justify-content:center"><input id="nt" placeholder="Patient / token (optional)" style="flex:none;width:220px"><label class="s"><input type="checkbox" id="ur" style="padding:0"> Urgent</label></div><div class="row" style="justify-content:center;margin-top:12px">${A.map((a,i)=>`<button class="qa" style="--c:${esc(a.color)}" data-wa="${i}">${esc(a.icon)} ${esc(a.label)} → ${esc(S.roles[a.to]||a.to)}</button>`).join('')}</div>`:'')+`</div>`;
 document.querySelectorAll('[data-wa]').forEach(b=>b.onclick=async()=>{await api('send',{action:b.dataset.wa,to:'all',note:$('#nt').value.trim(),urgent:$('#ur').checked});$('#nt').value='';toast('Sent')})}
function admPane(t,f,m){mode=m;cur=null;list();$('#app').classList.add('inchat');$('#main').innerHTML=`<div class="ch"><b style="flex:1">${t}</b><button class="cb" id="cx">Close</button></div><div id="body" class="bodys"></div>`;$('#cx').onclick=back;f()}
const msgsHTML=()=>{let d=null,h='';const now=Date.now();CH.forEach(m=>{if(m.day!==d){d=m.day;if(d)h+=`<div class="dy"><span>${esc(d)}</span></div>`}const me=m.frm==S.me.id,ac=m.kind=='action';
 if(m.del){h+=`<div class="mw ${me?'me':''}"><div class="bb gone">This message was deleted</div></div>`;return}
 const can=me&&(m.age+(now-CHT)/1000)<60;
 h+=`<div class="mw ${me?'me':''}">${can?`<button class="dl" data-d="${m.id}" title="Delete (possible for 1 minute)">${IC(P.trash)}</button>`:''}<div class="bb${ac?' ac':''}${m.urgent?' ur':''}"${ac?` style="--c:${esc(m.color)}"`:''}>${ac?`<div class="al">${esc(m.icon)} ${esc(m.label)}${m.urgent?' · URGENT':''}</div>`:m.urgent?'<div class="al">URGENT</div>':''}<div>${esc(m.text)}</div><div class="mt">${esc(m.ts)} ${me?tk(m):''}</div>${me&&m.esc&&m.st!='read'?'<div class="nr">No reply after 2 min</div>':''}</div></div>`});
 return h||'<div class="dy"><span>No messages yet</span></div>'};
function paint(){const e=$('#msgs');if(!e)return;const atEnd=e.scrollHeight-e.scrollTop-e.clientHeight<80;e.innerHTML=msgsHTML();if(atEnd||!e.dataset.f){e.scrollTop=e.scrollHeight;e.dataset.f=1}
 e.querySelectorAll('[data-d]').forEach(b=>b.onclick=async()=>{await api('delete',{id:b.dataset.d});reloadMsgs()})}
async function reloadMsgs(){if(!cur)return;CH=await api('chat?w='+cur);CHT=Date.now();paint()}
async function openChat(){const p=S.people.find(x=>x.id==cur);if(!p)return back();mode='chat';list();$('#app').classList.add('inchat');const A=S.role.actions;
 $('#main').innerHTML=`<div class="ch"><button class="bk" id="bk">←</button>${av(p.name,p.id)}<div><b>${esc(p.name)}</b><div class="s">${p.online?'Online':'Offline'}${p.dnd?' · Do not disturb (away)':''} · ${esc(S.roles[p.role]||'')}</div></div></div><div id="msgs"></div>
 ${A.length?`<div class="chips">${A.map((a,i)=>`<button class="chip" style="--c:${esc(a.color)}" data-ca="${i}" title="Type a patient/token note first (optional)">${esc(a.icon)} ${esc(a.label)}</button>`).join('')}</div>`:''}
 <div class="ib"><label class="urg" title="Mark as urgent"><input type="checkbox" id="ur"><span>Urgent</span></label><input id="mx" placeholder="Type a message"><button class="snd" id="ms" title="Send">${IC(P.send)}</button></div>`;
 $('#bk').onclick=back;
 const send=async()=>{const x=$('#mx').value.trim();if(!x)return;$('#mx').value='';await api('send',{to:cur,text:x,urgent:$('#ur').checked});$('#ur').checked=false;reloadMsgs()};
 $('#ms').onclick=send;$('#mx').onkeydown=e=>{if(e.key=='Enter')send()};
 document.querySelectorAll('[data-ca]').forEach(b=>b.onclick=async()=>{const a=A[b.dataset.ca],one=p.role==a.to;
  if(!one&&!confirm(`"${a.label}" goes to everyone in ${S.roles[a.to]||a.to}. Send?`))return;
  await api('send',{action:b.dataset.ca,to:one?cur:'all',note:$('#mx').value.trim(),urgent:$('#ur').checked});$('#mx').value='';$('#ur').checked=false;reloadMsgs()});
 await reloadMsgs();$('#mx').focus()}
async function hist(){const Hh=await api('admin/history');let f='',st='';
 const rows=()=>Hh.rows.filter(r=>(!st||r.st==st)&&(!f||(r.from+r.to+r.text+r.label).toLowerCase().includes(f))).map(r=>`<tr><td>${esc(r.date)}</td><td>${esc(r.from)}</td><td>${esc(r.to)}</td><td>${r.urgent?'🚨 ':''}${esc(r.text)}</td><td>${r.st=='read'?'✓✓ understood':r.st=='delivered'?'✓✓ delivered':'✓ sent'}</td><td>${esc(r.dtm)}</td><td>${esc(r.rtm)}</td><td>${r.secs??''}</td></tr>`).join('');
 $('#body').innerHTML=`<div class="card"><h2>Slowest to respond (average seconds)</h2><div class="row">${Hh.stats.map(s=>`<span class="bd"><b>${esc(s.name)}</b> ${s.avg}s <span class="s">(${s.n})</span></span>`).join('')||'<span class="s">No data yet</span>'}</div></div>
 <div class="card"><div class="row"><input id="hf" placeholder="Search name or message…"><select id="hs"><option value="">All</option><option value="sent">Sent</option><option value="delivered">Delivered</option><option value="read">Understood</option></select><button class="p" id="ex">⬇ Export CSV</button></div>
 <div style="overflow:auto;margin-top:10px"><table id="ht"><tr><th>Date</th><th>From</th><th>To</th><th>Message</th><th>Status</th><th>Delivered</th><th>Understood</th><th>Secs</th></tr><tbody id="hb">${rows()}</tbody></table></div></div>`;
 $('#hf').oninput=e=>{f=e.target.value.toLowerCase();$('#hb').innerHTML=rows()};$('#hs').onchange=e=>{st=e.target.value;$('#hb').innerHTML=rows()};$('#ex').onclick=()=>location='/api/admin/export?t='+T}
async function admin(){const A=await api('admin/data'),ro=Object.entries(A.roles),ropt=v=>ro.map(([k,r])=>`<option value="${k}"${k==v?' selected':''}>${esc(r.label)}</option>`).join('');
 function arow(a={icon:'🔔',label:'',text:'',to:'',color:'#0A84FF',claim:false}){return `<div class="row ar"><input class="i" value="${esc(a.icon)}"><input class="l" placeholder="Button name" value="${esc(a.label)}"><input class="x" placeholder="Message shown" value="${esc(a.text)}"><select class="to">${ropt(a.to)}</select><input class="c" type="color" value="${esc(a.color)}"><label class="s" style="flex:none"><input class="cl" type="checkbox" ${a.claim?'checked':''} style="flex:none"> ✋ claim</label><button class="d x2">✕</button></div>`}
 $('#body').innerHTML=`<div class="card"><h2>Users</h2><div style="overflow:auto"><table>`+Object.entries(A.users).map(([id,u])=>`<tr data-u="${id}"><td><input class="n" value="${esc(u.name)}" style="width:100%"></td><td><select class="r" ${id==S.me.id?'disabled title="You cannot change your own role"':''}>${ropt(u.role)}</select></td>
 <td><input class="w" type="text" placeholder="New password" style="width:130px"></td><td><button class="p sv">Save</button> <button class="d dl">Delete</button></td></tr>`).join('')+`</table></div>
 <h2 style="margin-top:18px">Add user</h2><div class="row"><input id="nn" placeholder="Full name"><select id="nr">${ropt()}</select><input id="np" placeholder="Password"><button class="p" id="na">+ Add</button></div></div>
 <div class="card"><h2>Roles &amp; task buttons</h2><p class="s">Each button sends a pop-up to everyone in the target role (or one person). ✋ claim = first person to tap "I'll take it" closes it for the others.</p>`+
 ro.map(([k,r])=>`<div class="card" style="background:#fff" data-r="${k}"><div class="row"><input class="rl" value="${esc(r.label)}" ${k=='admin'?'disabled':''}><button class="p rs">Save role</button>${k=='admin'?'':'<button class="d rd">Delete role</button>'}</div><div class="acts">${r.actions.map(arow).join('')}</div><button class="aa" style="margin-top:6px">+ Add task button</button></div>`).join('')+
 `<h2>New role</h2><div class="row"><input id="rn" placeholder="e.g. Lab, Nurse, Pharmacy"><button class="p" id="ra">+ Create role</button></div></div>`;
 const R=()=>admin();document.querySelectorAll('tr[data-u]').forEach(t=>{const id=t.dataset.u;t.querySelector('.sv').onclick=async()=>{const r=await api('admin/user_save',{id,name:t.querySelector('.n').value,role:t.querySelector('.r').value,pw:t.querySelector('.w').value});if(!r.error){toast('Saved ✓');R()}};
  t.querySelector('.dl').onclick=async()=>{if(confirm('Delete '+t.querySelector('.n').value+'?')){await api('admin/user_del',{id});R()}}});
 $('#na').onclick=async()=>{const r=await api('admin/user_save',{name:$('#nn').value,role:$('#nr').value,pw:$('#np').value});if(!r.error)R()};
 $('#ra').onclick=async()=>{if($('#rn').value.trim()){await api('admin/role_save',{label:$('#rn').value,actions:[]});R()}};
 document.querySelectorAll('[data-r]').forEach(c=>{const id=c.dataset.r,box=c.querySelector('.acts'),wire=r=>r.querySelector('.x2').onclick=()=>r.remove();box.querySelectorAll('.ar').forEach(wire);
  c.querySelector('.aa').onclick=()=>{box.insertAdjacentHTML('beforeend',arow());wire(box.lastElementChild)};
  c.querySelector('.rs').onclick=async()=>{await api('admin/role_save',{id,label:c.querySelector('.rl').value,actions:[...box.querySelectorAll('.ar')].filter(r=>r.querySelector('.l').value.trim()).map(r=>({icon:r.querySelector('.i').value,label:r.querySelector('.l').value,text:r.querySelector('.x').value||r.querySelector('.l').value,to:r.querySelector('.to').value,color:r.querySelector('.c').value,claim:r.querySelector('.cl').checked}))});toast('Role saved ✓');R()};
  const rd=c.querySelector('.rd');if(rd)rd.onclick=async()=>{if(confirm('Delete this role?')){await api('admin/role_del',{id});R()}}})}
T?start().catch(loginView):loginView();
