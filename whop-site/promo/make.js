const { chromium } = require('playwright');
const FONT = 'file:///home/claude/tazmanian-trader-vip-whop-site/node_modules/@fontsource/bebas-neue/files/bebas-neue-latin-400-normal.woff2';
const base = (inner, w, h) => `<!DOCTYPE html><html><head><style>
@font-face{font-family:'Bebas Neue';src:url('${FONT}') format('woff2')}
*{box-sizing:border-box;margin:0}
body{width:${w}px;height:${h}px;background:#0d0d0d;color:#f2f2f2;font-family:'Inter Display','Inter',sans-serif;position:relative;overflow:hidden}
.glow{position:absolute;right:-200px;top:50%;transform:translateY(-50%);width:${h*1.4}px;height:${h*1.4}px;background:radial-gradient(closest-side,rgba(204,0,0,.38),transparent 70%)}
.brand{font-family:'Bebas Neue';letter-spacing:.04em;color:#f2f2f2}.brand b{color:#cc0000;font-weight:400}
h1{font-family:'Bebas Neue';font-weight:400;line-height:.9}
.red{color:#cc0000}.green{color:#1db954}.muted{color:#bdbdbd}
.candles{position:absolute;left:0;right:0;bottom:0;height:22%;opacity:.25}
</style></head><body><div class="glow"></div>${inner}</body></html>`;
function candles(n){let s='',p=60,seed=7;const r=()=>((seed=(seed*9301+49297)%233280)/233280);for(let i=0;i<n;i++){const d=i<n*.55?-1.4:i<n*.65?0:1.8;const o=p,c=p+d+(r()-.5)*7;const up=c<o;const col=up?'#1db954':'#cc0000';const x=i*14+7;s+=`<line x1="${x}" x2="${x}" y1="${Math.min(o,c)-r()*4}" y2="${Math.max(o,c)+r()*4}" stroke="${col}" stroke-width="1.2"/><rect x="${x-4}" y="${Math.min(o,c)}" width="8" height="${Math.max(2,Math.abs(c-o))}" fill="${col}"/>`;p=c}return `<svg class="candles" viewBox="0 0 ${n*14} 110" preserveAspectRatio="none">${s}</svg>`}
const W=1600,H=900;
const pages = {
 'vip.png': base(`${candles(60)}<img src="bear_fade.png" style="position:absolute;right:20px;bottom:30px;height:820px">
  <div style="position:absolute;left:90px;top:110px;width:820px">
   <div class="brand" style="font-size:44px">Tazmanian <b>Trader</b></div>
   <h1 style="font-size:150px;margin-top:40px">VIP ⭐️</h1>
   <div style="font-size:40px;margin-top:22px;line-height:1.25">Options alerts on my real positions.<br>Setup drops the <span class="red">night before</span>.</div>
   <div class="muted" style="font-size:30px;margin-top:30px">Wins posted. Losses posted. No gurus. No BS.</div>
   <div style="font-family:'Bebas Neue';font-size:46px;margin-top:40px">3 days free <span class="muted">·</span> <span class="green">$30/mo</span></div>
  </div>`, W, H),
 'free.png': base(`${candles(60)}<img src="bear_fade.png" style="position:absolute;right:20px;bottom:30px;height:820px">
  <div style="position:absolute;left:90px;top:130px;width:820px">
   <div class="brand" style="font-size:44px">Tazmanian <b>Trader</b></div>
   <h1 style="font-size:150px;margin-top:40px">The free side</h1>
   <div style="font-size:40px;margin-top:22px;line-height:1.3">🚨 Free alerts &nbsp; 💬 Free Discord<br>🎙️ Voice channel &nbsp; 📚 Free education</div>
   <div class="green" style="font-family:'Bebas Neue';font-size:56px;margin-top:40px">$0</div>
  </div>`, W, H),
 'rulebook.png': base(`<img src="rulebook-cover.jpg" style="position:absolute;right:140px;top:90px;height:720px;border-radius:10px;box-shadow:0 40px 120px -30px rgba(204,0,0,.8)">
  <div style="position:absolute;left:90px;top:150px;width:800px">
   <div class="brand" style="font-size:44px">Tazmanian <b>Trader</b></div>
   <h1 style="font-size:128px;margin-top:36px">The $280 Rulebook</h1>
   <div style="font-size:38px;margin-top:22px;line-height:1.3">The risk system behind my<br>$280 to $5K run.</div>
   <div class="muted" style="font-size:30px;margin-top:26px">🎁 Things I Wish I Knew included</div>
   <div class="green" style="font-family:'Bebas Neue';font-size:70px;margin-top:30px">$18</div>
  </div>`, W, H),
 'wish.png': base(`<img src="wish-cover.jpg" style="position:absolute;right:140px;top:90px;height:720px;border-radius:10px;box-shadow:0 40px 120px -30px rgba(204,0,0,.8)">
  <div style="position:absolute;left:90px;top:170px;width:800px">
   <div class="brand" style="font-size:44px">Tazmanian <b>Trader</b></div>
   <h1 style="font-size:128px;margin-top:36px">Things I Wish I Knew</h1>
   <div style="font-size:38px;margin-top:22px;line-height:1.3">14 lessons from the<br>small-account grind.</div>
   <div class="green" style="font-family:'Bebas Neue';font-size:70px;margin-top:36px">$2</div>
  </div>`, W, H),
};
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:W,height:H}});
for(const [f,html] of Object.entries(pages)){require('fs').writeFileSync('/home/claude/promo/'+f+'.html',html);await p.goto('file:///home/claude/promo/'+f+'.html');await p.waitForTimeout(400);await p.screenshot({path:'/home/claude/promo/'+f});console.log('made',f)}
await b.close()})();
