// Hand-written shared helpers for generated UI tests (not agent-written).
import { expect, type APIRequestContext, type Page } from "@playwright/test"

export const API = (process.env.QA_UI_URL || "http://localhost:8000") + "/api/v1"
export const ADMIN_EMAIL = process.env.QA_ADMIN_EMAIL || "admin@example.com"
export const ADMIN_PASSWORD = process.env.QA_ADMIN_PASSWORD || "changethis"
export const PASSWORD = "Qa-Pass-12345"

export function uniqueEmail(prefix = "qaui"): string {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}@example.com`
}

/** Create a user through the API (fast, no UI). Returns credentials + id. */
export async function createUserViaApi(
  request: APIRequestContext,
  opts: { email?: string; password?: string; fullName?: string } = {},
) {
  const email = opts.email ?? uniqueEmail()
  const password = opts.password ?? PASSWORD
  const r = await request.post(`${API}/users/signup`, {
    data: { email, password, full_name: opts.fullName ?? "QA UI User" },
  })
  expect(r.status(), `signup failed: ${await r.text()}`).toBe(200)
  const body = await r.json()
  return { email, password, id: body.id as string }
}

export async function deleteUserViaApi(request: APIRequestContext, id: string) {
  const t = await request.post(`${API}/login/access-token`, {
    form: { username: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  })
  const token = (await t.json()).access_token
  await request.delete(`${API}/users/${id}`, { headers: { Authorization: `Bearer ${token}` } })
}

/** Log in through the real login form and wait for the dashboard. */
export async function uiLogin(page: Page, email: string, password: string) {
  await page.goto("/login")
  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
  await page.getByRole("button", { name: "Log In" }).click()
  await page.waitForURL("/")
  await expect(page.getByText("Welcome back, nice to see you again!")).toBeVisible()
}

export async function uiLogout(page: Page) {
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL(/\/login/)
}
