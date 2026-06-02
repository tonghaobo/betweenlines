"""
生产环境验证脚本
使用方法：PROD_URL=https://betweenlines-api.railway.app python tests/test_production.py
"""
import os
import httpx
import asyncio

PROD_URL = os.getenv("PROD_URL", "http://localhost:8000")

SAMPLE_CHAT = """A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢"""


async def test_health():
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{PROD_URL}/health")
        print(f"✅ Health: {response.status_code} - {response.json()}")
        assert response.status_code == 200


async def test_cors():
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.options(
            f"{PROD_URL}/api/v1/analyze",
            headers={
                "Origin": "https://betweenlines.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )
        print(f"✅ CORS preflight: {response.status_code}")
        assert "access-control-allow-origin" in response.headers


async def test_analyze():
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{PROD_URL}/api/v1/analyze",
            json={"chat_content": SAMPLE_CHAT},
        )
        data = response.json()
        print(f"✅ Analyze: {response.status_code} - status={data.get('chat_status')}")
        assert response.status_code == 200
        assert "chat_status" in data
        assert "reply_suggestions" in data


async def test_rate_limit():
    async with httpx.AsyncClient(timeout=10.0) as client:
        responses = []
        for i in range(25):
            response = await client.post(
                f"{PROD_URL}/api/v1/analyze",
                json={"chat_content": "A: hi\nB: hello"},
            )
            responses.append(response.status_code)
        
        has_429 = 429 in responses
        print(f"✅ Rate limit: {'429 returned' if has_429 else 'No rate limiting detected'}")


async def main():
    print("=" * 50)
    print(f"Production Validation: {PROD_URL}")
    print("=" * 50)
    
    await test_health()
    await test_cors()
    await test_analyze()
    await test_rate_limit()
    
    print("\n✅ All production tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
