import {afterEach, describe, expect, it, vi} from "vitest";
import {api, ApiError, isActive, percent} from "./api";

afterEach(() => vi.unstubAllGlobals());
describe("operational API", () => {
  it("exposes a safe server validation error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:"Plan expired"}), {status:409})));
    await expect(api("/test", {})).rejects.toEqual(new ApiError("Plan expired", 409));
  });
  it("handles a proxy outage without a JSON payload", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Unavailable", {status:502})));
    await expect(api("/test")).rejects.toThrow("Request failed (502)");
  });
  it("distinguishes active incidents and formats small error rates", () => {
    expect(isActive("RESOLVED")).toBe(false);
    expect(isActive("AWAITING_APPROVAL")).toBe(true);
    expect(percent(.002)).toBe("0.2%");
  });
});
