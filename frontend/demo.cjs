const { chromium } = require('playwright')
const path = require('path')
const fs = require('fs')

const discover = process.argv.includes('--discover')
const rehearse = process.argv.includes('--rehearse')
const record = !discover && !rehearse
const base = process.env.CASETRACE_BASE_URL || 'http://127.0.0.1:15173'
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw new Error('Use an isolated loopback synthetic installation')
const password = process.env.CASETRACE_TEST_PASSWORD || 'Casetrace-browser-check-2026'
const output = process.env.CASETRACE_DEMO_OUTPUT || path.resolve(__dirname, '../docs/demo.webm')

;(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.CASETRACE_CHROME_CHANNEL || undefined })
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 },
    ...(record ? { recordVideo: { dir: path.resolve(__dirname, 'test-results/demo'), size: { width: 1280, height: 720 } } } : {}) })
  await context.addInitScript(() => {
    document.addEventListener('DOMContentLoaded', () => {
      const cursor = document.createElement('div')
      cursor.id = 'demo-cursor'
      cursor.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5"/></svg>'
      cursor.style.cssText = 'position:fixed;z-index:999999;pointer-events:none;left:0;top:0;filter:drop-shadow(1px 1px 2px #555)'
      document.body.appendChild(cursor)
      document.addEventListener('mousemove', event => { cursor.style.left = event.clientX + 'px'; cursor.style.top = event.clientY + 'px' })
      const bar = document.createElement('div')
      bar.id = 'demo-subtitle'
      bar.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:999998;background:#152d39ed;color:white;padding:14px;text-align:center;font:500 17px system-ui;pointer-events:none'
      document.body.appendChild(bar)
    })
  })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const pause = async (ms = 2500) => { if (record) await page.waitForTimeout(ms) }
  async function stage(text) {
    console.log(text)
    if (discover) console.log(JSON.stringify(await page.locator('input,select,textarea,button').evaluateAll(elements => elements.filter(el => el.offsetParent !== null).map(el => ({ tag: el.tagName, name: el.name, type: el.type, text: el.textContent.trim().slice(0, 45), required: el.required, options: el.tagName === 'SELECT' ? [...el.options].map(option => ({ value: option.value, text: option.text })) : undefined }))), null, 2))
    await page.evaluate(text => { document.getElementById('demo-subtitle').textContent = text }, text)
    await pause(3500)
  }
  async function click(locator, label) {
    await locator.waitFor({ state: 'visible' })
    await locator.scrollIntoViewIfNeeded()
    const box = await locator.boundingBox()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: record ? 12 : 1 })
    await pause(350)
    await locator.click()
    await pause(1600)
    if (rehearse) console.log('Rehearsed:', label)
  }
  async function type(locator, text, label) {
    await click(locator, label)
    await locator.fill('')
    if (record) await locator.pressSequentially(text, { delay: 28 })
    else await locator.fill(text)
  }
  async function screenshot(name) {
    if (!record) return
    await page.evaluate(() => { for (const id of ['demo-cursor', 'demo-subtitle']) document.getElementById(id).style.visibility = 'hidden' })
    await page.screenshot({ path: path.resolve(__dirname, '../docs/screenshots/' + name) })
    await page.evaluate(() => { for (const id of ['demo-cursor', 'demo-subtitle']) document.getElementById(id).style.visibility = 'visible' })
  }
  async function signIn(username) {
    if (!await page.getByLabel('Username').count()) await page.goto(base)
    await page.getByLabel('Username').waitFor()
    await type(page.getByLabel('Username'), username, 'Officer username')
    await type(page.getByLabel('Password', { exact: true }), password, 'Training password')
    await click(page.getByRole('button', { name: 'Sign in', exact: true }), 'Sign in')
    await page.getByRole('heading', { name: 'Case register', exact: true }).waitFor()
  }
  async function openCase() {
    await type(page.getByRole('searchbox'), 'DEMO-FIR-001', 'Case search')
    await click(page.getByRole('button', { name: /^Open/ }).first(), 'Open synthetic case')
    await page.getByText('Loading evidence…', { exact: true }).waitFor({ state: 'hidden' })
  }
  try {
    await page.goto(base)
    await page.getByLabel('Username').waitFor()
    await stage('Step 1 - Sign in to the synthetic training workspace')
    await signIn('demo.io')
    await stage('Step 2 - Find the case and review its original evidence')
    await openCase()
    const scanned = page.getByRole('button').filter({ hasText: 'scanned-hi.png' })
    if (!await scanned.count()) {
      await page.getByLabel('Evidence file').setInputFiles(path.resolve(__dirname, '../data/synthetic/scanned-hi.png'))
      await click(page.getByRole('button', { name: 'Upload evidence', exact: true }), 'Upload synthetic scan')
      await page.getByText('Evidence saved.', { exact: true }).waitFor()
    } else await click(scanned.first(), 'Review scanned evidence')
    await stage('Step 3 - Compare OCR entities with the preserved original')
    await page.locator('.hash').first().scrollIntoViewIfNeeded()
    await pause(6000)
    await click(page.getByRole('button', { name: 'Investigation plan', exact: true }), 'Investigation plan')
    await click(page.getByRole('button', { name: /Generate plan|Refresh plan/ }), 'Generate cited checklist')
    await stage('Step 4 - Review cited checklist steps and saved progress')
    const first = page.locator('ol.steps > li').first()
    if (await first.getByRole('button', { name: 'Mark done', exact: true }).count()) await click(first.getByRole('button', { name: 'Mark done', exact: true }), 'Complete reviewed step')
    await pause(4500)
    await click(page.getByRole('button', { name: 'Money trail', exact: true }), 'Money trail')
    await page.locator('.react-flow__node').first().waitFor()
    await stage('Step 5 - Explore transfers with interactive account controls')
    await click(page.getByRole('button', { name: /zoom in/i }), 'Zoom money trail')
    await click(page.getByRole('button', { name: /fit view/i }), 'Fit the trail')
    await click(page.locator('.react-flow__node').first(), 'Select account')
    await pause(5000)
    await screenshot('money-trail.png')
    await click(page.getByRole('button', { name: 'Deadlines', exact: true }), 'Deadline tracker')
    await stage('Step 6 - Calculate reminders from reviewed dates')
    await page.getByLabel('Confirmed progress-update anchor').fill(new Date().toISOString().slice(0, 10))
    await click(page.getByRole('button', { name: 'Calculate reminders', exact: true }), 'Calculate reminders')
    await pause(4500)
    await click(page.getByRole('button', { name: 'Legal library', exact: true }), 'Legal library')
    await stage('Step 7 - Review a section summary and original source text')
    await type(page.getByLabel('Question', { exact: true }), 'BNSS 94', 'Legal question')
    await click(page.getByRole('button', { name: 'Search sections', exact: true }), 'Search official text')
    await page.getByRole('heading', { name: 'Matching sections', exact: true }).waitFor()
    await page.evaluate(() => window.scrollTo({ top: 350, behavior: 'smooth' }))
    await pause(6500)
    await click(page.getByRole('button', { name: 'Case register', exact: true }), 'Return to case register')
    await openCase()
    await click(page.getByRole('button', { name: 'Notices', exact: true }), 'Draft notice')
    const recipient = 'Synthetic Bank - Walkthrough ' + Date.now()
    await stage('Step 8 - Save an officer-reviewed notice draft')
    await type(page.getByLabel('Recipient', { exact: true }), recipient, 'Recipient')
    await type(page.getByLabel('Case facts', { exact: true }), 'Fictional transfers require a review of the relevant statement period and account records.', 'Officer facts')
    await click(page.getByRole('button', { name: 'Save draft', exact: true }), 'Save draft')
    await page.getByText('Draft saved for officer review.').waitFor()
    await pause(5000)
    await click(page.getByRole('button', { name: 'Sign out', exact: true }), 'Sign out investigating officer')
    await stage('Step 9 - A separate supervisor reviews the notice')
    await signIn('demo.sho')
    await openCase()
    await click(page.getByRole('button', { name: 'Notices', exact: true }), 'Supervisor notice register')
    await click(page.getByRole('button').filter({ hasText: recipient }), 'Open draft for review')
    await pause(4500)
    await click(page.getByRole('button', { name: 'Approve draft', exact: true }), 'Approve draft')
    await click(page.getByRole('button', { name: 'Record simulated send', exact: true }), 'Record simulated training send')
    await stage('Step 10 - Inspect the audit trail and supervisor overview')
    await click(page.getByRole('button', { name: 'Activity', exact: true }), 'Case activity')
    await page.getByRole('cell', { name: 'notice.send_simulated', exact: true }).first().waitFor()
    await pause(5000)
    await click(page.getByRole('button', { name: 'Supervision', exact: true }), 'Supervisor overview')
    await pause(6000)
    if (errors.length) throw new Error(errors.join('; '))
    await screenshot('workspace.png')
    await context.close()
    if (record) { fs.mkdirSync(path.dirname(output), { recursive: true }); await page.video().saveAs(output); console.log('Saved recording:', output) }
    console.log(discover ? 'Discovery completed' : rehearse ? 'Rehearsal passed' : 'Recording completed')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
