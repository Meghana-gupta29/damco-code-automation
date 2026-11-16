import { expect, test } from "@playwright/test"
import {
  API,
  createUserViaApi,
  deleteUserViaApi,
  uiLogin,
} from "./helpers"

test("TC-051 Search box filters the items list and shows the no-match empty state", async ({
  page,
  request,
}) => {
  const user = await createUserViaApi(request)
  try {
    const uniq = `s${Date.now()}${Math.floor(Math.random() * 1e6)}`
    const alpha = `${uniq}-Alpha`
    const beta = `${uniq}-Beta`

    const tokenRes = await request.post(`${API}/login/access-token`, {
      form: { username: user.email, password: user.password },
    })
    expect(tokenRes.status()).toBe(200)
    const token = (await tokenRes.json()).access_token

    for (const title of [alpha, beta]) {
      const r = await request.post(`${API}/items/`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { title, description: "pr1 search" },
      })
      expect(r.status(), `item create failed: ${await r.text()}`).toBe(200)
    }

    await uiLogin(page, user.email, user.password)
    await page.goto("/items")

    await expect(page.getByText(alpha, { exact: true })).toBeVisible()
    await expect(page.getByText(beta, { exact: true })).toBeVisible()

    const search = page.getByTestId("item-search")
    await search.fill(`${uniq}-alpha`)

    await expect(page.getByText(beta, { exact: true })).toHaveCount(0)
    await expect(page.getByText(alpha, { exact: true })).toBeVisible()

    await search.fill(`${uniq}-nomatch-zzz`)

    await expect(page.getByText("No items match your search")).toBeVisible()
    await expect(page.getByText("Try a different search term")).toBeVisible()
  } finally {
    await deleteUserViaApi(request, user.id)
  }
})
