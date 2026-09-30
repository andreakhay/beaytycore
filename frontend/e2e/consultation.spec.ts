import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const image = fs.readFileSync(path.join(__dirname, "fixtures", "portrait.png"));
const dataUrl = `data:image/png;base64,${image.toString("base64")}`;
const identity = "11111111-1111-4111-8111-111111111111";

function rows(feature: "hairstyle" | "makeup" | "nails") {
  const ids = feature === "hairstyle" ? ["crew_cut", "bob", "pixie"]
    : feature === "makeup" ? ["natural_makeup", "soft_glam", "bold_glam"]
      : ["classic_red", "nude_pink", "glossy_black"];
  return ids.map((style, index) => ({ id: `rec-${index + 1}`,
    primary: { feature, style_id: style, style_name: `Look ${index + 1}`,
      service: { feature, name: feature, estimated_price: 500, currency: "PHP",
        estimated_duration_minutes: 45, estimate_kind: "demo_only" }, nail_path: feature === "nails" ? (index === 1 ? "renderer" : "model") : null },
    reason: "A supported look to explore.", complements: [{ feature: "makeup", style_id: "natural_makeup",
      style_name: "Natural Makeup", service: { feature: "makeup", name: "Makeup", estimated_price: 400,
        currency: "PHP", estimated_duration_minutes: 30, estimate_kind: "demo_only" }, nail_path: null }] }));
}

async function mockConsultation(page: Page, feature: "hairstyle" | "makeup" | "nails", failSecond = false) {
  const recommendations = rows(feature);
  const attempts = [0, 0, 0];
  const generationRequests: number[] = [];
  let selected: string | null = null;
  await page.route("**/consultations**", async (route) => {
    const url = new URL(route.request().url());
    const routePath = url.pathname;
    const method = route.request().method();
    if (routePath === "/consultations/mode") {
      await route.fulfill({ json: { provider: "deterministic", model: null } }); return;
    }
    const state = { id: identity, primary_service: feature, stage: "recommended", photo: null,
      recommendations: { recommendations }, generations: [], selected_recommendation_id: selected };
    if (routePath === "/consultations" && method === "POST") {
      expect(route.request().postDataJSON()).toEqual({ primary_service: feature });
      await route.fulfill({ status: 201, json: state }); return;
    }
    if (routePath.endsWith("/photo") && method === "PUT") {
      expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
      await route.fulfill({ json: { ...state, photo: { id: identity, content_type: "image/png", width: 128, height: 128 } } }); return;
    }
    if (routePath === `/consultations/${identity}` && method === "PATCH") {
      expect(route.request().postDataJSON()).toHaveProperty("preferences");
      await route.fulfill({ json: state }); return;
    }
    if (routePath.endsWith("/recommendations") && method === "POST") {
      await route.fulfill({ json: { recommendations } }); return;
    }
    const match = routePath.match(/\/recommendations\/rec-(\d)\/generation$/);
    if (match) {
      const index = Number(match[1]) - 1;
      const success = !failSecond || index !== 1 || (method === "POST" ? attempts[index] > 0 : attempts[index] > 1);
      if (method === "POST") {
        generationRequests.push(index);
        attempts[index]++;
        await new Promise((resolve) => setTimeout(resolve, 150));
        if (!success) { await route.fulfill({ status: 502, json: { detail: "Controlled inference failure." } }); return; }
      }
      const generation = { recommendation_id: `rec-${index + 1}`, status: success ? "completed" : "failed",
        attempts: attempts[index], error: success ? null : "Controlled inference failure.", result_available: success };
      const result = success ? { status: "completed", generator: "mock_remote", style: {
        id: recommendations[index].primary.style_id, name: recommendations[index].primary.style_name,
        description: "", status: "available" },
      image: { data_url: dataUrl, content_type: "image/png", width: 128, height: 128 } } : null;
      await route.fulfill({ json: { generation, result } }); return;
    }
    if (routePath.endsWith("/select") && method === "POST") {
      selected = routePath.split("/").at(-2)!;
      await route.fulfill({ json: { ...state, selected_recommendation_id: selected } }); return;
    }
    await route.fulfill({ status: 404, json: { detail: "Unexpected request" } });
  });
  return { generationRequests, attempts };
}

