import { expect, test } from "@playwright/test";
import path from "node:path";

const photo = path.join(__dirname, "fixtures", "portrait.png");

for (const { feature, pagePath, styleName, styleId, button, resultAlt } of [
  { feature: "hairstyle", pagePath: "/", styleName: "Bob", styleId: "bob", button: "Generate preview", resultAlt: "Development preview from the mock generator" },
  { feature: "makeup", pagePath: "/makeup", styleName: "Soft Glam", styleId: "soft_glam", button: "Generate preview", resultAlt: "Normalized original portrait returned by the makeup prototype" },
  { feature: "nails", pagePath: "/nails", styleName: "Classic Red Gloss", styleId: "classic_red", button: "Try this style", resultAlt: "Original photo preview" },
]) {
  test(`${feature} page discovers styles and generates through the central local backend`, async ({ page }) => {
    const requests: string[] = [];
    page.on("request", (request) => requests.push(new URL(request.url()).pathname));
    const styles = page.waitForResponse((response) => new URL(response.url()).pathname === `/features/${feature}/styles`);
    await page.goto(pagePath);
    expect((await styles).status()).toBe(200);
    await page.locator("input[type=file]").setInputFiles(photo);
    await page.locator("button[aria-pressed]").filter({ hasText: styleName }).click();
    const generation = page.waitForResponse((response) => new URL(response.url()).pathname === `/features/${feature}/generate`);
    await page.getByRole("button", { name: button }).click();
    const response = await generation;
    expect(response.status()).toBe(200);
    const request = response.request();
    expect(request.method()).toBe("POST");
    expect(request.headers()["content-type"]).toContain("multipart/form-data; boundary=");
    // Edge omits uploaded file bodies from postDataBuffer; client tests inspect
    // FormData directly, and the local backend response proves it parsed it.
    expect((await response.json()).style.id).toBe(styleId);
    await expect(page.getByAltText(resultAlt)).toBeVisible();
    expect(requests.filter((url) => ["/styles", "/generate", "/makeup/styles", "/makeup/generate", "/nails/styles", "/nails/generate"].includes(url))).toEqual([]);
  });
}
