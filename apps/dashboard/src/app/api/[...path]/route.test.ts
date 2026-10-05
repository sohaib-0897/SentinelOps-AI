import {afterEach, describe, expect, it, vi} from "vitest";
import {NextRequest} from "next/server";
import {GET, POST} from "./route";

afterEach(() => {vi.unstubAllGlobals(); vi.unstubAllEnvs();});
const context = (path: string[] = ["v1","incidents"]) => ({params:Promise.resolve({path})});

describe("server API trust boundary", () => {
  it("rejects path traversal and cross-origin mutation before contacting upstream", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch",fetch);
    expect((await GET(new NextRequest("http://dashboard/api/v1/test"),context(["v1","..","health"]))).status).toBe(400);
    expect((await POST(new NextRequest("http://dashboard/api/v1/test",{method:"POST",headers:{Origin:"http://attacker",Host:"dashboard"}}),context())).status).toBe(403);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("bounds proxy body bytes before forwarding", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch",fetch);
    const request = new NextRequest("http://dashboard/api/v1/telemetry",{method:"POST",body:"x".repeat(1_000_001)});
    expect((await POST(request,context(["v1","telemetry"]))).status).toBe(413);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("keeps the operator credential on the server side", async () => {
    vi.stubEnv("API_OPERATOR_TOKEN","test-server-only-token");
    const fetch = vi.fn().mockResolvedValue(new Response('{"state":"healthy"}',{headers:{"Content-Type":"application/json"}}));
    vi.stubGlobal("fetch",fetch);
    const response = await GET(new NextRequest("http://dashboard/api/v1/incidents"),context());
    expect(fetch.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer test-server-only-token");
    expect(response.headers.get("Authorization")).toBeNull();
    expect(await response.text()).not.toContain("test-server-only-token");
  });
});
