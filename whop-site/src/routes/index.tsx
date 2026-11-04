import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

export const Route = createFileRoute('/')({ component: Home })

const CHECKOUT = {
  free: 'https://whop.com/checkout/plan_t2O2XNWqjsbyu',
  monthly: 'https://whop.com/checkout/plan_uZtBpXSbpCtes',
  quarter: 'https://whop.com/checkout/plan_M2Q5ZFhW6XZXp',
  annual: 'https://whop.com/checkout/plan_jlvUnH4Ixfl1i',
  lifetime: 'https://whop.com/checkout/plan_gQQqGiDD7i7D9',
  rulebook: 'https://whop.com/checkout/plan_kZYCbS1zNSVMo',
  wish: 'https://whop.com/checkout/plan_sPbwrhvIVf1W9',
}

const LOGO = '/bear-head.jpg'
const MASCOT = '/bear.jpg'

// Decorative candles only (no axis, no data claims): a run up, a top, then a fade.
function makeCandles(n: number) {
  let seed = 7
  const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280)
  const out: { o: number; c: number; h: number; l: number }[] = []
  let p = 70
  for (let i = 0; i < n; i++) {
    const drift = i < n * 0.55 ? -1.6 : i < n * 0.65 ? 0 : 1.9
    const o = p
    const c = p + drift + (rnd() - 0.5) * 7
    const h = Math.min(o, c) - rnd() * 4
    const l = Math.max(o, c) + rnd() * 4
    out.push({ o, c, h, l })
    p = c
  }
  return out
}
const CANDLES = makeCandles(46)

function CandleBand() {
  const w = 14
  return (
    <svg className="candles" viewBox={`0 0 ${CANDLES.length * w} 110`} preserveAspectRatio="none" aria-hidden="true">
      {CANDLES.map((k, i) => {
        const up = k.c < k.o
        const x = i * w + w / 2
        const col = up ? '#1db954' : '#cc0000'
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={k.h} y2={k.l} stroke={col} strokeWidth="1.2" />
            <rect x={x - 4} y={Math.min(k.o, k.c)} width="8" height={Math.max(2, Math.abs(k.c - k.o))} fill={col} />
          </g>
        )
      })}
    </svg>
  )
}

const TAPE = ['$SPY', '$QQQ', '$NVDA', '$TSLA', '$AMD', '$INTC', '$RKLB', 'Bearish by default', 'Pattern. Process. Paid.']

function Tape() {
  const row = TAPE.map((t, i) => (
    <span key={i} className="tape-item">
      {t}
      <span className="tape-sep" aria-hidden="true">🌪️</span>
    </span>
  ))
  return (
    <div className="tape" aria-hidden="true">
      <div className="tape-track">
        {row}
        {row}
        {row}
        {row}
      </div>
    </div>
  )
}

function Logo({ size }: { size: number }) {
  return (
    <img
      src={LOGO}
      width={size}
      height={size}
      alt=""
      className="logo-img"
      style={{ width: size, height: size }}
      onError={(e) => {
        ;(e.currentTarget as HTMLImageElement).style.display = 'none'
      }}
    />
  )
}

function Tornado({ size = 30 }: { size?: number }) {
  // Original tornado mark: stacked strokes narrowing to a point.
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <g fill="none" strokeLinecap="round" strokeWidth="3">
        <path d="M3 5h26" stroke="#cc0000" />
        <path d="M6 11h20" stroke="#cc0000" />
        <path d="M10 17h14" stroke="#f2f2f2" />
        <path d="M12 23h8" stroke="#f2f2f2" />
        <path d="M15 29h2" stroke="#f2f2f2" />
      </g>
    </svg>
  )
}

const STEPS = [
  {
    t: 'Plan drops the night before',
    d: "Ticker, trigger, stop. Posted in the Discord before you go to bed, so you're not finding out after the move.",
  },
  {
    t: '9:30 is for one thing',
    d: "Place the order. That's it. No chasing the open, no FOMO entries, and after a big win I sit the open out.",
  },
  {
    t: 'Stops ride the chart',
    d: "No random number. If price closes through a key level against me, I'm out. No hoping, no praying.",
  },
  {
    t: 'Half off at 2x',
    d: 'Hit a double? Half comes off. The rest gets to run.',
  },
  {
    t: "Two L's and I'm done",
    d: "Two losing trades and the day's over. No revenge trades. Not today.",
  },
  {
    t: 'Every alert labeled',
    d: "In the trade? It says so. Not in it? It's labeled an idea. You never have to guess.",
  },
]

