const assert = require('node:assert/strict');
const {chromium} = require('playwright');
(async()=>{
  const b=await chromium.launch({executablePath:process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
  try {
    for(const [width,height] of [[3022,1588],[1440,1000],[390,844]]) {
      const page=await b.newPage({viewport:{width,height}});
      for(const panel of ['metrics','vitals','drinking','habits','activity','family','nutrition','socioeconomic','review']){
        await page.goto(`${process.env.PREVIEW_URL || 'http://127.0.0.1:8023'}/?preview=health-room&panel=${panel}`);
        await page.locator('.health-room-board').waitFor({state:'visible'});
        await page.evaluate(()=>document.getAnimations().forEach(a=>{if(a.effect.getComputedTiming().iterations!==Infinity)a.finish()}));
        const rect=await page.locator('.health-room-board').boundingBox();
        assert.ok(rect.x>=0 && rect.x+rect.width<=width,`${width}/${panel}: board clips`);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
        if(width===3022 && panel!=='review'){
          assert.ok(rect.width>=1590,`${panel}: board did not expand`);
          assert.ok(rect.height>=height-360);
        }
        if(panel==='drinking' && width===3022)await page.screenshot({path:'/tmp/health-board-large.png',fullPage:true});
        if(panel==='review' && width===3022){
          const review=await page.locator('#health-review-panel').boundingBox();
          assert.ok(review.width>=1470);
          assert.ok(review.height>=height-140);
          assert.equal(await page.locator('#review-health').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),3);
          assert.equal(await page.locator('#review-lifestyle').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),3);
          assert.equal(await page.locator('#review-detail-health').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),4);
          await page.screenshot({path:'/tmp/review-board-large.png',fullPage:true});
        }
      }
      await page.close();
      console.log(`${width}: eight health-entry panels and review fit the viewport`);
    }
  } finally {await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
