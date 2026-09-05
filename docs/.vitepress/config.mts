import { defineConfig, type HeadConfig, type Plugin } from 'vitepress'

const defaultSiteUrl = 'https://peter-gy.github.io/agent-plugins/'

function normalizeBasePath(value: string | undefined): string {
  const name = value?.trim().replace(/^\/+|\/+$/g, '')
  return name ? `/${name}` : ''
}

function normalizeSiteUrl(value: string | undefined): URL {
  const configured = value?.trim() || defaultSiteUrl
  return new URL(`${configured.replace(/\/+$/, '')}/`)
}

const basePath = normalizeBasePath(process.env.BASE_PATH)
const base = basePath ? `${basePath}/` : '/'
const siteUrl = normalizeSiteUrl(process.env.SITE_URL)
const ogImage = new URL('og.png', siteUrl).href
const publicPath = (path: string): string =>
  `${basePath}/${path.replace(/^\/+/, '')}`
const devPort = process.env.PORT ? Number(process.env.PORT) : undefined
const robotsPlugin: Plugin = {
  name: 'agent-plugins-robots',
  apply: 'build',
  generateBundle() {
    this.emitFile({
      type: 'asset',
      fileName: 'robots.txt',
      source: `User-agent: *\nAllow: /\n\nSitemap: ${new URL('sitemap.xml', siteUrl).href}\n`
    })
  }
}

function pageUrl(relativePath: string): string {
  const route = relativePath
    .replace(/(^|\/)index\.md$/, '$1')
    .replace(/\.md$/, '')
  return new URL(route, siteUrl).href
}

export default defineConfig({
  title: 'agent-plugins',
  description:
    'Ship agent instructions and integrations with Python packages.',
  base,
  cleanUrls: true,
  lastUpdated: true,
  lang: 'en-US',
  sitemap: {
    hostname: siteUrl.href
  },
  head: [
    ['meta', { name: 'color-scheme', content: 'light dark' }],
    [
      'link',
      {
        rel: 'icon',
        type: 'image/svg+xml',
        href: publicPath('/favicon.svg')
      }
    ],
    [
      'meta',
      {
        id: 'theme-color-light',
        name: 'theme-color',
        content: '#ffffff',
        media: '(prefers-color-scheme: light)'
      }
    ],
    [
      'meta',
      {
        id: 'theme-color-dark',
        name: 'theme-color',
        content: '#0a0a0a',
        media: '(prefers-color-scheme: dark)'
      }
    ]
  ],
  themeConfig: {
    logo: {
      light: '/brand/agent-plugins-mark-light.svg',
      dark: '/brand/agent-plugins-mark-dark.svg',
      alt: ''
    },
    nav: [
      {
        text: 'Guide',
        link: '/guide/what-is-an-agent-plugin',
        activeMatch: '^/guide/'
      },
      {
        text: 'Integrations',
        link: '/integrations/agent-skills',
        activeMatch: '^/integrations/'
      },
      {
        text: 'Reference',
        link: '/reference/python-api',
        activeMatch: '^/(reference/|troubleshooting$)'
      },
      { text: 'PyPI', link: 'https://pypi.org/project/agent-plugins/' }
    ],
    sidebar: [
      {
        text: 'Start',
        items: [
          {
            text: 'What is an Agent Plugin?',
            link: '/guide/what-is-an-agent-plugin'
          },
          { text: 'Get started', link: '/guide/getting-started' },
          { text: 'How packaging works', link: '/guide/artifact-lifecycle' }
        ]
      },
      {
        text: 'Author and package',
        items: [
          { text: 'Plugin directory', link: '/guide/plugin-directory' },
          { text: 'Build backends', link: '/guide/build-backends' },
          { text: 'Editable installs', link: '/guide/editable-installs' },
          { text: 'Verify a package', link: '/guide/verify-package' }
        ]
      },
      {
        text: 'Integrate',
        items: [
          { text: 'Agent Skills', link: '/integrations/agent-skills' },
          { text: 'MCP servers', link: '/integrations/mcp-servers' },
          {
            text: 'Client extension files',
            link: '/integrations/client-extensions'
          }
        ]
      },
      {
        text: 'Inspect',
        items: [
          { text: 'Installed plugins', link: '/guide/inspect-installed' },
          { text: 'Validation and caching', link: '/guide/validation' }
        ]
      },
      {
        text: 'Reference',
        items: [
          { text: 'Python API', link: '/reference/python-api' },
          { text: 'CLI', link: '/reference/cli' },
          { text: 'pyproject.toml', link: '/reference/pyproject' },
          { text: 'plugin.json', link: '/reference/plugin-json' },
          { text: 'mcp.json', link: '/reference/mcp-json' },
          { text: 'Errors and issues', link: '/reference/errors' },
          { text: 'Troubleshooting', link: '/troubleshooting' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/peter-gy/agent-plugins' }
    ],
    search: {
      provider: 'local'
    },
    outline: {
      level: [2, 3],
      label: 'On this page'
    },
    editLink: {
      pattern:
        'https://github.com/peter-gy/agent-plugins/edit/main/docs/:path',
      text: 'Edit this page on GitHub'
    },
    lastUpdated: {
      text: 'Updated'
    },
    docFooter: {
      prev: 'Previous',
      next: 'Next'
    },
    footer: {
      message: 'Released under the Apache License 2.0.',
      copyright: 'Copyright © 2026 Péter Ferenc Gyarmati'
    }
  },
  transformPageData(pageData) {
    const canonical = pageUrl(pageData.relativePath)
    const title = pageData.relativePath === 'index.md'
      ? 'agent-plugins'
      : pageData.title
      ? `${pageData.title} | agent-plugins`
      : 'agent-plugins'
    const description = pageData.description ||
      'Ship agent instructions and integrations with Python packages.'

    ;((pageData.frontmatter.head ??= []) as HeadConfig[]).push(
      ['link', { rel: 'canonical', href: canonical }],
      ['meta', { property: 'og:type', content: 'website' }],
      ['meta', { property: 'og:locale', content: 'en_US' }],
      ['meta', { property: 'og:site_name', content: 'agent-plugins' }],
      ['meta', { property: 'og:title', content: title }],
      ['meta', { property: 'og:description', content: description }],
      ['meta', { property: 'og:url', content: canonical }],
      ['meta', { property: 'og:image', content: ogImage }],
      ['meta', { property: 'og:image:secure_url', content: ogImage }],
      ['meta', { property: 'og:image:type', content: 'image/png' }],
      ['meta', { property: 'og:image:width', content: '4800' }],
      ['meta', { property: 'og:image:height', content: '2520' }],
      [
        'meta',
        {
          property: 'og:image:alt',
          content: 'Ship Agent Plugins with Python packages.'
        }
      ],
      ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
      ['meta', { name: 'twitter:title', content: title }],
      ['meta', { name: 'twitter:description', content: description }],
      ['meta', { name: 'twitter:image', content: ogImage }],
      [
        'meta',
        {
          name: 'twitter:image:alt',
          content: 'Ship Agent Plugins with Python packages.'
        }
      ]
    )
  },
  vite: {
    plugins: [robotsPlugin],
    server: {
      host: '127.0.0.1',
      port: devPort,
      strictPort: devPort !== undefined
    }
  }
})
