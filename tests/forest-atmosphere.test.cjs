const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-atmosphere.js'), 'utf8');
const window = {};
vm.runInNewContext(source, { window, document: {getElementById: () => null} });
const {seoulTime, hourlyEvent, strength, weatherLabel} = window.ForestAtmosphere;
test('Seoul time and lighting boundaries are independent of browser timezone', () => {
  assert.equal(seoulTime(Date.parse('2026-09-03T15:00:00Z')).hour, 0);
  assert.deepEqual([4,5,6,7,17,18,19,20].map(strength), [.42,.3,.16,0,0,.16,.3,.42]);
});
test('one hourly bell; no startup, duplicate, hidden, disabled or wake-up catch-up bell', () => {
  const now = Date.parse('2026-09-03T09:00:01Z'), prev = now - 2000;
  assert.equal(hourlyEvent(prev,now,true,true,-Infinity),true);
  assert.equal(hourlyEvent(null,now,true,true,-Infinity),false);
  assert.equal(hourlyEvent(prev,now,false,true,-Infinity),false);
  assert.equal(hourlyEvent(prev,now,true,false,-Infinity),false);
  assert.equal(hourlyEvent(prev,now,true,true,seoulTime(now).key),false);
  assert.equal(hourlyEvent(now-7200000,now,true,true,-Infinity),false);
  assert.equal(hourlyEvent(now,now+1000,true,true,-Infinity),false);
});
test('weather codes cover rain snow fog thunder and unknown without inventing sunshine', () => {
  for (const [code,label] of [[0,'맑음'],[3,'흐림'],[45,'안개'],[61,'비'],[75,'눈'],[95,'뇌우'],[999,'날씨 정보']]) assert.equal(weatherLabel(code)[1],label);
});
test('live clock dispatches one bell and evening toast, then respects OFF', () => {
  let now = Date.parse('2026-09-03T08:59:59Z'), off = false;
  const dispatched = [], timers = [], handlers = {};
  const icon = {}, title = {}, subtitle = {};
  const toast = {hidden:true, classList:{remove(){},add(){}}, querySelector:s => s === 'strong' ? title : s === 'small' ? subtitle : icon};
  const clock = {};
  const elements = {'forest-clock':clock,'forest-time-toast':toast};
  const document = {hidden:false,getElementById:id=>elements[id],addEventListener(){}};
  class FakeDate extends Date { static now(){return now;} }
  const window = {addEventListener:(name,fn)=>{handlers[name]=fn;},dispatchEvent:event=>dispatched.push(event.type)};
  vm.runInNewContext(source, {window,document,Date:FakeDate,URLSearchParams,location:{search:''},
    localStorage:{getItem:()=>off?'off':'on'}, CustomEvent:class{constructor(type){this.type=type;}},
    setInterval:fn=>timers.push(fn), setTimeout:()=>1, clearTimeout(){},requestAnimationFrame:fn=>fn(),
    AbortController,fetch:()=>new Promise(()=>{}),ResizeObserver:class{observe(){}}
  });
  assert.equal(dispatched.length,0);
  now += 2000; timers[0]();
  assert.deepEqual(dispatched,['forest-hour-chime','forest-time-changed']);
  assert.equal(title.textContent,'저녁이 찾아왔어요');
  assert.equal(toast.hidden,false);
  now += 1000; timers[0]();
  assert.equal(dispatched.length,2);
  off=true; handlers['forest-atmosphere-updated']();
  assert.equal(toast.hidden,true);
  now=Date.parse('2026-09-03T09:59:59Z'); timers[0]();
  now+=2000;timers[0]();
  assert.equal(dispatched.length,2);
});
