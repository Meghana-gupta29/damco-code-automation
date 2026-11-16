import { test, expect } from "@playwright/test";
import {
  uniqueEmail,
  createUserViaApi,
  deleteUserViaApi,
  uiLogin,
  PASSWORD,
} from "./helpers";

test("TC-047 Non-superuser cannot access admin page", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await expect(page.getByRole("link", { name: "Admin" })).toHaveCount(0);

    await page.goto("/admin");
    await expect(page).not.toHaveURL(/\/admin/);
    await expect(page.getByRole("heading", { name: "Users" })).not.toBeVisible();
    await expect(
      page.getByText("Manage user accounts and permissions"),
    ).not.toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});