const STEP_EMOJI = ['🌙', '🔔', '🛑', '💰', '✋', '🏷️']

const FREE = [
  ['🚨', 'The free alerts channel'],
  ['💬', 'The free Discord'],
  ['📚', 'All the free education I put out'],
  ['🎙️', "The voice channel: jump in during market hours when I'm on and talk trades (and trash) with me"],
  ['🌙', 'Nightly trading sessions. Not every night, but often'],
]

const VIP = [
  ['🧠', 'Full trade reasoning: strike, expiry, stop and target'],
  ['🌙', 'The next day setup, posted the night before'],
  ['📈', 'Real-time chart breakdowns'],
  ['🔍', 'Pattern work: RSI 80/20, MACD divergence, TD Sequential'],
  ['📊', 'Weekly reviews'],
  ['✅', 'Wins and losses posted. Nothing hidden'],
]

const REVIEWS = [
  { who: 'traderafurs', q: "Taz is super dedicated… For options traders his technical strategy is killer and he goes into detail with the thesis behind a lot of the trades." },
  { who: 'jadensamuels', q: "Honestly one of the most intelligent and experienced traders I've ever met. His assistance and knowledge is more helpful than any YouTube video or 'main stream' trader!" },
  { who: 'latebakery', q: "This guy is unreal! … He will guide you to succes" },
  { who: 'lucient', q: 'Hes a chart wizard' },
  { who: 'smoke1foryoboy', q: 'Join Taz he definitely dedicate his time and energy into trading' },
]

const FAQ = [
  {
    q: 'I work all day. Can I still follow?',
    a: "That's exactly why the setup drops the night before. Read it at night, place the order at the open, and get back to your day.",
  },
  {
    q: 'I trade crypto. Why switch to options?',
    a: "Bring the same hunger for big moves. When you buy an option, the most you can lose is what you paid for it, and you know that number before you click buy. The market closes at 4 PM, so you can actually sleep.",
  },
  {
    q: "I'm new to options. Is this over my head?",
    a: 'Every VIP alert comes with the reasoning: why this ticker, why this strike, where the stop is and why. The free side has education too, so start there if you want.',
  },
  {
    q: 'How many alerts do you send?',
    a: 'A few focused setups, not a firehose. If there is no clean setup, there is no alert.',
  },
  {
    q: 'Are the alerts on your real positions?',
    a: "Yes. If I'm not in it, it's labeled an idea. I'm never passing off a trade I didn't take.",
  },
  {
    q: 'Do you trade 0DTE?',
    a: 'Not standalone. I use expirations a week or more out for 1 to 5 day holds, with contracts mostly in the $100 to $200 range.',
  },
  {
    q: 'Can I cancel?',
    a: 'Yes. Memberships run through Whop, and you can cancel from your Whop account.',
  },
  {
    q: 'Can I get a refund?',
    a: "No. All sales are final. That covers memberships and PDFs, because you get access the moment you pay. You can cancel anytime and you won't be billed again. Not sure yet? Start with the 3-day free trial on the monthly plan or the free channel.",
  },
  {
    q: 'Is this financial advice?',
    a: "No. Everything here is for entertainment and education only. I'm not a licensed financial advisor. The alerts are my own trades, shown in real time. Nothing here tells you to buy or sell anything. Options can go to zero. Every trade you take is your decision and your risk.",
  },
]

// NYSE full-day closures, 2026 to 2027.
const HOLIDAYS = new Set([
  '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07', '2026-11-26', '2026-12-25',
  '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18', '2027-07-05', '2027-09-06', '2027-11-25', '2027-12-24',
])
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const isTradingDay = (d: Date) => d.getDay() !== 0 && d.getDay() !== 6 && !HOLIDAYS.has(ymd(d))
const etNow = () => new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }))
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

