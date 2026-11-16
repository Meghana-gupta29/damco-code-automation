import { test, expect } from "@playwright/test";
import {
  uniqueEmail,
  createUserViaApi,
  deleteUserViaApi,
  uiLogin,
  uiLogout,
  PASSWORD,
} from "./helpers";

test("TC-044 Update profile in settings", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/settings");
    await page.getByRole("tab", { name: "My profile" }).click();
    const newName = `Renamed ${Date.now()}`.slice(0, 30);
    await page.getByRole("button", { name: "Edit" }).click();
    await page.getByLabel("Full name").fill(newName);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("User updated successfully")).toBeVisible();

    await page.reload();
    await page.getByRole("tab", { name: "My profile" }).click();
    await expect(
      page.locator("form").getByText(newName, { exact: true }),
    ).toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-045 Change password in settings", async ({ page, request }) => {
  const email = uniqueEmail();
  const newPassword = `NewPass-${Date.now()}`;
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/settings");
    await page.getByRole("tab", { name: "Password" }).click();
    await page.getByTestId("current-password-input").fill(PASSWORD);
    await page.getByTestId("new-password-input").fill(newPassword);
    await page.getByTestId("confirm-password-input").fill(newPassword);
    await page.getByRole("button", { name: "Update Password" }).click();
    await expect(page.getByText("Password updated successfully")).toBeVisible();

    await uiLogout(page);
    await uiLogin(page, email, newPassword);
    await expect(page).toHaveURL(/\/$/);
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-046 Change password validation: mismatch and wrong current", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/settings");
    await page.getByRole("tab", { name: "Password" }).click();

    // Mismatch: flagged inline, no request sent
    let updateCalls = 0;
    page.on("request", (r) => {
      if (r.url().includes("/users/me/password")) updateCalls++;
    });
    await page.getByTestId("current-password-input").fill(PASSWORD);
    await page.getByTestId("new-password-input").fill("FirstNewPass-123");
    await page.getByTestId("confirm-password-input").fill("OtherNewPass-456");
    await page.getByRole("button", { name: "Update Password" }).click();
    await expect(page.getByText("The passwords don't match")).toBeVisible();
    expect(updateCalls).toBe(0);

    // Wrong current password: API 400 and error toast
    const newPw = "ValidNewPass-789";
    await page.getByTestId("current-password-input").fill("WrongCurrent-000");
    await page.getByTestId("new-password-input").fill(newPw);
    await page.getByTestId("confirm-password-input").fill(newPw);
    const responsePromise = page.waitForResponse((r) =>
      r.url().includes("/users/me/password"),
    );
    await page.getByRole("button", { name: "Update Password" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(400);
    await expect(page.getByText(/incorrect password/i).first()).toBeVisible();
    await expect(
      page.getByText("Password updated successfully"),
    ).not.toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});
