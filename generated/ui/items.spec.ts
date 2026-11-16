import { test, expect, type Page } from "@playwright/test";
import {
  uniqueEmail,
  createUserViaApi,
  deleteUserViaApi,
  uiLogin,
  uiLogout,
  PASSWORD,
} from "./helpers";

async function addItemViaUi(page: Page, title: string, description?: string) {
  await page.getByRole("button", { name: "Add Item" }).click();
  await page.getByLabel("Title").fill(title);
  if (description) await page.getByLabel("Description").fill(description);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Item created successfully")).toBeVisible();
  await expect(page.getByRole("dialog")).not.toBeVisible();
}

test("TC-039 Create item through the UI", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/items");
    const title = `Item ${Date.now()}`;
    await addItemViaUi(page, title, "Created via UI test");
    await expect(
      page.getByRole("row").filter({ hasText: title }),
    ).toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-040 Item form requires title and enforces max length", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/items");
    await page.getByRole("button", { name: "Add Item" }).click();

    await page.getByLabel("Title").fill("");
    await page.getByLabel("Title").blur();
    await expect(page.getByText("Title is required")).toBeVisible();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Item created successfully")).not.toBeVisible();

    const longTitle = "L".repeat(256);
    await page.getByLabel("Title").fill(longTitle);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Item created successfully")).not.toBeVisible();
    await expect(page.getByRole("dialog")).toBeVisible();

    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.getByText(longTitle)).not.toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-041 Edit item through the UI", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/items");
    const title = `Edit me ${Date.now()}`;
    await addItemViaUi(page, title);

    const row = page.getByRole("row").filter({ hasText: title });
    await row.getByRole("button").last().click();
    await page.getByRole("menuitem", { name: "Edit Item" }).click();
    const updated = `Edited ${Date.now()}`;
    await page.getByLabel("Title").fill(updated);
    await page.getByRole("button", { name: "Save" }).click();

    await expect(page.getByText("Item updated successfully")).toBeVisible();
    await expect(
      page.getByRole("row").filter({ hasText: updated }),
    ).toBeVisible();
    await expect(page.getByText(title, { exact: true })).not.toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-042 Delete item through the UI with confirmation", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await page.goto("/items");
    const title = `Delete me ${Date.now()}`;
    await addItemViaUi(page, title);
    const row = page.getByRole("row").filter({ hasText: title });

    // Cancel keeps the item
    await row.getByRole("button").last().click();
    await page.getByRole("menuitem", { name: "Delete Item" }).click();
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    // The row actions dropdown stays open after the dialog closes (app keeps the menu item
    // selected via preventDefault) and hides the table from role queries; close it first.
    await page.keyboard.press("Escape");
    await expect(row).toBeVisible();

    // Confirm deletes it
    await row.getByRole("button").last().click();
    await page.getByRole("menuitem", { name: "Delete Item" }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Delete", exact: true })
      .click();
    await expect(
      page.getByText("The item was deleted successfully"),
    ).toBeVisible();
    await expect(page.getByText(title)).not.toBeVisible();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-043 Items list shows only the logged-in user's items", async ({ page, request }) => {
  const emailA = uniqueEmail();
  const emailB = uniqueEmail();
  await createUserViaApi(request, { email: emailA, password: PASSWORD });
  await createUserViaApi(request, { email: emailB, password: PASSWORD });
  try {
    await uiLogin(page, emailA, PASSWORD);
    await page.goto("/items");
    const title = `A-only ${Date.now()}`;
    await addItemViaUi(page, title);
    await expect(page.getByText(title)).toBeVisible();

    await uiLogout(page);
    await uiLogin(page, emailB, PASSWORD);
    await page.goto("/items");
    await expect(page.getByText("You don't have any items yet")).toBeVisible();
    await expect(page.getByText(title)).not.toBeVisible();
  } finally {
    await deleteUserViaApi(request, emailA).catch(() => {});
    await deleteUserViaApi(request, emailB).catch(() => {});
  }
});
