"""Start a named scenario on the running API; never auto-approve remediation."""
import argparse
import asyncio

import httpx

from sentinelops.simulation import scenarios


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario",choices=list(scenarios()))
    parser.add_argument("--api",default="http://127.0.0.1:8000")
    parser.add_argument("--speed",type=float,default=1)
    args = parser.parse_args()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(args.api+"/api/v1/demo/start",json={"scenario":args.scenario})
        response.raise_for_status()
        speed = await client.post(args.api+"/api/v1/demo/speed",json={"speed":args.speed})
        speed.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
