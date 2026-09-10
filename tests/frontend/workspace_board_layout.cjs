const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
  try {
    for(const width of [3022,1440,390]){
      const page=await browser.newPage({viewport:{width,height:1620}});
      for(const [name,preview] of [['home','dashboard-home'],['challenge','challenge-record'],['report','report-forest'],['tools','health-tools'],['together','dashboard-home']]){
        await page.goto(`${process.env.PREVIEW_URL || 'http://127.0.0.1:8023'}/?preview=${preview}`);
        if(name==='together')await page.locator('[data-workspace="together"]').first().click();
        const panel=page.locator(`#workspace-panel-${name}`);
        await panel.waitFor({state:'visible'});
        await page.evaluate(()=>document.getAnimations().forEach(a=>{if(a.effect.getComputedTiming().iterations!==Infinity)a.finish()}));
        const rect=await panel.boundingBox();
        assert.ok(rect.x>=0 && rect.x+rect.width<=width,`${width}/${name}: clipped board`);
        if(width===3022)assert.equal(rect.width,1360);
        if(width===1440)assert.ok(rect.width>1080,`${name}: laptop board narrowed`);
        if(width>=1000){
          const heading=await page.locator('.dashboard-hero').boundingBox();
          assert.ok(Math.abs(heading.width-rect.width)<1);
          assert.ok(Math.abs(heading.x-rect.x)<1);
        }
        if(width===3022 && ['home','report'].includes(name))await page.screenshot({path:`/tmp/workspace-large-${name}.png`,fullPage:true});
      }
      console.log(`${width}: five workspace board sizes and heading alignment passed`);
      await page.close();
    }
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
