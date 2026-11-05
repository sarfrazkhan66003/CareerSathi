document.addEventListener('DOMContentLoaded',()=>{
 // quiz progress
 const quiz=document.getElementById('quizForm');
 if(quiz){const bar=document.getElementById('xProg'),txt=document.getElementById('xProgTxt'),btn=document.getElementById('quizSubmit');
  const upd=()=>{const total=quiz.querySelectorAll('fieldset').length;const done=quiz.querySelectorAll('input[type=radio]:checked').length;
   bar.style.width=(done/total*100)+'%';txt.textContent=done+' of '+total+' answered';btn.disabled=done<total;};
  quiz.addEventListener('change',upd);upd();}
 // checklists persist locally (per-device convenience only)
 document.querySelectorAll('[data-check-key]').forEach(box=>{const key='cs_'+box.dataset.checkKey;let saved={};
  try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
  box.querySelectorAll('input[type=checkbox]').forEach((c,i)=>{c.checked=!!saved[i];c.addEventListener('change',()=>{saved[i]=c.checked;try{localStorage.setItem(key,JSON.stringify(saved))}catch(e){}})});});
 // print buttons
 document.querySelectorAll('[data-print]').forEach(b=>b.addEventListener('click',()=>window.print()));
 // copy buttons
 document.querySelectorAll('[data-copy]').forEach(b=>b.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(b.dataset.copy);const o=b.textContent;b.textContent='Copied ✓';setTimeout(()=>b.textContent=o,1500)}catch(e){}}));
 // FAQ assistant
 const root=document.getElementById('xa');
 if(root){const box=document.getElementById('xaBox'),btn=document.getElementById('xaBtn'),log=document.getElementById('xaLog'),form=document.getElementById('xaForm'),inp=form.querySelector('input');
  const add=(t,c)=>{const p=document.createElement('p');p.className='xa-m '+c;p.textContent=t;log.appendChild(p);log.scrollTop=log.scrollHeight;};
  add('Hi! I am the CareerSathi FAQ assistant (automated, not a human counsellor). Ask about streams, mentors, plans, exams or scholarships.','b');
  btn.addEventListener('click',()=>{const o=box.classList.toggle('open');btn.setAttribute('aria-expanded',o);if(o)inp.focus();});
  form.addEventListener('submit',async e=>{e.preventDefault();const q=inp.value.trim();if(!q)return;add(q,'u');inp.value='';
   try{const r=await fetch('/assistant/ask',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':root.dataset.csrf},body:JSON.stringify({q})});
    const d=await r.json();add(d.answer||d.error||'Something went wrong.','b');}catch(err){add('Network problem. Please try again.','b');}});}
});

// ===== v12 =====
document.addEventListener('DOMContentLoaded',()=>{
 // PWA service worker
 if('serviceWorker' in navigator&&location.protocol!=='file:')navigator.serviceWorker.register('/sw.js').catch(()=>{});
 // Cloudflare Turnstile on the login form (only when configured on the server)
 const key=document.querySelector('meta[name=cs-turnstile]');
 const lf=document.querySelector('form[action="/login"]');
 if(key&&lf){const d=document.createElement('div');d.className='cf-turnstile';d.dataset.sitekey=key.content;lf.insertBefore(d,lf.querySelector('button'));
  const s=document.createElement('script');s.src='https://challenges.cloudflare.com/turnstile/v0/api.js';s.async=true;document.head.appendChild(s);}
 // assessment: timer + answered counter
 const af=document.getElementById('assessForm');
 if(af){const fs=af.querySelectorAll('fieldset'),out=document.getElementById('aCount'),tm=document.getElementById('aTimer'),btn=af.querySelector('button.btn-primary');
  const upd=()=>{let n=0;fs.forEach(f=>{if(f.querySelector('input:checked'))n++});out.textContent=n+' of '+fs.length+' answered';btn.disabled=n<fs.length;btn.title=n<fs.length?'Answer every question to submit':''};
  af.addEventListener('change',upd);upd();
  af.addEventListener('submit',e=>{if(btn.disabled){e.preventDefault();const f=[...fs].find(x=>!x.querySelector('input:checked'));if(f)f.scrollIntoView({behavior:'smooth',block:'center'})}});
  let left=parseInt(af.dataset.minutes||'30',10)*60;const tick=()=>{const m=Math.floor(left/60),s=left%60;tm.textContent='⏱ '+m+':'+String(s).padStart(2,'0');if(left--<=0){clearInterval(iv);tm.textContent='⏱ Time is over. Please finish the remaining questions to see your score.'}};const iv=setInterval(tick,1000);tick();}
 // enquiry form: adapt stream labels to the class, enforce max 5 colleges
 const g=document.getElementById('enqGrade');
 if(g){const lab=document.getElementById('enqStreamLabel'),hint=document.getElementById('enqStreamHint');
  const set=()=>{const v=g.value;if(['8','9','10'].includes(v)){lab.textContent='Which stream are you considering?';hint.textContent='Not sure yet? Pick "Not sure" and ask for stream guidance below.'}
   else if(v==='11'){lab.textContent='Which stream are you studying in Class 11?';hint.textContent=''}
   else{lab.textContent='Which stream did you study in Class 12?';hint.textContent='PCM, PCB, PCMB, Commerce or Arts.'}};g.addEventListener('change',set);set();}
 // enquiry: Science streams hidden for Class 8-10 below the score threshold; alert + roadmap when chosen anyway
 const ef=document.getElementById('enqForm');
 if(ef&&ef.dataset.score!==''){const score=+ef.dataset.score,th=+ef.dataset.threshold,low=score<th,G=['8','9','10'],SCI=['PCM','PCB','PCMB'];
  const st=document.getElementById('st'),gr=document.getElementById('enqGrade'),tpl=document.getElementById('sciOpts'),note=document.getElementById('sciLockNote'),un=document.getElementById('sciUnlock'),al=document.getElementById('sciAlert'),road=document.getElementById('sciRoadmap'),ack=document.getElementById('prepAck');
  const apply=()=>{const gated=low&&(G.includes(gr.value)||G.includes(ef.dataset.pgrade)),show=!gated||(un&&un.checked),cur=st.value;
   [...st.options].forEach(o=>{if(SCI.includes(o.value))o.remove()});
   if(show&&tpl){const un2=[...st.options].find(o=>o.value==='UNSURE');tpl.content.querySelectorAll('option').forEach(o=>st.insertBefore(o.cloneNode(true),un2||null))}
   if([...st.options].some(o=>o.value===cur))st.value=cur;else st.value='';
   if(note)note.hidden=!gated;
   const sci=SCI.includes(st.value);if(al){al.hidden=!(low&&sci);if(road&&sci)road.href='/stream-roadmap/'+st.value}
   if(ack)ack.value=(gated&&un&&un.checked&&sci)?'yes':''};
  [gr,st,un].forEach(x=>x&&x.addEventListener('change',apply));apply();}
 // share buttons
 document.querySelectorAll('[data-wa]').forEach(a=>{a.href='https://wa.me/?text='+encodeURIComponent(a.dataset.wa+' '+location.href)});
});
