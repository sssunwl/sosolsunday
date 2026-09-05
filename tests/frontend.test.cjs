const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const api=require('../docs/assets/site.js');
const cal=JSON.parse(read('docs/data/holidays.json'));
const pages=['docs/index.html','docs/destinations/index.html','docs/destinations/city.html','docs/seasonal/index.html','docs/places/index.html'];

test('September 3: the next shared window is December 25–27 with both countries represented',()=>{
  const win=api.nextWindow(cal,'2026-09-03');
  assert.deepEqual({from:win.from,to:win.to,len:win.len},{from:'2026-12-25',to:'2026-12-27',len:3});
  assert.ok(win.why.includes('行憲紀念日'));
  assert.ok(win.why.includes('聖誕節'));
  assert.ok(win.why.includes('聖誕節翌日'));
  assert.equal((api.date(win.from)-api.date('2026-09-03'))/api.DAY,113);
});

test('Every returned day is a shared day off, with no makeup working day',()=>{
  for(const start of ['2026-01-01','2026-02-10','2026-04-01','2026-09-03','2026-12-27','2027-01-01']){
    const win=api.nextWindow(cal,start);
    assert.ok(win); assert.ok(win.len>=3); assert.ok(win.why.length);
    for(let d=api.date(win.from);api.iso(d)<=win.to;d=new Date(+d+api.DAY)){
      for(const c of ['TW','HK']){
        const data=cal.years[d.getUTCFullYear()][c],s=api.iso(d);
        assert.ok(!data.workdays.includes(s));
        assert.ok([0,6].includes(d.getUTCDay())||data.holidays.some(h=>h[0]===s&&h[2]!=='half'));
      }
    }
  }
});

test('Ordinary weekends, half-days, gaps, and makeup workdays never create false windows',()=>{
  const sample={years:{2026:{TW:{holidays:[['2026-09-04','A','half']]},HK:{holidays:[['2026-09-04','B']]}}}};
  assert.equal(api.nextWindow(sample,'2026-09-03'),null);
  sample.years[2026].TW.holidays=[['2026-09-04','A']];
  sample.years[2026].TW.workdays=['2026-09-05'];
  assert.equal(api.nextWindow(sample,'2026-09-03'),null);
  sample.years[2026].TW.workdays=[];
  sample.years[2026].TW.holidays=[['2026-09-07','A']];
  assert.equal(api.nextWindow(sample,'2026-09-03'),null);
  assert.equal(api.nextWindow({years:{2026:{TW:{holidays:[]}}}},'2026-09-03'),null);
  assert.equal(api.nextWindow(null),null);
  assert.equal(api.nextWindow(cal,'2028-01-01'),null);
});

test('Year boundaries use both years of data and return maximal continuous runs',()=>{
  const sample={years:{2026:{TW:{holidays:[['2026-12-31','Eve']]},HK:{holidays:[['2026-12-31','Eve']]}},2027:{TW:{holidays:[['2027-01-01','New year']]},HK:{holidays:[['2027-01-01','New year']]}}}};
  assert.deepEqual(api.nextWindow(sample,'2026-12-30'),{from:'2026-12-31',to:'2027-01-03',len:4,why:['Eve','New year']});
});

test('Taiwan/Hong Kong day boundaries do not depend on UTC midnight or the visitor timezone',()=>{
  assert.equal(api.todayISO(new Date('2026-09-02T16:01:00Z')),'2026-09-03');
  assert.equal(api.todayISO(new Date('2026-09-02T15:59:00Z')),'2026-09-02');
});

test('City holiday reminders return three future holidays in the current year',()=>{
  for(const country of ['JP','KR','TW']){
    const list=api.upcomingHolidays(cal,country,'2026-09-03');
    assert.equal(list.length,3);
    assert.ok(list.every(h=>h.date>='2026-09-03'&&h.date<'2027'&&h.days>=1));
  }
  assert.equal(api.upcomingHolidays(cal,'JP','2026-12-30').length,0);
  assert.equal(api.upcomingHolidays(null,'JP').length,0);
  assert.equal(api.upcomingHolidays(cal,'ZZ').length,0);
});

test('Data fetch handles network, HTTP, and JSON errors without throwing',async()=>{
  const original=global.fetch;
  try{
    for(const stub of [async()=>{throw new Error('offline')},async()=>({ok:false}),async()=>({ok:true,json:async()=>{throw new Error('bad JSON')}})]){
      global.fetch=stub; assert.equal(await api.getJSON('/fixture'),null);
    }
    global.fetch=async()=>({ok:true,json:async()=>({ok:1})});
    assert.deepEqual(await api.getJSON('/fixture'),{ok:1});
  }finally{global.fetch=original;}
});

