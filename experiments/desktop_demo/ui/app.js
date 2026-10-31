'use strict';
const $=id=>document.getElementById(id);
const names={overview:'Genel bakış',notes:'Notlar',search:'Notlarda ara',title:'Başlık',reminder:'Hatırlatıcı ekle',save:'Notu kaydet',details:'Ayrıntı',clear:'Temizle'};
const targetEls=[...document.querySelectorAll('.web-target')];
let appliedTrial=0;
let api=null,state=null,lastToken=null,acknowledged=null,busy=false,geometryKey='',userBusy=false,errorToken=null,activePage='home',preferenceEpoch=0,preferenceSaving=false;
function notice(message=''){ $('error').textContent=message; $('notice').classList.toggle('hidden',!message); }
async function act(action,payload={}){
  if(userBusy)return;
  if(!api){notice('Uygulama henüz hazır değil. Birkaç saniye bekle.');return;}
  userBusy=true;
  try{const r=await command(action,payload);if(r?.ok)notice();return r;}
  finally{userBusy=false;}
}
function geometry(){return [innerWidth,innerHeight,screenX,screenY,devicePixelRatio];}
async function command(action,payload={}){
  if(!api)return null;
  try{const r=await api.command(action,payload);if(!r.ok)notice(r.message);return r;}
  catch(e){notice('Uygulama bağlantısı kesildi. Pencereyi yeniden aç.');}
}
function regions(){return Object.fromEntries(targetEls.map(el=>{const r=el.getBoundingClientRect();return [el.dataset.control,[r.x/innerWidth,r.y/innerHeight,r.width/innerWidth,r.height/innerHeight]];}));}
const pageLabels={home:'Ana sayfa',calibration:'Kalibrasyon',practice:'Bakışla seçim',settings:'Ayarlar',help:'Yardım'};
function show(section){
  for(const id of ['preparation','ready','results','measurement','demo']){
    $(id).classList.toggle('hidden',id!==section);
  }
}
function page(name){
  activePage=name;
  for(const key of Object.keys(pageLabels))$(key+'Page').classList.toggle('hidden',key!==name);
  for(const el of document.querySelectorAll('[data-page]')){
    const selected=el.dataset.page===name;
    el.classList.toggle('on',selected);
    if(selected)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');
  }
  $('pageLabel').textContent=pageLabels[name];
  for(const id of ['setupArea','setupActions'])$(id).classList.toggle('hidden',!['home','calibration'].includes(name));
  document.querySelector('.main').scrollTop=0;
}
async function navigate(name){
  if(state&&!['preparation','error'].includes(state.phase)){
    const r=await act('home');if(!r?.ok)return;
  }
  show('preparation');page(name);
}
function appearance(p){
  if(!p)return;
  document.documentElement.dataset.theme=p.theme;
  document.documentElement.dataset.reducedMotion=String(p.reduced_motion);
  for(const el of document.querySelectorAll('[data-theme-choice]'))el.setAttribute('aria-pressed',String(el.dataset.themeChoice===p.theme));
  $('motionToggle').setAttribute('aria-checked',String(p.reduced_motion));
}
async function saveAppearance(p){
  if(userBusy)return;
  preferenceSaving=true;preferenceEpoch++;
  try{
    const r=await act('preferences',p);
    if(r?.ok){
      state.preferences={...state.preferences,...p};
      appearance(state.preferences);
      $('settingsStatus').textContent='Tercihin kaydedildi.';
    }else $('settingsStatus').textContent='Tercih kaydedilemedi. Önceki görünüm korundu.';
  }finally{preferenceEpoch++;preferenceSaving=false;}
}
function results(s){const count=k=>s.trials.filter(t=>t.outcome===k).length;
  $('correct').textContent=count('correct')+' / '+s.total_trials;
  $('wrong').textContent=count('incorrect');$('timeout').textContent=count('timeout');
  $('duration').textContent=(s.trials.reduce((n,t)=>n+t.elapsed_s,0)/Math.max(1,s.trials.length)).toFixed(1)+' sn';
  $('trialRows').replaceChildren(...s.trials.map((t,i)=>{const row=document.createElement('tr');for(const value of [i+1,names[t.expected],names[t.selected]||'—',({correct:'Doğru',incorrect:'Yanlış',timeout:'Süre doldu'})[t.outcome],t.elapsed_s.toFixed(1)+' sn']){const c=document.createElement('td');c.textContent=value;row.append(c);}return row;}));
  $('recordPath').textContent=s.record_path?'Seçimlerin bu cihazda saklandı.':'Bu oturum kaydedilemedi.';
}
function render(s){
  state=s;document.title='Eye Tracker · '+(s.model_name==='mgaze'?'MGaze':'UniGaze');const phase=s.phase;const measurement=['calibration','check','fitting'].includes(phase);
  if(lastToken!==s.token){
    lastToken=s.token;acknowledged=null;
    show(measurement?'measurement':['ready','demo','results'].includes(phase)?phase:'preparation');
    if(phase==='results')results(s);
    if(phase==='error'){page('calibration');}
    if(['ready','results'].includes(phase))activePage='practice';
  }
  if(phase==='error'&&errorToken!==s.token){errorToken=s.token;notice(s.message);}
  $('cameraBadge').textContent=({off:'Kamera kapalı',loading:'Kamera hazırlanıyor',ready:s.tracking?'Gözlerin görünüyor':'Yüzünü kameraya çevir',stopping:'Kamera kapanıyor',error:'Kamera açılamadı'})[s.camera];
  appearance(s.preferences);
  $('cameraBadge').classList.toggle('failed',s.camera==='error');
  $('cameraBadge').classList.toggle('tracking',s.camera==='ready'&&s.tracking);
  $('cameraStart').disabled=s.camera==='stopping';
  $('cameraBadge').classList.toggle('loading',['loading','stopping'].includes(s.camera));
  $('practiceStart').disabled=!s.can_demo||s.camera!=='ready';
  $('practiceStatus').textContent=s.can_demo&&s.camera==='ready'?'Göz ayarın hazır. İstediğinde başlayabilirsin.':'Önce kamerayı açıp kalibrasyonu tamamla.';
  $('cameraStart').textContent=s.camera==='loading'?'Vazgeç':s.camera==='stopping'?'Kapatılıyor…':s.camera==='ready'?'Kamerayı kapat':'Kamerayı aç';
  $('calibrate').disabled=s.camera!=='ready'||!s.tracking;
  $('cameraStart').className=s.camera==='ready'?'quiet':'primary';
  $('calibrate').className=s.camera==='ready'?'primary':'quiet';
  $('stepCamera').className=s.camera==='ready'?'done':'current';
  $('stepCalibration').className=s.can_demo?'done':s.camera==='ready'?'current':'';
  $('stepPractice').className=s.can_demo?'current':'';
  if(s.preview){if($('preview').src!==s.preview)$('preview').src=s.preview;$('preview').classList.remove('hidden');$('cameraPlaceholder').classList.add('hidden');}
  else{$('preview').classList.add('hidden');$('cameraPlaceholder').classList.remove('hidden');}
  if(s.eye_preview){
    if($('eyePreview').src!==s.eye_preview)$('eyePreview').src=s.eye_preview;
    $('eyePreview').classList.remove('hidden');$('eyePlaceholder').classList.add('hidden');
  }else{$('eyePreview').classList.add('hidden');$('eyePlaceholder').classList.remove('hidden');$('eyePlaceholder').textContent=s.camera==='ready'?'Gözler aranıyor…':'Kamera açıldığında görünür.';}
  if(measurement){
    $('fitting').classList.toggle('hidden',phase!=='fitting');
    $('fixation').classList.toggle('hidden',!s.point);
    if(s.point){
      $('fixation').style.left=s.point[0]*100+'%';$('fixation').style.top=s.point[1]*100+'%';
      $('fixation').classList.toggle('label-above',s.point[1]>=.8);
      $('measureLabel').style.left=(12+Math.max(110,Math.min(innerWidth-110,s.point[0]*innerWidth))-s.point[0]*innerWidth)+'px';
    }
    const m=s.measurement;
    if(m){$('measureLabel').textContent=(m.phase==='calibration'?'Kalibrasyon':'Kontrol')+' '+m.index+'/'+m.total+' · '+(m.sample_based?m.samples+'/'+m.required_samples+' örnek':m.remaining_s.toFixed(1)+' sn');$('measureProgress').style.width=m.remaining_fraction*100+'%';}
  }
  if(s.trials.length<appliedTrial)appliedTrial=0;
  while(appliedTrial<s.trials.length){const trial=s.trials[appliedTrial++];if(trial.selected)activateControl(trial.selected);}
  if(phase==='ready')$('checkError').textContent=Math.round(s.checks.reduce((v,r)=>v+r.mean_px,0)/s.checks.length)+' px';
  if(phase==='demo'){
    $('instruction').textContent=s.paused?'Mola veriyoruz.':'“'+names[s.expected]+'” öğesini seç.';
    $('trialInfo').textContent=s.paused?'Hazır olduğunda Devam et düğmesine bas.':`Adım ${s.index+1} / ${s.total_trials} · İstenen öğeye bakışını sabitle.`;
    $('pause').textContent=s.paused?'Devam et':'Duraklat';$('targets').classList.toggle('paused',s.paused);
    $('trackingLabel').textContent=s.paused?'Duraklatıldı':s.tracking?'Bakışın izleniyor':'Gözlerin görünmüyor. Kameraya doğru bak.';
    for(const el of targetEls){const on=el.dataset.control===s.dwell_target&&!s.paused;el.classList.toggle('focused',on);fillFor(el).style.width=(on?s.dwell_progress*100:0)+'%';}
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
 const epoch=preferenceEpoch;
 try{const g=geometry(),key=JSON.stringify(g);if(geometryKey!==key){geometryKey=key;await command('geometry',{geometry:g});}
   const s=await api.snapshot();if(epoch===preferenceEpoch&&!preferenceSaving)render(s);
 }catch(e){notice('Uygulama bağlantısı kesildi. Pencereyi yeniden aç.');for(const el of targetEls)fillFor(el).style.width='0%';}
 finally{busy=false;setTimeout(poll,16);}
}
function fillFor(el){return el.querySelector('.fill')||el.parentElement.querySelector('.fill');}
function activateControl(id){
  const el=document.querySelector('[data-control="'+id+'"]');
  if(id==='title'||id==='search'){el.focus({preventScroll:true});$('webFeedback').textContent='Alan seçildi. İstersen klavyeyle yazabilirsin.';}
  if(id==='overview'||id==='notes'){
    for(const tab of document.querySelectorAll('.web-tab'))tab.classList.toggle('selected',tab===el);
    $('webSectionTitle').textContent=id==='overview'?'Bugünün notları':'Tüm notlar';
  }
  if(id==='reminder')el.setAttribute('aria-checked',String(el.getAttribute('aria-checked')!=='true'));
  if(id==='details'){const open=el.getAttribute('aria-expanded')!=='true';el.setAttribute('aria-expanded',String(open));$('webDetail').classList.toggle('expanded',open);}
  if(id==='clear'){$('webTitle').value='';$('webFeedback').textContent='Başlık temizlendi.';}
  if(id==='save'){const title=$('webTitle').value.trim();$('webNoteTitle').textContent=title||'Yeni not';$('webFeedback').textContent='Not bu deneme alanına eklendi.';}
}
for(const el of targetEls)el.addEventListener('click',async e=>{
  e.preventDefault();
  if(state?.phase==='demo'&&!state.paused){await act('pause');notice('Fareyle deneme: bakış ölçümü duraklatıldı. Devam et ile sürdürebilirsin.');}
  activateControl(el.dataset.control);
});
$('webSearch').addEventListener('input',()=>{
  const match=$('webNoteTitle').textContent.toLocaleLowerCase('tr').includes($('webSearch').value.toLocaleLowerCase('tr'));
  $('webCount').textContent=match?'1 not':'Eşleşme yok';
});
$('cameraStart').onclick=()=>act(['ready','loading'].includes(state?.camera)?'stop_camera':'camera');
const calibrate=()=>act('calibrate',{geometry:geometry()});
for(const id of ['calibrate','recalibrateReady','recalibrateResult'])$(id).onclick=calibrate;
for(const id of ['startDemo','again','practiceStart'])$(id).onclick=()=>act('demo');
for(const id of ['homeDemo','homeReady','homeResult'])$(id).onclick=()=>navigate('home');
for(const el of document.querySelectorAll('[data-page]'))el.onclick=()=>navigate(el.dataset.page);
$('practiceSetup').onclick=()=>navigate('calibration');
for(const el of document.querySelectorAll('[data-theme-choice]'))el.onclick=()=>saveAppearance({theme:el.dataset.themeChoice});
$('motionToggle').onclick=()=>saveAppearance({reduced_motion:!state?.preferences?.reduced_motion});
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
page('home');
appearance({theme:'lavender',reduced_motion:false});
connect();
setTimeout(()=>{if(!api)notice('Uygulama başlatılamadı. Pencereyi kapatıp yeniden aç.');},10000);
