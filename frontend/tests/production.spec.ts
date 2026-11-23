import { test, expect } from '@playwright/test'

const url = process.env.CASETRACE_PRODUCTION_TEST_URL
test.skip(!url, 'Requires the isolated production verification stack')
test.use({ baseURL: url, ignoreHTTPSErrors: true })

test('production onboarding, evidence, approval and recorded external dispatch', async ({ page }) => {
  if (!url || !['localhost', '127.0.0.1'].includes(new URL(url).hostname)) throw new Error('Use the disposable loopback verification stack')
  const password = 'Casetrace-production-check-only-2026'
  async function login(username: string, value = password) {
    await page.goto('/')
    await page.getByLabel('Username', { exact: true }).fill(username)
    await page.getByLabel('Password', { exact: true }).fill(value)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  }
  async function changePassword() {
    await expect(page.getByRole('heading', { name: 'Account security', exact: true })).toBeVisible()
    await page.getByLabel('Current password', { exact: true }).fill(password)
    await page.getByLabel('New password', { exact: true }).fill(password + '-individual')
    await page.getByLabel('Confirm new password', { exact: true }).fill(password + '-individual')
    await page.getByRole('button', { name: 'Change password', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Case register', exact: true })).toBeVisible()
  }
  const suffix = Date.now()
  const io = `check.io.${suffix}`, sho = `check.sho.${suffix}`
  await login('operator.check')
  await expect(page.getByText('Restricted officer access', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Officer accounts', exact: true }).click()
  for (const [username, role] of [[io, 'IO'], [sho, 'SHO']]) {
    await page.getByLabel('Username', { exact: true }).fill(username)
    await page.getByLabel('Name', { exact: true }).fill('Synthetic verification officer')
    await page.getByRole('combobox', { name: 'Role', exact: true }).first().selectOption(role)
    await page.getByLabel('Temporary password', { exact: true }).fill(password)
    await page.getByRole('button', { name: 'Add officer', exact: true }).click()
    await expect(page.getByRole('heading').filter({ hasText: username })).toBeVisible()
  }
  await page.getByRole('button', { name: 'Sign out' }).click()
  await login(io)
  await changePassword()
  await page.getByRole('button', { name: '+ New case', exact: true }).click()
  const reference = `CHECK-${suffix}`
  await page.getByLabel('Case reference', { exact: true }).fill(reference)
  await page.getByLabel('Case title', { exact: true }).fill('Synthetic production configuration verification')
  await page.getByLabel('Summary', { exact: true }).fill('Synthetic test data in an isolated verification database.')
  await page.getByRole('button', { name: 'Create case', exact: true }).click()
  await page.getByLabel('Evidence file').setInputFiles({ name: 'dispatch-proof.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic proof of a fictional external dispatch.') })
  await page.getByRole('button', { name: 'Upload evidence', exact: true }).click()
  await expect(page.getByText('Evidence saved.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Notices', exact: true }).click()
  await page.getByLabel('Recipient', { exact: true }).fill('Synthetic verification bank')
  await page.getByLabel('Case facts', { exact: true }).fill('Fictional records request for configuration verification only.')
  await page.getByRole('button', { name: 'Save draft', exact: true }).click()
  await expect(page.getByText('Draft saved for officer review.')).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await login(sho)
  await changePassword()
  await page.getByRole('searchbox').fill(reference)
  await page.getByRole('button', { name: /^Open/ }).first().click()
  await page.getByRole('button', { name: 'Notices', exact: true }).click()
  await page.getByRole('button').filter({ hasText: 'Synthetic verification bank' }).click()
  await page.getByRole('button', { name: 'Approve draft', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Record simulated send', exact: true })).toHaveCount(0)
  await page.getByLabel('External dispatch reference', { exact: true }).fill('FICTIONAL-DISPATCH-001')
  await page.getByRole('combobox', { name: 'Evidence of dispatch', exact: true }).selectOption({ label: 'dispatch-proof.txt' })
  await page.getByRole('button', { name: 'Record external dispatch', exact: true }).click()
  await expect(page.getByText('External dispatch record saved. CaseTrace did not send this notice.')).toBeVisible()
  await page.getByRole('button', { name: 'Activity', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'notice.dispatch_recorded', exact: true })).toBeVisible()
})
