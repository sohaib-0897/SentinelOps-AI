import type {NextRequest} from "next/server";

export const dynamic = "force-dynamic";
let identity: {token: string; expires: number} | null = null;

async function boundedBody(request: NextRequest): Promise<string | undefined> {
  if (!request.body) return undefined;
  const reader = request.body.getReader();
  const decoder = new TextDecoder();
  let size = 0;
  let text = "";
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 1_000_000) throw new RangeError("Request exceeds allowed size");
      text += decoder.decode(value,{stream:true});
    }
    return text + decoder.decode();
  } finally {
    await reader.cancel();
  }
}

async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  if (path[0] !== "v1") return Response.json({detail:"Unknown API version"},{status:404});
  if (path.some(segment => !/^[A-Za-z0-9_-]{1,128}$/.test(segment)) || request.nextUrl.search.length > 8192) return Response.json({detail:"Invalid API path or query"},{status:400});
  const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  const headers = new Headers();
  const operator = process.env.API_OPERATOR_TOKEN;
  if (operator) headers.set("Authorization",`Bearer ${operator}`);
  else if (request.headers.has("Authorization")) headers.set("Authorization",request.headers.get("Authorization")!);
  const audience = process.env.API_AUTH_AUDIENCE;
  try {
    if (audience) {
      if (!identity || identity.expires <= Date.now()) {
        const response = await fetch(`http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(audience)}&format=full`,{headers:{"Metadata-Flavor":"Google"},signal:AbortSignal.timeout(5000)});
        if (!response.ok) throw new Error("Identity unavailable");
        identity = {token:await response.text(), expires:Date.now()+240000};
      }
      headers.set("X-Serverless-Authorization",`Bearer ${identity.token}`);
    }
    if (request.method === "POST") {
      const origin = request.headers.get("Origin");
      if (origin && new URL(origin).host !== request.headers.get("Host")) return Response.json({detail:"Cross-origin mutation rejected"},{status:403});
      headers.set("Content-Type","application/json");
    }
    const target = `${base.replace(/\/$/,"")}/api/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
    const upstream = await fetch(target,{method:request.method,headers,body:request.method === "POST" ? await boundedBody(request) : undefined,cache:"no-store",signal:request.signal});
    return new Response(upstream.body,{status:upstream.status,headers:{"Content-Type":upstream.headers.get("Content-Type") ?? "application/json","Cache-Control":"no-cache, no-transform","X-Accel-Buffering":"no"}});
  } catch (error) {
    if (error instanceof RangeError) return Response.json({detail:"Request exceeds allowed size"},{status:413});
    return Response.json({detail:"Incident API unavailable. Retry after checking the service connection."},{status:502});
  }
}

export {proxy as GET, proxy as POST};
