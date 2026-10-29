'use strict';
const $=id=>document.getElementById(id);
const names={circle:'Daire',square:'Kare',triangle:'Üçgen',diamond:'Elmas'};
const targetEls=[...document.querySelectorAll('.target')];
let api=null,state=null,lastToken=null,acknowledged=null,busy=false,geometryKey='',userBusy=false,errorToken=null;
function notice(message=''){ $('error').textContent=message; $('notice').classList.toggle('hidden',!message); }
async function act(action,payload={}){
  if(userBusy)return;
  if(!api){notice('Uygulama henüz hazır değil. Birkaç saniye bekle.');return;}
  userBusy=true;
  try{const r=await command(action,payload);if(r?.ok)notice();}
  finally{userBusy=false;}
}
function geometry(){return [innerWidth,innerHeight,screenX,screenY,devicePixelRatio];}
async function command(action,payload={}){
  if(!api)return null;
  try{const r=await api.command(action,payload);if(!r.ok)notice(r.message);return r;}
  catch(e){notice('Uygulama bağlantısı kesildi. Pencereyi yeniden aç.');}
}
function regions(){return Object.fromEntries(targetEls.map(el=>{const r=el.getBoundingClientRect();return [el.dataset.shape,[r.x/innerWidth,r.y/innerHeight,r.width/innerWidth,r.height/innerHeight]];}));}
function show(section){for(const id of ['preparation','ready','results','measurement','demo']){
  const el=$(id);el.classList.toggle('hidden',id!==section);el.style.display=id===section?(id==='preparation'?'grid':'block'):'none';
}}
function results(s){const count=k=>s.trials.filter(t=>t.outcome===k).length;
  $('correct').textContent=count('correct')+' / '+s.total_trials;
  $('wrong').textContent=count('incorrect');$('timeout').textContent=count('timeout');
  $('duration').textContent=(s.trials.reduce((n,t)=>n+t.elapsed_s,0)/Math.max(1,s.trials.length)).toFixed(1)+' sn';
  $('trialRows').replaceChildren(...s.trials.map((t,i)=>{const row=document.createElement('tr');for(const value of [i+1,names[t.expected],names[t.selected]||'—',({correct:'Doğru',incorrect:'Yanlış',timeout:'Süre doldu'})[t.outcome],t.elapsed_s.toFixed(1)+' sn']){const c=document.createElement('td');c.textContent=value;row.append(c);}return row;}));
  $('recordPath').textContent=s.record_path?'Seçimlerin bu cihazda saklandı.':'Bu oturum kaydedilemedi.';
}
function render(s){
  state=s;const phase=s.phase;const measurement=['calibration','check','fitting'].includes(phase);
  if(lastToken!==s.token){
    lastToken=s.token;acknowledged=null;
    show(measurement?'measurement':['ready','demo','results'].includes(phase)?phase:'preparation');
    if(phase==='results')results(s);
  }
  if(phase==='error'&&errorToken!==s.token){errorToken=s.token;notice(s.message);}
  $('cameraBadge').textContent=({off:'Kamera kapalı',loading:'Kamera hazırlanıyor',ready:s.tracking?'Gözlerin görünüyor':'Yüzünü kameraya çevir',stopping:'Kamera kapanıyor',error:'Kamera açılamadı'})[s.camera];
  $('cameraBadge').classList.toggle('tracking',s.camera==='ready'&&s.tracking);
  $('cameraStart').disabled=s.camera==='stopping';
  $('cameraBadge').classList.toggle('loading',['loading','stopping'].includes(s.camera));
  $('navCalibrate').disabled=s.camera!=='ready'||!s.tracking;
  $('navPractice').disabled=!s.can_demo||s.camera!=='ready';
  $('cameraStart').textContent=s.camera==='loading'?'Vazgeç':s.camera==='stopping'?'Kapatılıyor…':s.camera==='ready'?'Kamerayı kapat':'Kamerayı aç';
  $('calibrate').disabled=s.camera!=='ready'||!s.tracking;
  if(s.preview){$('preview').src=s.preview;$('preview').classList.remove('hidden');$('cameraPlaceholder').classList.add('hidden');}
  else{$('preview').classList.add('hidden');$('cameraPlaceholder').classList.remove('hidden');}
  $('cameraHint').textContent=s.camera==='ready'?(s.tracking?'Rahat konumunu koru.':'Yüzün ve gözlerin kamerada görünsün.'):s.camera==='loading'?'İlk açılış birkaç saniye sürebilir.':'Kamera yalnızca başlattığında açılır.';
  if(measurement){$('fitting').classList.toggle('hidden',phase!=='fitting');$('fixation').classList.toggle('hidden',!s.point);if(s.point){$('fixation').style.left=s.point[0]*100+'%';$('fixation').style.top=s.point[1]*100+'%';}}
  if(phase==='ready')$('checkError').textContent=Math.round(s.checks.reduce((v,r)=>v+r.mean_px,0)/s.checks.length)+' px';
  if(phase==='demo'){
    $('instruction').textContent=s.paused?'Mola veriyoruz.':({circle:'Daireyi',square:'Kareyi',triangle:'Üçgeni',diamond:'Elması'})[s.expected]+' seç.';
    $('trialInfo').textContent=s.paused?'Hazır olduğunda Devam et düğmesine bas.':`Adım ${s.index+1} / ${s.total_trials} · İstenen şekle bakışını sabitle.`;
    $('pause').textContent=s.paused?'Devam et':'Duraklat';$('targets').classList.toggle('paused',s.paused);
    $('trackingLabel').textContent=s.paused?'Duraklatıldı':s.tracking?'Bakışın izleniyor':'Gözlerin görünmüyor. Kameraya doğru bak.';
    for(const el of targetEls){const on=el.dataset.shape===s.dwell_target&&!s.paused;el.classList.toggle('focused',on);el.querySelector('.fill').style.width=(on?s.dwell_progress*100:0)+'%';}
    const t=s.trials.at(-1);$('lastTrial').textContent=t?`Önceki: ${t.outcome==='correct'?'doğru':t.outcome==='incorrect'?'yanlış':'süre doldu'}`:'';
  }
  if(acknowledged!==s.token&&['calibration','check','demo'].includes(phase)&&!s.paused){
    const token=s.token;acknowledged=token;
    requestAnimationFrame(()=>requestAnimationFrame(async()=>{
      if(lastToken!==token)return;
      if(phase==='demo'){const r=await command('regions',{regions:regions()});if(!r?.ok){await command('pause');return;}}
      await command('ack',{token});
    }));
  }
}
async function poll(){
 if(!api||busy)return;busy=true;
 try{const g=geometry(),key=JSON.stringify(g);if(geometryKey!==key){geometryKey=key;await command('geometry',{geometry:g});}
   const s=await api.snapshot();render(s);
 }catch(e){notice('Uygulama bağlantısı kesildi. Pencereyi yeniden aç.');for(const el of targetEls)el.querySelector('.fill').style.width='0%';}
 finally{busy=false;setTimeout(poll,50);}
}
$('cameraStart').onclick=()=>act(['ready','loading'].includes(state?.camera)?'stop_camera':'camera');
const calibrate=()=>act('calibrate',{geometry:geometry()});
for(const id of ['calibrate','recalibrateReady','recalibrateResult','navCalibrate'])$(id).onclick=calibrate;
for(const id of ['startDemo','again','navPractice'])$(id).onclick=()=>act('demo');
for(const id of ['navHome','homeDemo','homeReady','homeResult'])$(id).onclick=()=>act('home');
$('pause').onclick=()=>act(state?.paused?'resume':'pause');
$('cancelMeasure').onclick=()=>act('pause');
$('dismissError').onclick=()=>notice();
window.addEventListener('blur',()=>command('focus',{active:false}));
window.addEventListener('focus',()=>command('focus',{active:true}));
document.addEventListener('visibilitychange',()=>command('focus',{active:!document.hidden&&document.hasFocus()}));
document.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();act('pause');}});
function connect(){
  if(api||!window.pywebview?.api)return;
  api=window.pywebview.api;
  notice();
  command('focus',{active:document.hasFocus()});
  poll();
}
window.addEventListener('pywebviewready',connect);
show('preparation');
connect();
setTimeout(()=>{if(!api)notice('Uygulama başlatılamadı. Pencereyi kapatıp yeniden aç.');},10000);