test('All shared pages carry the stylesheet, navigation, footer, waves, and one main landmark',()=>{
  for(const file of pages){
    const html=read(file);
    assert.match(html,/<link rel="stylesheet" href="(?:\.\.\/)?assets\/sosol\.css">/);
    assert.doesNotMatch(html,/:root|--gold|class="sec-ttl"|class="hdr"/);
    assert.equal((html.match(/<main\b/g)||[]).length,1,file);
    assert.equal((html.match(/<\/main>/g)||[]).length,1,file);
    assert.match(html,/class="site-header"/);assert.match(html,/class="site-footer"/);
    assert.match(html,/class="ocean-waves"/);
    assert.match(html,/aria-expanded="false"/);
    assert.match(html,/id="dropNav"[^>]*hidden/);
    const active=file.includes('seasonal')?'seasonal/':file.includes('destinations')?'destinations/':file.includes('places')?'places/':'./';
    assert.match(html,new RegExp('href="[^"\\n]*'+active.replaceAll('.','\\.')+'" aria-current="page"'));
  }
  const home=read(pages[0]);
  assert.ok(home.indexOf('class="statband"')<home.indexOf('class="calband"'));
  assert.ok(home.indexOf('class="calband"')<home.indexOf('id="deals"'));
  assert.doesNotMatch(home,/class="panel|function showPanel|function goDeal/);
  assert.equal((home.match(/key:'[a-z]+'/g)||[]).length,8);
});

test('Local links, stylesheets and scripts resolve to files under the published docs directory',()=>{
  for(const file of pages){
    const html=read(file).split('<script>')[0];
    for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g)){
      if(/^(?:https?:|data:|#)/.test(m[1]))continue;
      let target=path.resolve(root,path.dirname(file),m[1].split(/[?#]/)[0]);
      if(fs.existsSync(target)&&fs.statSync(target).isDirectory())target=path.join(target,'index.html');
      assert.ok(fs.existsSync(target),file+': '+m[1]);
    }
  }
});

test('Inline page scripts and shared script parse without dependencies',()=>{
  for(const file of pages){
    for(const m of read(file).matchAll(/<script>([\s\S]*?)<\/script>/g))assert.doesNotThrow(()=>new vm.Script(m[1],{filename:file}));
  }
  assert.doesNotThrow(()=>new vm.Script(read('docs/assets/site.js')));
});

test('Both calendar copies agree when the sibling project is available',t=>{
  if(!fs.existsSync(path.join(root,'../SunFamilyTrip/calendar.html')))return t.skip('Standalone checkout: sibling project is not present');
  assert.equal(read('docs/calendar/index.html'),read('../SunFamilyTrip/calendar.html'));
});

// A tiny rendering harness: exercises page logic against the existing JSON shapes
// and failed fetches without introducing a package dependency or changing data.
async function renderPage(file,lookup,search=''){
  const nodes=new Map();
  const node=()=>({innerHTML:'',textContent:'',className:'',hidden:false,options:[],
    classList:{add(){},remove(){},toggle(){}},querySelectorAll:()=>[],appendChild(){},setAttribute(){}});
  const document={title:'',getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},
    querySelectorAll:()=>[],querySelector:()=>node(),createElement:()=>node()};
  const context=vm.createContext({document,location:{search},URLSearchParams,Date,console,
    SoSol:{...api,todayISO:()=> '2026-09-03',getJSON:async p=>lookup(p),updateStatus(){}}});
  const script=read(file).match(/<script>([\s\S]*?)<\/script>/)[1];
  await vm.runInContext(script,context);
  return nodes;
}

test('Landing renders live data, six calendar months, and the holiday banner',async()=>{
  const lookup=p=>JSON.parse(read('docs/'+p.replace(/^\.\//,'')));
  const nodes=await renderPage('docs/index.html',lookup);
  assert.equal((nodes.get('cityGrid').innerHTML.match(/class="dcard"/g)||[]).length,8);
  assert.match(nodes.get('nextbox').innerHTML,/12\/25\(五\) – 12\/27\(日\)/);
  assert.equal((nodes.get('priceTable').innerHTML.match(/scope="col"/g)||[]).length,7);
  assert.equal((nodes.get('heroList').innerHTML.match(/hero-price-row/g)||[]).length,4);
  assert.ok((nodes.get('eventList').innerHTML.match(/class="ecard /g)||[]).length<=6);
  assert.match(nodes.get('hotelList').innerHTML,/HK\$/);
});

test('Landing and seasonal views replace loading content when every fetch fails',async()=>{
  const home=await renderPage('docs/index.html',()=>null);
  for(const id of ['destRow','heroList','priceTable','hotelList','eventList','nextbox']){
    assert.ok(home.get(id).innerHTML.length,id);assert.doesNotMatch(home.get(id).innerHTML,/載入中|計算中/,id);
  }
  const seasonal=await renderPage('docs/seasonal/index.html',()=>null);
  assert.match(seasonal.get('events-list').innerHTML,/活動資料暫時無法載入/);
});

test('All city JSON shapes render; invalid city keys cause no data request',async()=>{
  for(const key of ['okinawa','ishigaki','miyakojima','tokyo','fukuoka','seoul','busan','taipei']){
    const nodes=await renderPage('docs/destinations/city.html',p=>JSON.parse(read(path.posix.join('docs/destinations',p))),'?key='+key);
    assert.equal((nodes.get('holiday-list').innerHTML.match(/class="hrow-card holiday-row"/g)||[]).length,3,key);
    assert.ok(nodes.get('highlights').innerHTML.length,key);
  }
  for(const key of ['../../secret','__proto__','toString','']){
    const missing=await renderPage('docs/destinations/city.html',()=>{throw new Error('Unexpected fetch');},'?key='+key);
    assert.match(missing.get('main').innerHTML,/找不到這個城市/);
  }
});
