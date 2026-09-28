import { expect, test } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

const portrait = path.join(__dirname, "fixtures", "portrait.png");

test("Makeup has its own catalog and clearly labelled placeholder flow", async ({ page }) => {
  await page.goto("/makeup");
  await expect(page.getByRole("heading", { name: "Explore a new look. Keep the portrait yours." })).toBeVisible();
  await expect(page.locator("button[aria-pressed]")).toHaveCount(10);
  await expect(page.getByRole("button", { name: "Generate preview" })).toBeDisabled();
  await page.locator("input[type=file]").setInputFiles(portrait);
  await page.locator("button[aria-pressed]").filter({ hasText: "Soft Glam" }).click();
  await page.getByRole("button", { name: "Generate preview" }).click();
  await expect(page.getByRole("heading", { name: "A preview of the workflow" })).toBeVisible();
  await expect(page.getByText("No makeup was applied.", { exact: false })).toBeVisible();
  await expect(page.getByAltText("Normalized original portrait returned by the makeup prototype")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByRole("button", { name: "Generate preview" })).toBeDisabled();
});

test("Makeup request errors are visible and the button recovers", async ({ page }) => {
  await page.goto("/makeup");
  await expect(page.locator("button[aria-pressed]")).toHaveCount(10);
  await page.locator("input[type=file]").setInputFiles(portrait);
  await page.locator("button[aria-pressed]").filter({ hasText: "Classic Red Lip" }).click();
  await page.route("**/features/makeup/generate", (route) => route.abort());
  await page.getByRole("button", { name: "Generate preview" }).click();
  await expect(page.getByText("The backend is unavailable", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate preview" })).toBeEnabled();
});

test("Makeup navigation returns to the Hairstyle feature on a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/makeup");
  await expect(page.getByRole("navigation", { name: "Features" }).getByRole("link", { name: "Hairstyle" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("navigation", { name: "Features" }).getByRole("link", { name: "Hairstyle" }).click();
  await expect(page.getByRole("heading", { name: /Discover your next hairstyle/ })).toBeVisible();
});

test("Configured Makeup renders a model result, not a placeholder", async ({ page }) => {
  await page.route("**/features/makeup/styles", async (route) => {
    const response = await route.fetch();
    const styles = (await response.json()).map((style: { status: string }) => ({ ...style, status: "trained_preset" }));
    await route.fulfill({ json: styles });
  });
  await page.route("**/features/makeup/generate", async (route) => {
    await route.fulfill({ json: {
      status: "completed", generator: "flux2_klein_base_makeup001",
      style: { id: "soft_glam", name: "Soft Glam", description: "Blended eyes", status: "trained_preset" },
      image: { data_url: `data:image/png;base64,${fs.readFileSync(portrait).toString("base64")}`,
        content_type: "image/png", width: 128, height: 128 },
      metadata: { runtime_seconds: 60 },
    } });
  });
  await page.goto("/makeup");
  await expect(page.getByRole("button", { name: "Generate makeup" })).toBeDisabled();
  await page.getByLabel("Upload your portrait").setInputFiles(portrait);
  await page.locator("button[aria-pressed]").filter({ hasText: "Soft Glam" }).click();
  await page.getByRole("button", { name: "Generate makeup" }).click();
  await expect(page.getByRole("heading", { name: "Your MAKEUP-001 result" })).toBeVisible();
  await expect(page.getByAltText("MAKEUP-001 generated Soft Glam result")).toBeVisible();
  await expect(page.getByText("No makeup was applied.", { exact: false })).toHaveCount(0);
  await expect(page.getByText("not an exact prediction of real cosmetics", { exact: false })).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByRole("heading", { name: "Your MAKEUP-001 result" })).toHaveCount(0);
});

test("Configured Makeup preserves selection while generating and recovers from GPU errors", async ({ page }) => {
  await page.route("**/features/makeup/styles", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ json: (await response.json()).map((style: { status: string }) => ({ ...style, status: "trained_preset" })) });
  });
  let finishRequest: (() => Promise<void>) | undefined;
  await page.route("**/features/makeup/generate", async (route) => {
    finishRequest = () => route.fulfill({ status: 502, json: { detail: "The Makeup GPU is busy. Wait for the current request to finish." } });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/makeup");
  await page.getByLabel("Upload your portrait").setInputFiles(portrait);
  await page.locator("button[aria-pressed]").filter({ hasText: "Classic Red Lip" }).click();
  await page.getByRole("button", { name: "Generate makeup" }).click();
  await expect(page.locator(".studio-processing")).toContainText("Creating your makeup look");
  await expect(page.getByRole("button", { name: "Remove" })).toBeDisabled();
  await expect(page.locator("button[aria-pressed]").first()).toBeDisabled();
  await expect.poll(() => Boolean(finishRequest)).toBe(true);
  await finishRequest!();
  await expect(page.getByRole("alert").filter({ hasText: "Makeup GPU is busy" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate makeup" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Remove" })).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
