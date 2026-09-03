/* Shared navigation, data states, and holiday helpers. No data is rewritten here. */
(function(root){
  'use strict';
  const DAY=86400000;
  const iso=d=>d.toISOString().slice(0,10);
  const date=s=>new Date(s+'T00:00:00Z');
  const todayISO=(now=new Date())=>new Intl.DateTimeFormat('en-CA',{
    timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'
  }).format(now);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function nextWindow(cal,today=todayISO()){
    if(!cal?.years)return null;
    const countries=['TW','HK'], index={}, work={};
    for(const c of countries){
      index[c]={}; work[c]=new Set();
      for(const y of Object.values(cal.years)){
        for(const h of y[c]?.holidays||[])if(h[2]!=='half')index[c][h[0]]=h[1];
        for(const d of y[c]?.workdays||[])work[c].add(d);
      }
    }
    // Scan continuous shared days off; never infer holidays in an uncovered year.
    const end=Math.max(...Object.keys(cal.years).map(Number));
    let run=[];
    const result=()=>{
      if(run.length<3)return null;
      const why=[...new Set(run.flatMap(s=>countries.map(c=>index[c][s])).filter(Boolean))];
      return why.length?{from:run[0],to:run.at(-1),len:run.length,why}:null;
    };
    for(let d=date(today);d.getUTCFullYear()<=end;d=new Date(+d+DAY)){
      const s=iso(d),year=cal.years[d.getUTCFullYear()];
      const off=c=>year?.[c]&&!work[c].has(s)&&(index[c][s]||[0,6].includes(d.getUTCDay()));
      if(countries.every(off))run.push(s);
      else{const found=result();if(found)return found;run=[];}
    }
    return result();
  }
  function upcomingHolidays(cal,country,today=todayISO()){
    const data=cal?.years?.[today.slice(0,4)]?.[country];
    if(!data)return [];
    const work=new Set(data.workdays||[]);
    const holidays=(data.holidays||[]).filter(h=>h[2]!=='half'&&!work.has(h[0]));
    const days=new Set(holidays.map(h=>h[0]));
    const off=s=>s.startsWith(today.slice(0,4))&&!work.has(s)&&(days.has(s)||[0,6].includes(date(s).getUTCDay()));
    return holidays.filter(h=>h[0]>=today).sort((a,b)=>a[0].localeCompare(b[0])).slice(0,3).map(h=>{
      let from=date(h[0]),to=date(h[0]);
      while(off(iso(new Date(+from-DAY))))from=new Date(+from-DAY);
      while(off(iso(new Date(+to+DAY))))to=new Date(+to+DAY);
      return {date:h[0],name:h[1],estimated:h[2]==='est'||data.status!=='official',days:Math.round((to-from)/DAY)+1};
    });
  }
  async function getJSON(path){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
    try{const r=await fetch(path+'?v='+Date.now(),{signal:controller.signal});return r.ok?await r.json():null;}
    catch{return null;}finally{clearTimeout(timeout);}
  }
  function updateStatus(...datasets){
    const dates=[...new Set(datasets.map(d=>d?.updated_at).filter(Boolean))].sort();
    const stamp=dates[0],stale=!stamp||stamp.slice(0,10)<todayISO();
    const pill=document.getElementById('updPill');
    if(pill){
      pill.classList.toggle('stale',stale);
      pill.innerHTML='<span class="dot"></span>'+esc(stamp?(stale?'資料 '+stamp.slice(5,10).replace('-','/'):'今日更新'):'資料未載入');
      pill.title=stamp?'最早報價更新：'+stamp:'無法取得價格資料';
    }
    const foot=document.getElementById('footUpd');
    if(foot)foot.textContent=stamp?'機酒數據更新：'+dates.join(' / '):'價格資料暫時無法取得，請稍後再試';
    const notice=document.getElementById('dataNotice');
    if(notice){
      notice.hidden=!stale;
      notice.textContent=stamp?'目前顯示 '+stamp+' 的最近一期報價，非今日即時價格；日期與實際售價請以訂購平台為準。':'價格資料暫時無法取得，目的地指南與假期年曆仍可瀏覽。';
    }
  }
  const api={DAY,iso,date,todayISO,esc,nextWindow,upcomingHolidays,getJSON,updateStatus};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.SoSol=api;
  if(typeof document==='undefined')return;
  const header=document.getElementById('hdr'),menu=document.getElementById('menuBtn'),nav=document.getElementById('dropNav');
  if(menu&&nav){
    const close=()=>{nav.hidden=true;menu.setAttribute('aria-expanded','false');};
    menu.addEventListener('click',()=>{nav.hidden=!nav.hidden;menu.setAttribute('aria-expanded',String(!nav.hidden));});
    nav.addEventListener('click',e=>{if(e.target.closest('a'))close();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!nav.hidden){close();menu.focus();}});
    document.addEventListener('click',e=>{if(!header.contains(e.target))close();});
    matchMedia('(min-width:861px)').addEventListener('change',e=>{if(e.matches)close();});
  }
  if(header){
    const update=()=>header.classList.toggle('stuck',scrollY>10);
    addEventListener('scroll',update,{passive:true});update();
  }
})(globalThis);
