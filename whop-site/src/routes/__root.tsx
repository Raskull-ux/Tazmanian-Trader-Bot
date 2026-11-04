import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'

import appCss from '../styles.css?url'

const DESCRIPTION =
  'Small-account options alerts on real positions. The next day setup gets posted the night before. Wins and losses posted. No gurus. No BS.'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'Tazmanian Trader VIP | Small-account options alerts' },
      { name: 'description', content: DESCRIPTION },
      { name: 'theme-color', content: '#0d0d0d' },
      { property: 'og:title', content: 'Tazmanian Trader VIP' },
      { property: 'og:description', content: DESCRIPTION },
      { property: 'og:type', content: 'website' },
      { property: 'og:image', content: 'https://tazmanian-trader-vip.whop.site/bear.jpg' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      { rel: 'icon', type: 'image/png', href: '/favicon.png' },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  )
}