for (const feature of ["hairstyle", "makeup", "nails"] as const) {
  test(`${feature} consultation progressively generates three looks and saves selection`, async ({ page }) => {
    const tracked = await mockConsultation(page, feature);
    await page.goto("/consultation");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /^Makeup A finish/ }).click();
    await expect(page.getByRole("button", { name: /^Makeup A finish/ })).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: new RegExp(`^${feature}`, "i") }).click();
    await page.getByLabel("Upload consultation photo").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: image });
    await expect(page.getByAltText("Consultation photo preview")).toBeVisible();
    await page.getByLabel("Occasion or event").fill("Celebration");
    await page.getByRole("button", { name: /Find my looks/ }).click();
    await expect(page.getByRole("article")).toHaveCount(3);
    await expect(page.getByRole("article").nth(0)).toContainText("completed");
    await expect(page.getByRole("article").nth(2)).toContainText("completed");
    expect(tracked.generationRequests).toEqual([0, 1, 2]);
    await expect(page.getByAltText("Generated Look 1 preview")).toBeVisible();
    await page.getByRole("article").nth(1).getByRole("button", { name: "Select this look" }).click();
    await expect(page.getByRole("region", { name: "Selected recommendation" })).toContainText("Look 2");
    await expect(page.getByText("Natural Makeup").first()).toBeVisible();
  });
}

test("one failed look is retried manually without regenerating siblings", async ({ page }) => {
  const tracked = await mockConsultation(page, "hairstyle", true);
  await page.goto("/consultation");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Upload consultation photo").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: image });
  await expect(page.getByAltText("Consultation photo preview")).toBeVisible();
  await page.getByRole("button", { name: /Find my looks/ }).click();
  await expect(page.getByRole("article").nth(1)).toContainText("Controlled inference failure.");
  await expect(page.getByRole("article").nth(2)).toContainText("completed");
  expect(tracked.generationRequests).toEqual([0, 1, 2]);
  await page.getByRole("article").nth(1).getByRole("button", { name: "Retry this look" }).click();
  await expect(page.getByRole("article").nth(1)).toContainText("completed");
  expect(tracked.generationRequests).toEqual([0, 1, 2, 1]);
});

for (const item of [{ feature: "hairstyle", href: "/" }, { feature: "makeup", href: "/makeup" },
  { feature: "nails", href: "/nails" }] as const) {
  test(`${item.feature} Custom opens the existing page with the photo`, async ({ page }) => {
    await page.route(`**/features/${item.feature}/styles`, (route) => route.fulfill({ json: [] }));
    await page.route("**/health", (route) => route.fulfill({ json: { status: "ok", generator: "mock" } }));
    await page.goto("/consultation");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: new RegExp(`^${item.feature}`, "i") }).click();
    await page.getByLabel("Upload consultation photo").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: image });
    await expect(page.getByAltText("Consultation photo preview")).toBeVisible();
    await page.getByRole("link", { name: new RegExp(`Custom ${item.feature}`, "i") }).click();
    await expect(page).toHaveURL(new RegExp(`${item.href.replace("/", "\\/")}$`));
    await expect(page.getByText("photo.png")).toBeVisible();
    await expect(page.locator(".studio-photo img")).toBeVisible();
  });
}

test("malformed two-item recommendations fail safely before generation", async ({ page }) => {
  const tracked = await mockConsultation(page, "hairstyle");
  await page.route("**/consultations/*/recommendations", (route) => route.fulfill({ json: {
    recommendations: rows("hairstyle").slice(0, 2),
  } }));
  await page.goto("/consultation");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Upload consultation photo").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: image });
  await expect(page.getByAltText("Consultation photo preview")).toBeVisible();
  await page.getByRole("button", { name: /Find my looks/ }).click();
  await expect(page.locator(".studio-alert")).toContainText("unreadable response");
  expect(tracked.generationRequests).toEqual([]);
});

test("consultation remains usable on a narrow screen", async ({ page }) => {
  await mockConsultation(page, "nails");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/consultation");
  await page.getByRole("button", { name: /^Nails A polished/ }).click();
  await page.getByLabel("Upload consultation photo").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: image });
  await page.getByRole("button", { name: /Find my looks/ }).click();
  await expect(page.getByRole("article").nth(2)).toContainText("completed");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
