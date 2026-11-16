import { test, expect } from "@playwright/test";
import {
  uniqueEmail,
  createUserViaApi,
  deleteUserViaApi,
  uiLogin,
  PASSWORD,
} from "./helpers";

test("TC-031 Sign up via UI form", async ({ page, request }) => {
  const email = uniqueEmail();
  try {
    await page.goto("/signup");
    await page.getByTestId("full-name-input").fill("UI Signup User");
    await page.getByTestId("email-input").fill(email);
    await page.getByTestId("password-input").fill(PASSWORD);
    await page.getByTestId("confirm-password-input").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign Up" }).click();
    await expect(page).toHaveURL(/\/login/);
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-032 Sign-up validation: mismatched passwords", async ({ page }) => {
  let signupCalls = 0;
  page.on("request", (r) => {
    if (r.url().includes("/users/signup")) signupCalls++;
  });
  await page.goto("/signup");
  await page.getByTestId("full-name-input").fill("Mismatch User");
  await page.getByTestId("email-input").fill(uniqueEmail());
  await page.getByTestId("password-input").fill(PASSWORD);
  await page.getByTestId("confirm-password-input").fill(PASSWORD + "different");
  await page.getByTestId("confirm-password-input").blur();
  await page.getByRole("button", { name: "Sign Up" }).click();
  await expect(page.getByText("The passwords don't match")).toBeVisible();
  await expect(page).toHaveURL(/\/signup/);
  expect(signupCalls).toBe(0);
});

test("TC-033 Sign-up validation: short password and invalid email", async ({ page }) => {
  let signupCalls = 0;
  page.on("request", (r) => {
    if (r.url().includes("/users/signup")) signupCalls++;
  });
  await page.goto("/signup");
  await page.getByTestId("full-name-input").fill("Invalid Input User");
  await page.getByTestId("email-input").fill("not-an-email");
  await page.getByTestId("email-input").blur();
  await page.getByTestId("password-input").fill("1234567");
  await page.getByTestId("password-input").blur();
  await page.getByTestId("confirm-password-input").fill("1234567");
  await page.getByTestId("confirm-password-input").blur();
  await page.getByRole("button", { name: "Sign Up" }).click();
  await expect(page.getByText("Invalid email address")).toBeVisible();
  await expect(
    page.getByText("Password must be at least 8 characters"),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/signup/);
  expect(signupCalls).toBe(0);
});

test("TC-034 Sign-up with an already registered email", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await page.goto("/signup");
    await page.getByTestId("full-name-input").fill("Duplicate User");
    await page.getByTestId("email-input").fill(email);
    await page.getByTestId("password-input").fill(PASSWORD);
    await page.getByTestId("confirm-password-input").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign Up" }).click();
    await expect(page.getByText(/already exists/i).first()).toBeVisible();
    await expect(page).toHaveURL(/\/signup/);
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-035 Login via UI with valid credentials", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await uiLogin(page, email, PASSWORD);
    await expect(page).toHaveURL(/\/$/);
    await expect(
      page.getByText("Welcome back, nice to see you again!"),
    ).toBeVisible();
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token"),
    );
    expect(token).toBeTruthy();
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-036 Login via UI with wrong password", async ({ page, request }) => {
  const email = uniqueEmail();
  await createUserViaApi(request, { email, password: PASSWORD });
  try {
    await page.goto("/login");
    await page.getByTestId("email-input").fill(email);
    await page.getByTestId("password-input").fill(PASSWORD + "-wrong");
    await page.getByRole("button", { name: "Log In" }).click();
    await expect(
      page.getByText(/incorrect email or password/i).first(),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  } finally {
    await deleteUserViaApi(request, email).catch(() => {});
  }
});

test("TC-037 Login form empty and invalid email validation", async ({ page }) => {
  let loginCalls = 0;
  page.on("request", (r) => {
    if (r.url().includes("/login/access-token")) loginCalls++;
  });
  await page.goto("/login");
  await page.getByRole("button", { name: "Log In" }).click();
  await expect(page.getByText("Invalid email address")).toBeVisible();
  await expect(page.getByText("Password is required")).toBeVisible();

  await page.getByTestId("email-input").fill("not-an-email");
  await page.getByTestId("email-input").blur();
  await page.getByRole("button", { name: "Log In" }).click();
  await expect(page.getByText("Invalid email address")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
  expect(loginCalls).toBe(0);
});

test("TC-038 Unauthenticated access to protected route redirects to login", async ({ page }) => {
  await page.goto("/login");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/items");
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/login/);
});
