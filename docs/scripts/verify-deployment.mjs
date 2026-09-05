import { setTimeout as delay } from 'node:timers/promises'

const siteUrl = new URL(process.argv[2])
const siteRoot = siteUrl.pathname.replace(/\/+$/, '')
const attempts = 60
const retryDelay = 10_000

function collectReferences(html) {
  const references = new Set()

  for (const match of html.matchAll(/\b(?:href|src)=["']([^"'#]+)["']/g)) {
    const reference = new URL(match[1], siteUrl)

    if (reference.origin !== siteUrl.origin) continue

    const insideSite =
      !siteRoot ||
      reference.pathname === siteRoot ||
      reference.pathname.startsWith(`${siteRoot}/`)

    if (!insideSite) {
      throw new Error(`Reference escapes the Pages base path: ${reference.href}`)
    }

    references.add(reference.href)
  }

  return [...references]
}

async function fetchPage(url) {
  const response = await fetch(url, {
    headers: {
      'accept-encoding': 'gzip, deflate, br',
      'user-agent': 'agent-plugins-deployment-check'
    }
  })

  if (!response.ok) {
    await response.body?.cancel()
    throw new Error(`GET ${url} returned ${response.status}`)
  }

  return response
}

async function verifyDeployment() {
  const page = await fetchPage(siteUrl)
  const contentType = page.headers.get('content-type') ?? ''

  if (!contentType.startsWith('text/html')) {
    await page.body?.cancel()
    throw new Error(`GET ${siteUrl.href} returned ${contentType || 'no content type'}`)
  }

  const references = collectReferences(await page.text())

  if (references.length === 0) {
    throw new Error(`GET ${siteUrl.href} returned no page references`)
  }

  await Promise.all(
    references.map(async (reference) => {
      const response = await fetchPage(reference)
      await response.body?.cancel()
    })
  )

  return references.length
}

for (let attempt = 1; attempt <= attempts; attempt += 1) {
  try {
    const referenceCount = await verifyDeployment()
    console.log(
      `Verified ${siteUrl.href} and ${referenceCount} same-origin references.`
    )
    break
  } catch (error) {
    if (attempt === attempts) throw error

    console.warn(
      `Deployment check ${attempt}/${attempts} failed: ${error.message}`
    )
    await delay(retryDelay)
  }
}
