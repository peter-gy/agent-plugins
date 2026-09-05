import { readFile, stat } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const packageRoot = dirname(fileURLToPath(new URL('../package.json', import.meta.url)))
const outputRoot = join(packageRoot, '.vitepress', 'dist')
const baseName = process.env.BASE_PATH?.trim().replace(/^\/+|\/+$/g, '')
const basePath = baseName ? `/${baseName}` : ''
const deployedSiteUrl = new URL(
  `${(process.env.SITE_URL?.trim() || 'https://peter-gy.github.io/agent-plugins').replace(/\/+$/, '')}/`
)
const publicPath = (path) => `${basePath}/${path.replace(/^\/+/, '')}`
const failures = []

const check = (condition, message) => {
  if (!condition) failures.push(message)
}

const isFile = async (path) => {
  try {
    return (await stat(path)).isFile()
  } catch {
    return false
  }
}

const indexPath = join(outputRoot, 'index.html')
check(await isFile(indexPath), 'Missing built home page')
check(await isFile(join(outputRoot, 'favicon.svg')), 'Missing built favicon')
check(await isFile(join(outputRoot, 'og.png')), 'Missing built Open Graph image')
check(await isFile(join(outputRoot, 'robots.txt')), 'Missing built robots file')
check(await isFile(join(outputRoot, 'llms.txt')), 'Missing generated llms.txt')
check(
  await isFile(join(outputRoot, 'llms-full.txt')),
  'Missing generated llms-full.txt'
)

if (await isFile(indexPath)) {
  const index = await readFile(indexPath, 'utf8')
  check(
    index.includes(`href="${publicPath('/assets/')}`),
    `Missing stylesheet under ${publicPath('/assets/')}`
  )
  check(
    index.includes(`src="${publicPath('/assets/')}`),
    `Missing script under ${publicPath('/assets/')}`
  )
  check(
    index.includes(`href="${publicPath('/favicon.svg')}"`),
    `Missing favicon reference: ${publicPath('/favicon.svg')}`
  )
  check(
    index.includes(`href="${publicPath('/guide/getting-started')}"`),
    `Missing base-aware guide link: ${publicPath('/guide/getting-started')}`
  )
  check(index.includes('property="og:title"'), 'Missing Open Graph title')
  check(index.includes('property="og:description"'), 'Missing Open Graph description')
  check(index.includes('property="og:image"'), 'Missing Open Graph image')
  check(index.includes('content="4800"'), 'Missing Open Graph image width')
  check(index.includes('content="2520"'), 'Missing Open Graph image height')

  const siteUrl = process.env.SITE_URL?.trim().replace(/\/+$/, '')
  if (siteUrl) {
    const sitePathName = new URL(siteUrl).pathname.replace(/\/+$/, '')
    check(
      sitePathName === basePath,
      `SITE_URL path ${sitePathName || '/'} does not match BASE_PATH ${basePath || '/'}`
    )
    check(
      index.includes(`href="${siteUrl}/"`),
      `Missing canonical site URL: ${siteUrl}/`
    )
    check(
      index.includes(`content="${siteUrl}/og.png"`),
      `Missing deployed Open Graph image URL: ${siteUrl}/og.png`
    )
    const robotsPath = join(outputRoot, 'robots.txt')
    if (await isFile(robotsPath)) {
      const robots = await readFile(robotsPath, 'utf8')
      check(
        robots.includes(`Sitemap: ${siteUrl}/sitemap.xml`),
        `Missing deployed sitemap URL in robots.txt: ${siteUrl}/sitemap.xml`
      )
    }
  }
}

const llmsPath = join(outputRoot, 'llms.txt')
const llmsFullPath = join(outputRoot, 'llms-full.txt')
if (await isFile(llmsPath)) {
  const llms = await readFile(llmsPath, 'utf8')
  check(
    llms.includes(`${deployedSiteUrl.href}guide/getting-started.md`),
    'llms.txt is missing the getting-started Markdown URL'
  )
  check(
    llms.includes(`${deployedSiteUrl.href}reference/python-api.md`),
    'llms.txt is missing the Python API Markdown URL'
  )
}
if (await isFile(llmsFullPath)) {
  const llmsFull = await readFile(llmsFullPath, 'utf8')
  check(
    llmsFull.includes(`url: ${deployedSiteUrl.href}`),
    'llms-full.txt is missing canonical page URLs'
  )
  check(
    llmsFull.includes('# Python API reference'),
    'llms-full.txt is missing the Python API content'
  )
}

if (failures.length > 0) {
  console.error(
    `Documentation build verification failed:\n${failures
      .map((failure) => `- ${failure}`)
      .join('\n')}`
  )
  process.exitCode = 1
} else {
  console.log(`Verified documentation build at base path ${basePath || '/'}.`)
}
