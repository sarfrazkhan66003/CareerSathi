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
