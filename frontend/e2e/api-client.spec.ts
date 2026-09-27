import { expect, test } from "@playwright/test";
import { ApiError, API_BASE_URL, generate, getFeatures, getStyles, type FeatureId } from "../lib/api";

const originalFetch = globalThis.fetch;
test.afterEach(() => { globalThis.fetch = originalFetch; });

test("feature discovery uses the central API", async () => {
  globalThis.fetch = async (url, init) => {
    expect(url).toBe(`${API_BASE_URL}/features`);
    expect(init?.cache).toBe("no-store");
    return Response.json([{ id: "nails", name: "Nails", description: "Hand photo" }]);
  };
  expect(await getFeatures()).toEqual([{ id: "nails", name: "Nails", description: "Hand photo" }]);
});

for (const feature of ["hairstyle", "makeup", "nails"] satisfies FeatureId[]) {
  test(`${feature} sends its feature route and multipart fields and parses the result`, async () => {
    const file = new File(["portrait bytes"], "portrait.png", { type: "image/png" });
    const result = { status: "completed", generator: "test", style: { id: "selected" }, image: { data_url: "data:image/png;base64,test" } };
    let calls = 0;
    globalThis.fetch = async (url, init) => {
      calls++;
      if (calls === 1) {
        expect(url).toBe(`${API_BASE_URL}/features/${feature}/styles`);
        return Response.json([{ id: "selected", name: "Selected", description: "Test", status: "available" }]);
      }
      expect(url).toBe(`${API_BASE_URL}/features/${feature}/generate`);
      expect(init?.method).toBe("POST");
      expect(init?.headers).toBeUndefined(); // fetch must supply the multipart boundary
      const form = init?.body as FormData;
      expect([...form.keys()]).toEqual(["image", "style_id"]);
      expect(form.get("style_id")).toBe("selected");
      expect((form.get("image") as File).name).toBe(file.name);
      expect(await (form.get("image") as File).text()).toBe("portrait bytes");
      return Response.json(result);
    };
    expect((await getStyles(feature))[0].id).toBe("selected");
    expect(await generate(feature, file, "selected")).toEqual(result);
    expect(calls).toBe(2);
  });
}

for (const [status, detail, code] of [
  [400, "Please choose a valid hairstyle.", "invalid_style"],
  [415, "Please upload a JPG or PNG image.", "invalid_image"],
  [404, "Unknown feature.", "invalid_feature"],
  [502, "The Makeup GPU is busy.", "inference_failed"],
  [504, "Internal timeout details", "timeout"],
] as const) {
  test(`HTTP ${status} has a normalized error and never falls back`, async () => {
    let calls = 0;
    globalThis.fetch = async () => { calls++; return Response.json({ detail }, { status }); };
    const error = await getStyles("makeup").catch((error) => error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe(code);
    expect(error.status).toBe(status);
    expect(error.message).toBe(status === 504 ? "The request timed out. Please try again." : detail);
    expect(calls).toBe(1);
  });
}

test("validation arrays, network failure, timeout and unreadable responses are safe", async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ msg: "Field required" }] }, { status: 422 });
  await expect(getStyles("makeup")).rejects.toMatchObject({ code: "invalid_request", message: "Field required" });
  globalThis.fetch = async () => { throw new TypeError("internal network detail"); };
  await expect(getStyles("nails")).rejects.toMatchObject({ code: "backend_unavailable", message: expect.stringContaining("The backend is unavailable") });
  globalThis.fetch = async () => { throw new DOMException("internal detail", "TimeoutError"); };
  await expect(getStyles("nails")).rejects.toMatchObject({ code: "timeout" });
  globalThis.fetch = async () => new Response("<html>internal traceback</html>", { status: 502 });
  await expect(getStyles("nails")).rejects.toMatchObject({ code: "inference_failed", message: "The request could not be completed. Please try again." });
  globalThis.fetch = async () => new Response("not JSON");
  await expect(getStyles("nails")).rejects.toMatchObject({ code: "invalid_response" });
});
