"""
Chat Coach API 测试脚本
使用方法：python tests/test_api.py
前提：后端服务已启动在 http://localhost:8000
"""
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

SAMPLE_CHAT = """A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢
A: 那快去吃点东西吧
B: 嗯嗯好的"""


async def test_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"[Health] Status: {response.status_code}")
        print(f"[Health] Body: {response.json()}")
        assert response.status_code == 200


async def test_analyze():
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": SAMPLE_CHAT},
        )
        print(f"[Analyze] Status: {response.status_code}")
        data = response.json()
        print(f"[Analyze] Status: {data.get('chat_status')}")
        print(f"[Analyze] Analysis: {data.get('analysis', '')[:100]}...")
        print(f"[Analyze] Issues: {data.get('issues')}")
        print(f"[Analyze] Risks: {data.get('risks')}")
        print(f"[Analyze] Natural Reply: {data.get('reply_suggestions', {}).get('natural', '')}")
        print(f"[Analyze] Timing: {data.get('timing_advice')}")
        assert response.status_code == 200
        assert "chat_status" in data
        assert "reply_suggestions" in data


async def test_analyze_empty():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": "hi"},
        )
        print(f"[Analyze Empty] Status: {response.status_code}")
        assert response.status_code == 400


async def test_feedback():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"helpful": True},
        )
        print(f"[Feedback] Status: {response.status_code}")
        print(f"[Feedback] Body: {response.json()}")
        assert response.status_code == 200


async def test_stats():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/stats")
        print(f"[Stats] Status: {response.status_code}")
        print(f"[Stats] Body: {response.json()}")
        assert response.status_code == 200


async def main():
    print("=" * 50)
    print("Chat Coach API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Chat Analysis", test_analyze),
        ("Empty Input Validation", test_analyze_empty),
        ("Feedback Submission", test_feedback),
        ("Stats Endpoint", test_stats),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            print(f"\n--- {name} ---")
            await test_fn()
            print(f"✅ {name} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {str(e)}")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
