import { expect, test } from "@playwright/test";
import path from "node:path";

const photo = path.join(__dirname, "fixtures", "portrait.png");
const backend = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

test.skip(process.env.CONSULTATION_LOCAL_MOCK !== "1", "Run only with the local mock backend; never call live GPU in CI.");

for (const feature of ["hairstyle", "makeup", "nails"] as const) {
  test(`${feature} complete browser-to-consultation-to-existing-mock-handler flow`, async ({ page, request }) => {
    const health = await request.get(`${backend}/health`);
    const makeup = await request.get(`${backend}/makeup/health`);
    const nails = await request.get(`${backend}/nails/styles`);
    test.skip(!health.ok() || (await health.json()).generator !== "mock"
      || !makeup.ok() || (await makeup.json()).status !== "mock"
      || !nails.ok() || (await nails.json()).some((row: { status: string }) => row.status === "available"),
    "The central backend is not fully in local mock mode.");
    const generations: string[] = [];
    page.on("response", (response) => {
      if (/\/consultations\/[^/]+\/recommendations\/[^/]+\/generation$/.test(new URL(response.url()).pathname)
          && response.request().method() === "POST") generations.push(response.url());
    });
    await page.goto("/consultation");
    await page.getByRole("button", { name: new RegExp(`^${feature}`, "i") }).click();
    await page.getByLabel("Upload consultation photo").setInputFiles(photo);
    await page.getByRole("button", { name: /Find my looks/ }).click();
    await expect(page.getByRole("article")).toHaveCount(3);
    await expect(page.getByRole("article").nth(2)).toContainText("completed", { timeout: 30000 });
    expect(generations).toHaveLength(3);
    await expect(page.locator(".consult-card img")).toHaveCount(3);
    await page.getByRole("article").nth(0).getByRole("button", { name: "Select this look" }).click();
    await expect(page.getByRole("region", { name: "Selected recommendation" })).toBeVisible();
  });
}
