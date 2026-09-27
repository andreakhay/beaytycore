import { expect, test } from "@playwright/test";
import path from "node:path";

for (const { feature, pagePath, styleName, button } of [
  { feature: "hairstyle", pagePath: "/", styleName: "Bob", button: "Generate preview" },
  { feature: "makeup", pagePath: "/makeup", styleName: "Soft Glam", button: "Generate preview" },
  { feature: "nails", pagePath: "/nails", styleName: "Classic Red Gloss", button: "Try this style" },
]) {
  test(`${feature} displays malformed central results safely without legacy fallback`, async ({ page }) => {
    const crashes: string[] = [];
    const requests: string[] = [];
    page.on("pageerror", (error) => crashes.push(error.message));
    page.on("request", (request) => requests.push(new URL(request.url()).pathname));
    await page.route(`**/features/${feature}/generate`, (route) => route.fulfill({ json: { image: null } }));
    await page.goto(pagePath);
    await page.locator("input[type=file]").setInputFiles(path.join(__dirname, "fixtures", "portrait.png"));
    await page.locator("button[aria-pressed]").filter({ hasText: styleName }).click();
    await page.getByRole("button", { name: button }).click();
    await expect(page.getByRole("alert").filter({ hasText: "The backend returned an unreadable response" })).toBeVisible();
    await expect(page.getByRole("button", { name: button })).toBeEnabled();
    expect(crashes).toEqual([]);
    expect(requests.filter((url) => ["/generate", "/makeup/generate", "/nails/generate"].includes(url))).toEqual([]);
  });
}
