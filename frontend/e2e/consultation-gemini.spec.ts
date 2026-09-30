import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const photo = fs.readFileSync(path.join(__dirname, "fixtures", "portrait.png"));
const dataUrl = `data:image/png;base64,${photo.toString("base64")}`;
const identity = "11111111-1111-4111-8111-111111111111";

test("Gemini mode asks, captures answers, then feeds three existing result cards", async ({ page }) => {
  let turns = 0;
  const generated: string[] = [];
  const recommendations = ["crew_cut", "bob_hair", "layered_hair"].map((style, index) => ({
    id: `rec-${index + 1}`, primary: { feature: "hairstyle", style_id: style, style_name: style,
      service: { feature: "hairstyle", name: "Hairstyle", estimated_price: 600,
        currency: "PHP", estimated_duration_minutes: 60, estimate_kind: "demo_only" }, nail_path: null },
    reason: "Fits your clean graduation direction.", complements: [],
  }));
  await page.route("**/consultations**", async (route) => {
    const url = new URL(route.request().url()).pathname;
    const method = route.request().method();
    if (url === "/consultations/mode") {
      await route.fulfill({ json: { provider: "gemini", model: "gemini-3.8-flash" } }); return;
    }
    const messages = turns === 0 ? [] : turns === 1
      ? [{ role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" }]
      : turns === 2 ? [{ role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" },
        { role: "user", content: "My graduation.", created_at: "2026-09-30T00:00:00Z" },
        { role: "assistant", content: "What kind of look would you like?", created_at: "2026-09-30T00:00:00Z" }]
        : [{ role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" },
          { role: "user", content: "My graduation.", created_at: "2026-09-30T00:00:00Z" },
          { role: "assistant", content: "What kind of look would you like?", created_at: "2026-09-30T00:00:00Z" },
          { role: "user", content: "Clean and easy to maintain.", created_at: "2026-09-30T00:00:00Z" },
          { role: "assistant", content: "I have three ideas for you.", created_at: "2026-09-30T00:00:00Z" }];
    const state = { id: identity, primary_service: "hairstyle", stage: turns >= 3 ? "recommended" : "collecting",
      photo: turns > 0 ? { id: identity, content_type: "image/png", width: 128, height: 128 } : null,
      conversation_status: turns >= 3 ? "ready_for_recommendation" : "more_information",
      messages, recommendations: turns >= 3 ? { recommendations } : null,
      generations: [], selected_recommendation_id: null };
    if (url === "/consultations" && method === "POST") {
      await route.fulfill({ status: 201, json: state }); return;
    }
    if (url.endsWith("/photo") && method === "PUT") {
      await route.fulfill({ json: { ...state, photo: { id: identity, content_type: "image/png", width: 128, height: 128 } } }); return;
    }
    if (url.endsWith("/turn") && method === "POST") {
      turns++;
      const current = route.request().postDataJSON();
      if (turns === 1) expect(current).toEqual({});
      if (turns === 2) expect(current.message).toBe("My graduation.");
      if (turns === 3) expect(current.message).toBe("Clean and easy to maintain.");
      const completedMessages = turns === 1
        ? [{ role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" }]
        : turns === 2
          ? [{ role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" },
            { role: "user", content: "My graduation.", created_at: "2026-09-30T00:00:00Z" },
            { role: "assistant", content: "What kind of look would you like?", created_at: "2026-09-30T00:00:00Z" }]
          : [{ role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" },
            { role: "user", content: "My graduation.", created_at: "2026-09-30T00:00:00Z" },
            { role: "assistant", content: "What kind of look would you like?", created_at: "2026-09-30T00:00:00Z" },
            { role: "user", content: "Clean and easy to maintain.", created_at: "2026-09-30T00:00:00Z" },
            { role: "assistant", content: "I have three ideas for you.", created_at: "2026-09-30T00:00:00Z" }];
      await route.fulfill({ json: { state: { ...state, messages: completedMessages },
        assistant_message: turns === 1 ? "What are you getting ready for?" : turns === 2
          ? "What kind of look would you like?" : "I have three ideas for you.",
        status: turns >= 3 ? "ready_for_recommendation" : "more_information",
        recommendations: turns >= 3 ? { recommendations } : null } }); return;
    }
    const match = url.match(/\/recommendations\/(rec-\d)\/generation$/);
    if (match && method === "POST") {
      generated.push(match[1]);
      const index = Number(match[1].at(-1)) - 1;
      await route.fulfill({ json: { generation: { recommendation_id: match[1], status: "completed",
        attempts: 1, error: null, result_available: true },
      result: { status: "completed", generator: "mock_remote", style: {
        id: recommendations[index].primary.style_id, name: recommendations[index].primary.style_name,
        description: "", status: "available" }, image: { data_url: dataUrl,
          content_type: "image/png", width: 128, height: 128 } } } }); return;
    }
    await route.fulfill({ status: 404, json: { detail: "Unexpected request" } });
  });
  await page.goto("/consultation");
  await expect(page.getByText("Start when your photo is ready.", { exact: false })).toBeVisible();
  await expect(page.getByLabel("Occasion or event")).toHaveCount(0);
  await page.getByLabel("Upload consultation photo").setInputFiles({ name: "test.png", mimeType: "image/png", buffer: photo });
  await page.getByRole("button", { name: /Start AI consultation/ }).click();
  await expect(page.getByRole("log")).toContainText("What are you getting ready for?");
  await page.getByLabel("Your reply").fill("My graduation.");
  await page.getByRole("button", { name: "Send reply" }).click();
  await expect(page.getByRole("log")).toContainText("What kind of look would you like?");
  await page.getByLabel("Your reply").fill("Clean and easy to maintain.");
  await page.getByRole("button", { name: "Send reply" }).click();
  await expect(page.getByRole("article")).toHaveCount(3);
  await expect(page.getByRole("article").nth(2)).toContainText("completed");
  expect(generated).toEqual(["rec-1", "rec-2", "rec-3"]);
  await expect(page.locator(".consult-card img")).toHaveCount(3);
});

test("an unavailable opening question can be retried on the same consultation", async ({ page }) => {
  let creates = 0;
  let openingCalls = 0;
  await page.route("**/consultations**", async (route) => {
    const url = new URL(route.request().url()).pathname;
    if (url === "/consultations/mode") {
      await route.fulfill({ json: { provider: "gemini", model: "gemini-3.8-flash" } }); return;
    }
    const state = { id: identity, primary_service: "hairstyle", stage: "collecting",
      photo: null, messages: [], recommendations: null, generations: [], selected_recommendation_id: null };
    if (url === "/consultations") {
      creates++;
      await route.fulfill({ status: 201, json: state }); return;
    }
    if (url.endsWith("/photo")) {
      await route.fulfill({ json: { ...state, photo: { id: identity, content_type: "image/png", width: 128, height: 128 } } }); return;
    }
    if (url.endsWith("/turn")) {
      openingCalls++;
      if (openingCalls === 1) {
        await route.fulfill({ status: 503, json: { detail: "The AI consultant is unavailable. Please try again shortly." } });
      } else {
        await route.fulfill({ json: { state: { ...state, messages: [
          { role: "assistant", content: "What are you getting ready for?", created_at: "2026-09-30T00:00:00Z" }] },
        status: "more_information", assistant_message: "What are you getting ready for?", recommendations: null } });
      }
      return;
    }
    await route.fulfill({ status: 404 });
  });
  await page.goto("/consultation");
  await page.getByLabel("Upload consultation photo").setInputFiles({ name: "test.png", mimeType: "image/png", buffer: photo });
  await page.getByRole("button", { name: /Start AI consultation/ }).click();
  await expect(page.locator(".studio-alert")).toContainText("unavailable");
  await page.getByRole("button", { name: "Retry opening question" }).click();
  await expect(page.getByRole("log")).toContainText("What are you getting ready for?");
  expect(creates).toBe(1);
  expect(openingCalls).toBe(2);
});
