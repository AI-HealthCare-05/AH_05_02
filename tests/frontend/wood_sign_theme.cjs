const assert = require('node:assert/strict');
const {chromium} = require('playwright');
function luminance(hex) {
  const rgb=hex.match(/[0-9a-f]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
  return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)}
const cases = [
  ['signup','auth=signup','.signup-house-board'],
  ['eligibility','preview=eligibility-forest','.eligibility-forest-board'],
  ['health','preview=health-room','.health-room-board'],
  ['review','preview=health-room&panel=review','#health-review-panel'],
  ['analysis','preview=analysis-status&status=running','.prediction-status-card'],
  ['results','preview=results','.risk-forecast-panel'],
  ['challenge','preview=challenge-forest','#challenge-form'],
  ['record','preview=challenge-record','#workspace-panel-challenge'],
  ['report','preview=report-forest','#workspace-panel-report'],
  ['tools','preview=health-tools','#workspace-panel-tools'],
  ['home','preview=dashboard-home','.dashboard-hero'],
];
(async()=>{
  const b=await chromium.launch({executablePath:process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
  try {
    for(const width of [1440,390]) for(const [name,query,selector] of cases){
      const p=await b.newPage({viewport:{width,height:1000}});
      const errors=[]; p.on('pageerror',e=>errors.push(e.message));
      await p.goto(`${process.env.PREVIEW_URL || 'http://127.0.0.1:8023'}/?${query}`);
      await p.locator(selector).waitFor({state:'visible'});
      await p.evaluate(()=>document.getAnimations().forEach(animation=>{if(animation.effect.getComputedTiming().iterations!==Infinity)animation.finish()}));
      const image=await p.locator(selector).evaluate(el=>getComputedStyle(el).backgroundImage);
      assert.ok(image.includes(name==='home'?'200, 137, 79':'150, 97, 58'),`${name}: common sign finish missing`);
      const colors=await p.evaluate(()=>{const s=getComputedStyle(document.documentElement);return ['--sign-title-ink','--sign-body-ink','--sign-muted-ink','--sign-light-ink'].map(k=>s.getPropertyValue(k).trim())});
      for(const [ink,paper] of [[colors[0],'#ad6f3c'],[colors[1],'#f7e6c4'],[colors[2],'#f7e6c4'],[colors[3],'#9b6742']])assert.ok(contrast(ink,paper)>=4.5,`${name}: insufficient palette contrast`);
      const shadows=await p.locator('.signup-house-heading h2:visible,.eligibility-forest-heading h2:visible,.health-room-heading h2:visible,#health-review-title:visible,#result-stage:visible,#factors-title:visible,#challenge-title:visible,.dashboard-hero h2:visible').evaluateAll(elements=>elements.map(el=>getComputedStyle(el).textShadow));
      assert.ok(shadows.every(shadow=>shadow==='none'),`${name}: title shadow still present`);
      assert.deepEqual(errors,[],`${name}: browser errors`);
      if(width===1440) await p.screenshot({path:`/tmp/wood-theme-${name}.png`,fullPage:true});
      console.log(`${width} ${name}: shared finish, visible screen, no JS errors`);
      if(name==='home') {
        await p.locator('[data-workspace="together"]').first().click();
        await p.locator('#workspace-panel-together').waitFor({state:'visible'});
        await p.evaluate(()=>document.getAnimations().forEach(animation=>{if(animation.effect.getComputedTiming().iterations!==Infinity)animation.finish()}));
        assert.ok((await p.locator('#workspace-panel-together').evaluate(el=>getComputedStyle(el).backgroundImage)).includes('150, 97, 58'));
        if(width===1440) await p.screenshot({path:'/tmp/wood-theme-together.png',fullPage:true});
      }
      await p.close();
    }
  } finally {await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
