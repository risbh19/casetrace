import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

const password = process.env.CASETRACE_TEST_PASSWORD || 'Casetrace-browser-check-2026'

async function signIn(page: Page, username: string, value = password) {
  await page.goto('/')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password', { exact: true }).fill(value)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
}

async function openCase(page: Page) {
  await expect(page.getByRole('heading', { name: 'Case register', exact: true })).toBeVisible()
  await page.getByRole('searchbox').fill('DEMO-FIR-001')
  await page.getByRole('button', { name: /^Open/ }).first().click()
}

test('officer evidence, checklist, interactive graph and reminder clearing', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await signIn(page, 'demo.io')
  await openCase(page)
  const content = Buffer.from(`Synthetic browser evidence ${Date.now()}; account 9000012345, INR 19500.22`)
  await page.getByLabel('Evidence file').setInputFiles({ name: 'browser-evidence.txt', mimeType: 'text/plain', buffer: content })
  await page.getByRole('button', { name: 'Upload evidence', exact: true }).click()
  await expect(page.getByText('Evidence saved.', { exact: true })).toBeVisible()
  await expect(page.getByText('9000012345', { exact: false }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Investigation plan', exact: true }).click()
  await page.getByRole('button', { name: /Generate plan|Refresh plan/ }).click()
  await expect(page.getByText('Review the case intake', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Money trail', exact: true }).click()
  await expect(page.locator('.react-flow__node').first()).toBeVisible()
  await page.getByRole('button', { name: /zoom in/i }).click()
  await page.locator('.react-flow__node').first().click()
  await expect(page.getByText(/^Selected account:/)).toBeVisible()
  await page.getByRole('button', { name: 'Deadlines', exact: true }).click()
  await page.getByLabel('Custody date').fill(new Date().toISOString().slice(0, 10))
  await page.getByLabel('Reviewed offence band').selectOption('other_offence')
  await page.getByLabel('Officer-set report target').fill(new Date(Date.now() + 30 * 86400_000).toISOString().slice(0, 10))
  await page.getByRole('button', { name: 'Calculate reminders' }).click()
  await expect(page.getByText('Custody limit review', { exact: true })).toBeVisible()
  await page.getByLabel('Custody date').fill('')
  await page.getByLabel('Reviewed offence band').selectOption('')
  await page.getByLabel('Officer-set report target').fill('')
  await page.getByRole('button', { name: 'Calculate reminders' }).click()
  await expect(page.getByText('Custody limit review', { exact: true })).toHaveCount(0)
  expect(errors).toEqual([])
})

test('separate supervisor approval, simulated dispatch and audit trail', async ({ page }) => {
  await signIn(page, 'demo.io')
  await openCase(page)
  await page.getByRole('button', { name: 'Notices', exact: true }).click()
  const recipient = `Synthetic Bank ${Date.now()}`
  await page.getByLabel('Recipient', { exact: true }).fill(recipient)
  await page.getByLabel('Case facts').fill('Fictional transfer for the recorded workflow demonstration.')
  await page.getByRole('button', { name: 'Save draft', exact: true }).click()
  await expect(page.getByText('Draft saved for officer review.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Approve draft' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, 'demo.sho')
  await openCase(page)
  await page.getByRole('button', { name: 'Notices', exact: true }).click()
  await page.getByRole('button').filter({ hasText: recipient }).click()
  await page.getByRole('button', { name: 'Approve draft', exact: true }).click()
  await page.getByRole('button', { name: 'Record simulated send', exact: true }).click()
  await expect(page.getByText('Simulated send recorded.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Activity', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'notice.send_simulated', exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Supervision', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Supervision', exact: true })).toBeVisible()
})

test('station administrator provisions an officer with forced password change', async ({ page }) => {
  await signIn(page, 'demo.sp')
  await page.getByRole('button', { name: 'Officer accounts', exact: true }).click()
  const username = `browser.${Date.now()}`
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByLabel('Name', { exact: true }).fill('Synthetic browser officer')
  await page.getByLabel('Temporary password', { exact: true }).fill('Temporary-browser-passphrase')
  await page.getByRole('button', { name: 'Add officer', exact: true }).click()
  await expect(page.getByRole('heading').filter({ hasText: username })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, username, 'Temporary-browser-passphrase')
  await expect(page.getByRole('heading', { name: 'Account security', exact: true })).toBeVisible()
  await page.getByLabel('Current password', { exact: true }).fill('Temporary-browser-passphrase')
  await page.getByLabel('New password', { exact: true }).fill('Individual-browser-passphrase')
  await page.getByLabel('Confirm new password', { exact: true }).fill('Individual-browser-passphrase')
  await page.getByRole('button', { name: 'Change password', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Case register', exact: true })).toBeVisible()
})

test('mobile workspace has no horizontal page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await signIn(page, 'demo.io')
  await openCase(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
