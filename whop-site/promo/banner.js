const { chromium } = require('playwright');
const FONT='file:///home/claude/tazmanian-trader-vip-whop-site/node_modules/@fontsource/bebas-neue/files/bebas-neue-latin-400-normal.woff2';
const html=`<!DOCTYPE html><html><head><style>
@font-face{font-family:'Bebas Neue';src:url('${FONT}') format('woff2')}
*{margin:0;box-sizing:border-box}
body{width:1920px;height:1080px;background:#0d0d0d;color:#f2f2f2;font-family:'Inter Display','Inter',sans-serif;position:relative;overflow:hidden}
.glow{position:absolute;right:-250px;top:50%;transform:translateY(-50%);width:1500px;height:1500px;background:radial-gradient(closest-side,rgba(204,0,0,.4),transparent 70%)}
.bear{position:absolute;right:40px;bottom:40px;height:1000px}
.t{position:absolute;left:120px;top:130px;width:1000px}
.brand{font-family:'Bebas Neue';font-size:56px;letter-spacing:.04em}.brand b{color:#cc0000;font-weight:400}
h1{font-family:'Bebas Neue';font-weight:400;font-size:170px;line-height:.88;margin-top:40px}
.sub{font-size:48px;line-height:1.25;margin-top:34px}.red{color:#cc0000}
.pills{display:flex;gap:18px;margin-top:44px;flex-wrap:wrap}
.pill{font-size:32px;font-weight:600;padding:14px 26px;border-radius:999px;border:2px solid #333;background:#151515}
.pill.g{border-color:#1db954;color:#1db954}
.strip{position:absolute;left:0;right:0;bottom:0;height:16px;background:#cc0000}
</style></head><body><div class="glow"></div><img class="bear" src="bear_fade.png">
<div class="t"><div class="brand">Tazmanian <b>Trader</b></div>
<h1>Real trades.<br>Real stops.<br>No BS.</h1>
<div class="sub">Options alerts on real positions.<br>Setup drops the <span class="red">night before</span>.</div>
<div class="pills"><span class="pill g">🚨 Free alerts</span><span class="pill">🎙️ Voice channel</span><span class="pill">⭐ VIP room</span></div></div>
<div class="strip"></div></body></html>`;
(async()=>{require('fs').writeFileSync('/home/claude/promo/banner.html',html);const b=await chromium.launch();
const p=await b.newPage({viewport:{width:1920,height:1080}});await p.goto('file:///home/claude/promo/banner.html');await p.waitForTimeout(400);
await p.screenshot({path:'/home/claude/promo/tazmanian-discord-banner-1920x1080.png'});
const q=await b.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:0.5});await q.goto('file:///home/claude/promo/banner.html');await q.waitForTimeout(400);
await q.screenshot({path:'/home/claude/promo/tazmanian-discord-banner-960x540.png'});await b.close();console.log('ok')})();