// Which session the next night-before setup is for, worded for the strip.
function useNextSetupLabel() {
  const [label, setLabel] = useState("Tomorrow's setup drops tonight in VIP.")
  useEffect(() => {
    const et = etNow()
    const next = new Date(et)
    next.setHours(0, 0, 0, 0)
    next.setDate(next.getDate() + 1)
    while (!isTradingDay(next)) next.setDate(next.getDate() + 1)
    const gap = Math.round((next.getTime() - new Date(et.getFullYear(), et.getMonth(), et.getDate()).getTime()) / 8.64e7)
    if (gap === 1) setLabel("Tomorrow's setup drops tonight in VIP.")
    else {
      const eve = new Date(next)
      eve.setDate(eve.getDate() - 1)
      setLabel(`${DAYS[next.getDay()]}'s setup drops ${DAYS[eve.getDay()]} night in VIP.`)
    }
  }, [])
  return label
}

// Live clock to the next 9:30 AM ET open, skipping weekends and NYSE holidays.
function useMarketClock() {
  const [label, setLabel] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const tick = () => {
      const et = etNow()
      const mins = et.getHours() * 60 + et.getMinutes()
      const isOpen = isTradingDay(et) && mins >= 570 && mins < 960
      setOpen(isOpen)
      if (isOpen) return setLabel(null)
      const t = new Date(et)
      t.setHours(9, 30, 0, 0)
      if (et >= t) t.setDate(t.getDate() + 1)
      while (!isTradingDay(t)) t.setDate(t.getDate() + 1)
      const ms = t.getTime() - et.getTime()
      const h = Math.floor(ms / 3.6e6)
      const m = Math.floor((ms % 3.6e6) / 6e4)
      const sec = Math.floor((ms % 6e4) / 1e3)
      setLabel(`${h}h ${String(m).padStart(2, '0')}m ${String(sec).padStart(2, '0')}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])
  return { label, open }
}

function MarketClock() {
  const { label, open } = useMarketClock()
  return (
    <div className="clock" role="status">
      <span className={open ? 'dot dot-live' : 'dot'} aria-hidden="true" />
      {open ? (
        <span><strong>Market's open.</strong> VIP is in the room right now.</span>
      ) : label ? (
        <span>Next open in <strong className="clock-num">{label}</strong>. VIP gets the plan before the bell.</span>
      ) : (
        <span>VIP gets the plan before the bell.</span>
      )}
    </div>
  )
}

function Home() {
  const setupLabel = useNextSetupLabel()
  return (
    <>
      <a className="alert-strip" href={CHECKOUT.monthly}>
        🚨 {setupLabel} <strong>Try it free for 3 days.</strong>
      </a>
      <header className="bar">
        <div className="wrap">
          <a className="mark" href="#top" aria-label="Tazmanian Trader home">
            <Logo size={38} />
            <span className="mark-name">
              Tazmanian <b>Trader</b>
            </span>
          </a>
          <nav aria-label="Main">
            <a className="nl" href="#process">The process</a>
            <a className="nl" href="#inside">A look inside</a>
            <a className="nl" href="#pricing">Pricing</a>
            <a className="nl" href="#pdfs">PDFs</a>
            <a className="btn btn-red btn-sm" href={CHECKOUT.monthly}>Join VIP</a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <CandleBand />
          <div className="wrap hero-grid">
            <div>
              <h1>
                <span>Real trades.</span>
                <span>Real stops.</span>
                <span>No gurus. No BS.</span>
              </h1>
              <p className="lede">
                A Discord where I post my real options trades before I take them. 🌪️ Contracts mostly
                in the $100 to $200 range, so you can actually afford to follow. The full setup drops
                the night before, so you can place it at the open and go live your life. Everyone
                outside the room gets the recap. 🔥
              </p>
              <MarketClock />
              <div className="ctas">
                <a className="btn btn-red btn-big" href={CHECKOUT.monthly}>Get in free for 3 days 🔥</a>
                <a className="btn btn-ghost" href={CHECKOUT.free}>Join the free side</a>
              </div>
              <p className="fine">Then $30/mo. Cancel before the trial ends and you're not charged.</p>
            </div>

            <figure className="hero-visual">
              <img className="mascot" src={MASCOT} alt="Tazmanian Trader bear holding a tablet with a chart" width={924} height={860} />
              <div className="post" role="img" aria-label="Example of the night-before setup post: ticker, contract, trigger, stop and plan">
                <div className="post-head">
                  <span className="avatar"><Logo size={40} /></span>
                  <div>
                    <div className="post-who">Tazmanian Trader <small>9:12 PM</small></div>
                    <div className="post-chan">#tomorrows-setup</div>
                  </div>
                  <span className="tag tag-example">Example</span>
                </div>
                <dl className="post-body">
                  <dt>Ticker</dt><dd>$SPY puts</dd>
                  <dt>Contract</dt><dd>1+ week out, $100 to $200</dd>
                  <dt>Trigger</dt><dd>Rejection at the 10 SMA</dd>
                  <dt>Stop</dt><dd className="stop">Daily close back over the level</dd>
                  <dt>Plan</dt><dd className="tgt">Sell half at 2x, let the rest run</dd>
                </dl>
                <div className="post-foot">
                  <span><strong>9:30 AM:</strong> place this order. Nothing else.</span>
                </div>
              </div>
              <figcaption className="post-cap">The format of the night-before post. This one is an example, not a live alert.</figcaption>
            </figure>
          </div>
        </section>

        <Tape />

        <section className="s" id="process">
          <div className="wrap">
            <h2>The process</h2>
            <p className="intro">
              Same playbook every single day, written down before the bell so the market can't
              talk me out of it. 📋 Win or lose, the rules don't bend. And you don't need to stare
              at charts all day to follow it.
            </p>
            <ol className="steps">
              {STEPS.map((s, i) => (
                <li key={s.t}>
                  <div className="n">{i + 1}<span className="se" aria-hidden="true">{STEP_EMOJI[i]}</span></div>
                  <h3>{s.t}</h3>
                  <p>{s.d}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="s" id="inside">
          <div className="wrap inside">
            <div className="run-wrap">
            <div className="inside-logo"><Logo size={120} /></div>
            <p className="run" aria-label="280 dollars to 5,000 dollars">
              <span className="from">$280 to</span>
              <span className="to">$5K</span>
            </p>
            </div>
            <div>
              <h2 style={{ fontSize: 'clamp(40px,5vw,56px)', marginBottom: 18 }}>A look inside: the $280 Challenge. Twice.</h2>
              <p>
                Run one: a live Robinhood account, $280 to $4,951.97. Then I reset to a fresh $280
                and did it again: $4,096.76 in 3 weeks, 16 trades, 11 green, 5 red. Every trade
                called before entry. Wins posted, losses posted. 📊🔥
              </p>
              <p className="punch">The room saw every entry live. Everyone else found out after. 👀</p>
              <p className="disc">
                Past results from two challenges. Not typical and not a promise of future results.
                Options can go to zero, and losses get posted the same as wins.
              </p>
            </div>
          </div>
        </section>

        <section className="s" id="receipts-shots">
          <div className="wrap">
            <h2>The receipts 🧾</h2>
            <p className="intro">Run one is straight from my Robinhood, start to finish. Run two is the recap cards I posted during the challenge, losses included. Instagram buttons cropped out, numbers untouched.</p>
            <h3 className="run-label">Run 1</h3>
            <div className="shots-run">
              <figure className="shot"><img src="/receipts/start-280.jpg" alt="Robinhood balance showing $280.95" loading="lazy" /><figcaption>Day one: $280.95 in Robinhood</figcaption></figure>
              <div className="shot-arrow" aria-hidden="true">🌪️</div>
              <figure className="shot shot-green"><img src="/receipts/end-4951.jpg" alt="Robinhood balance showing $4,951.97" loading="lazy" /><figcaption>The finish: $4,951.97 in Robinhood</figcaption></figure>
            </div>
            <h3 className="run-label">Run 2: fresh $280 account</h3>
            <div className="shots-three">
              <figure className="shot shot-green"><img src="/receipts/three-weeks.jpg" alt="Recap card: 3 weeks complete, 16 trades, 11 green, 5 red, balance $280 to $4,096.76" loading="lazy" /><figcaption>$280 to $4,096.76 in 3 weeks</figcaption></figure>
              <figure className="shot"><img src="/receipts/week2.jpg" alt="Week 2 recap card with daily breakdown, including a red day of minus $160 on 3/19" loading="lazy" /><figcaption>Week 2: red day included</figcaption></figure>
              <figure className="shot"><img src="/receipts/thursday-green.jpg" alt="Challenge day 14 trade breakdown: 7 puts closed, 5 green and 2 red" loading="lazy" /><figcaption>Day 14: two losing trades, still a green day</figcaption></figure>
            </div>
            <p className="disc shots-disc">Past results from two challenges. Not typical and not a promise of future results.</p>
          </div>
        </section>

        <section className="s" id="reviews">
          <div className="wrap">
            <h2>What members say</h2>
            <div className="reviews">
              {REVIEWS.map((r) => (
                <figure className="review" key={r.who}>
                  <div className="stars" aria-label="5 out of 5 stars">★★★★★</div>
                  <blockquote>"{r.q}"</blockquote>
                  <figcaption>{r.who}</figcaption>
                </figure>
              ))}
            </div>
            <p className="disc shots-disc">Member reviews from Whop, all 5 stars. Results vary. The discipline part is on you.</p>
          </div>
        </section>

        <section className="s" id="vip">
          <div className="wrap">
            <h2>Free or VIP</h2>
            <p className="intro">The free side isn't a teaser. VIP is where you get the whole why behind every trade. 🔥</p>
            <div className="compare">
              <div className="tier">
                <h3>Free</h3>
                <p className="sub">$0. Pull up and see how I trade. 👀</p>
                <ul>
                  {FREE.map(([e, t]) => (
                    <li key={t}><span className="e" aria-hidden="true">{e}</span><span>{t}</span></li>
                  ))}
                </ul>
                <a className="btn btn-ghost" href={CHECKOUT.free}>Join free</a>
              </div>
              <div className="tier vip">
                <h3>VIP ⭐️</h3>
                <p className="sub">$30/mo. First 3 days are free. ⭐️</p>
                <ul>
                  {VIP.map(([e, t]) => (
                    <li key={t}><span className="e" aria-hidden="true">{e}</span><span>{t}</span></li>
                  ))}
                </ul>
                <p className="plus">Plus everything on the free side.</p>
                <a className="btn btn-red" href={CHECKOUT.monthly}>Get in free for 3 days 🔥</a>
              </div>
            </div>
          </div>
        </section>

        <section className="s" id="pricing">
          <div className="wrap">
            <h2>Pricing</h2>
            <p className="intro">Pick your run. Checkout goes through Whop. 💳</p>
            <div className="prices">
              <div className="price main">
                <div className="pn">Monthly</div>
                <div className="pv">$30<small>/mo</small></div>
                <p className="pd">3-day free trial. Cancel from your Whop account.</p>
                <a className="btn btn-red" href={CHECKOUT.monthly}>Get in free for 3 days 🔥</a>
              </div>
              <div className="price">
                <div className="pn">3 months</div>
                <div className="pv">$60</div>
                <p className="pd">Works out to $20/mo. Billed every 3 months.</p>
                <a className="btn btn-ghost" href={CHECKOUT.quarter}>Get 3 months</a>
              </div>
              <div className="price">
                <div className="pn">Annual</div>
                <div className="pv">$200<small>/yr</small></div>
                <p className="pd">Works out to about $16.67/mo. Best value for a full year. Billed once a year.</p>
                <a className="btn btn-ghost" href={CHECKOUT.annual}>Get annual</a>
              </div>
              <div className="price">
                <div className="pn">Lifetime</div>
                <div className="pv">$350</div>
                <p className="pd">Pay once. Never see another bill for VIP.</p>
                <a className="btn btn-ghost" href={CHECKOUT.lifetime}>Get lifetime</a>
              </div>
            </div>
          </div>
        </section>

        <section className="s" id="pdfs">
          <div className="wrap">
            <h2>The PDFs 📕</h2>
            <p className="intro">Not ready for the room yet? Start with the rules. Instant download.</p>
            <div className="books">
              <div className="book">
                <img src="/books/rulebook-cover.jpg" alt="The $280 Rulebook cover" loading="lazy" />
                <div className="book-body">
                  <h3>The $280 Rulebook</h3>
                  <p className="book-price">$18</p>
                  <p>The risk system behind my $280 to $5K run: base stake, picking contracts, stops, half off at 2x, daily limits, a 30-day routine, and the tools to run it. 16 pages.</p>
                  <p className="book-bonus">🎁 Includes Things I Wish I Knew free.</p>
                  <a className="btn btn-red" href={CHECKOUT.rulebook}>Get the rulebook</a>
                </div>
              </div>
              <div className="book">
                <img src="/books/wish-cover.jpg" alt="Things I Wish I Knew cover" loading="lazy" />
                <div className="book-body">
                  <h3>Things I Wish I Knew</h3>
                  <p className="book-price">$2</p>
                  <p>14 lessons from the small-account grind, a few lines each. Sizing, the open, stops, revenge trades, cutting winners early. Read it in 10 minutes.</p>
                  <a className="btn btn-ghost" href={CHECKOUT.wish}>Get it for $2</a>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="s getin-s">
          <div className="wrap">
            <h2>Getting in takes 2 minutes</h2>
            <ol className="getin">
              <li><span className="gi-n">1</span><div><h3>Start the free trial</h3><p>Checkout on Whop. Nothing charged for 3 days.</p></div></li>
              <li><span className="gi-n">2</span><div><h3>Get into the Discord</h3><p>Your VIP access comes through Whop right after checkout.</p></div></li>
              <li><span className="gi-n">3</span><div><h3>Catch tonight's setup</h3><p>Ticker, trigger and stop, waiting for you before the bell.</p></div></li>
            </ol>
            <div className="getin-cta"><a className="btn btn-red btn-big" href={CHECKOUT.monthly}>Get in free for 3 days 🔥</a></div>
          </div>
        </section>

        <section className="s" id="receipts">
          <div className="wrap receipts">
            <div className="rc-img"><img src="/bear.jpg" alt="" width={924} height={860} loading="lazy" /></div>
            <div>
              <h2>Who's behind the bear</h2>
              <p className="intro">
                I'm Tazmanian Trader. Trading since 2017. I was there for the Bitcoin run, COVID
                and the GameStop squeeze. I post the wins and the losses, so you see the real thing,
                not a highlight reel. 🌪️
              </p>
              <p className="intro">Don't take my word for it. Check the receipts:</p>
              <ul className="raw-links">
                <li>𝕏 <a href="https://x.com/tazmaniantrader">x.com/tazmaniantrader</a></li>
                <li>📰 <a href="https://tazmaniantrader.substack.com">tazmaniantrader.substack.com</a></li>
              </ul>
            </div>
          </div>
        </section>

        <section className="s">
          <div className="wrap">
            <h2>Who this is for</h2>
            <div className="fit">
              <div>
                <h3>✅ This is for you if</h3>
                <ul>
                  <li>💼 You've got a job and can't watch charts all day. This is built for you</li>
                  <li>📈 You're running $100 to $25k and want it to actually grow</li>
                  <li>🪙 You trade crypto and want to see what options on stocks can do</li>
                  <li>🌙 You want the plan before the bell, not the recap after</li>
                  <li>🤝 You're done paying gurus who trade size you'll never see</li>
                </ul>
              </div>
              <div>
                <h3>🚫 Skip it if</h3>
                <ul>
                  <li>🎰 You want guaranteed wins. They don't exist</li>
                  <li>📋 You want alerts to copy without ever learning why</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="s">
          <div className="wrap">
            <h2>Questions</h2>
            <div className="faq">
              {FAQ.map((f) => (
                <details key={f.q}>
                  <summary>{f.q}</summary>
                  <p>{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="closer">
          <CandleBand />
          <div className="wrap">
            <div className="closer-logo"><Logo size={96} /></div>
            <p className="sign">
              Pattern. Process. Paid.
              <span className="emo" aria-hidden="true">🌪️🔴</span>
            </p>
            <p className="closer-line">The next setup drops tonight. Be in the room when it does, or read about it tomorrow.</p>
            <div className="ctas">
              <a className="btn btn-red btn-big" href={CHECKOUT.monthly}>Get in free for 3 days 🔥</a>
              <a className="btn btn-ghost" href={CHECKOUT.free}>Join the free side</a>
            </div>
          </div>
        </section>
      </main>

      <div className="sticky-cta">
        <a className="btn btn-red" href={CHECKOUT.monthly}>Get in free for 3 days 🔥</a>
      </div>

      <footer>
        <div className="wrap">
          <p>
            Tazmanian Trader is for entertainment and educational purposes only and is not
            financial advice. Not a licensed financial advisor. Nothing here is a recommendation to
            buy or sell any security. Trading options involves substantial risk of loss, and you can
            lose your entire investment. All sales are final.
          </p>
          <p>
            Past results, including both $280 Challenges, do not guarantee future results. Every trade
            you take is your own decision.
          </p>
          <p className="foot-mark"><Tornado size={18} /> © {new Date().getFullYear()} Tazmanian Trader</p>
        </div>
      </footer>
    </>
  )
}
