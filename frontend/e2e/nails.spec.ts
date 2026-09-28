import { expect, test } from "@playwright/test";
import path from "node:path";

const photo = path.join(__dirname, "fixtures", "portrait.png");

test("Nails five-style page keeps development previews clearly labeled", async ({ page }) => {
  await page.goto("/nails");
  await expect(page.getByRole("heading", { name: "A polished look. Made for your hands." })).toBeVisible();
  await expect(page.locator("button[aria-pressed]")).toHaveCount(5);
  await expect(page.getByRole("button", { name: "Try this style" })).toBeDisabled();
  await page.locator("input[type=file]").setInputFiles(photo);
  await page.locator("button[aria-pressed]").filter({ hasText: "Classic Red Gloss" }).click();
  await page.getByRole("button", { name: "Try this style" }).click();
  await expect(page.getByText("Nail styling is unavailable in this development preview.")).toBeVisible();
  await expect(page.getByAltText("Original photo preview")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByRole("button", { name: "Try this style" })).toBeDisabled();
});
