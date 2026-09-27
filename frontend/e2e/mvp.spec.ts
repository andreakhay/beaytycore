import { expect, test } from "@playwright/test";
import path from "node:path";

const portrait = path.join(__dirname, "fixtures", "portrait.png");

test("upload, choose, generate, change style, and reset", async ({ page }) => {
  await page.goto("/");
  const generate = page.getByRole("button", { name: "Generate preview" });
  await expect(generate).toBeDisabled();
  await expect(page.getByText("Bob", { exact: true })).toBeVisible();

  await page.locator("input[type=file]").setInputFiles({
    name: "wrong.txt", mimeType: "text/plain", buffer: Buffer.from("not an image"),
  });
  await expect(page.locator("#upload-error")).toContainText("Choose a JPG or PNG portrait");
  await expect(generate).toBeDisabled();

  await page.locator("input[type=file]").setInputFiles(portrait);
  await expect(page.getByAltText("Preview of your uploaded portrait")).toBeVisible();
  await expect(generate).toBeDisabled();

  await page.locator('button[aria-pressed]').filter({ hasText: "Bob" }).click();
  await expect(generate).toBeEnabled();
  await page.route("**/features/hairstyle/generate", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.continue();
  });
  await generate.click();
  await expect(page.getByRole("button", { name: "Generating preview…" })).toBeDisabled();
  await expect(page.getByRole("heading", { name: "A first look at the flow" })).toBeVisible();
  await expect(page.getByText("AI model not connected yet.", { exact: false })).toBeVisible();
  await expect(page.getByAltText("Development preview from the mock generator")).toBeVisible();

  await page.locator('button[aria-pressed]').filter({ hasText: "Pixie" }).click();
  await expect(page.getByRole("heading", { name: "A first look at the flow" })).toHaveCount(0);
  await generate.click();
  await expect(page.getByText("Pixie", { exact: true }).last()).toBeVisible();

  await page.getByRole("button", { name: "Remove" }).click();
  await expect(generate).toBeDisabled();
  await expect(page.getByRole("heading", { name: "A first look at the flow" })).toHaveCount(0);
});

test("generation failure is shown as a clear error", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Bob", { exact: true })).toBeVisible();
  await page.locator("input[type=file]").setInputFiles(portrait);
  await page.locator('button[aria-pressed]').filter({ hasText: "Bob" }).click();
  await page.route("**/features/hairstyle/generate", (route) => route.abort());
  await page.getByRole("button", { name: "Generate preview" }).click();
  await expect(page.getByText("The backend is unavailable", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate preview" })).toBeEnabled();
});

test("backend unavailable is explained without a stack trace", async ({ page }) => {
  await page.route("**/features/hairstyle/styles", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByText("The local API is unavailable", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate preview" })).toBeDisabled();
  await page.unroute("**/features/hairstyle/styles");
  await page.getByRole("button", { name: "Retry connection" }).click();
  await expect(page.getByText("Bob", { exact: true })).toBeVisible();
});

test("the main flow remains usable on a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByText("Bob", { exact: true })).toBeVisible();
  await page.locator("input[type=file]").setInputFiles(portrait);
  await page.locator('button[aria-pressed]').filter({ hasText: "Bob" }).click();
  await page.getByRole("button", { name: "Generate preview" }).click();
  await expect(page.getByAltText("Development preview from the mock generator")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
