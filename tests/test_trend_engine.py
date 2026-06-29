from trend_engine import GoogleTrendingNowSource, YouTubeTrendSource, manual_tiktok_trend, trend_score


class FakeHttp:
    def __init__(self, json_responses=None, byte_response=b""):
        self.json_responses = list(json_responses or [])
        self.byte_response = byte_response
        self.calls = []

    def request_json(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.json_responses.pop(0)

    def request_bytes(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.byte_response


def test_trend_score_uses_weighted_components():
    score = trend_score(100, 100, 0, 0, 0, 0)
    assert score == 50.0


def test_manual_tiktok_trend_is_scored():
    item = manual_tiktok_trend(
        "Natural makeup hook",
        niche="Beauty",
        region="US",
        strength=80,
        niche_fit=90,
        monetization=70,
        originality=60,
        production_ease=75,
        url="https://www.tiktok.com/example",
    )
    assert item.source == "TikTok manual"
    assert item.score > 70
    assert item.url.startswith("https://")


def test_google_trending_rss_is_parsed_and_scored():
    xml = b"""<?xml version='1.0' encoding='UTF-8'?>
    <rss xmlns:ht='https://trends.google.com/trending/rss'><channel>
      <item>
        <title>New skincare routine</title>
        <link>https://trends.google.com/example</link>
        <ht:approx_traffic>100K+</ht:approx_traffic>
      </item>
    </channel></rss>"""
    source = GoogleTrendingNowSource(http=FakeHttp(byte_response=xml))

    items = source.fetch(niche="Beauty", niche_keywords=["skincare"], region="US")

    assert len(items) == 1
    assert items[0].title == "New skincare routine"
    assert items[0].niche_fit >= 70
    assert items[0].metadata["approx_traffic"] == "100K+"


def test_youtube_search_combines_search_and_statistics():
    http = FakeHttp(
        json_responses=[
            {
                "items": [
                    {
                        "id": {"videoId": "abc123"},
                        "snippet": {"title": "Eyeliner tutorial"},
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": "abc123",
                        "snippet": {
                            "title": "Eyeliner tutorial",
                            "channelTitle": "Creator",
                            "publishedAt": "2026-06-28T10:00:00Z",
                        },
                        "statistics": {"viewCount": "100000", "likeCount": "7000", "commentCount": "500"},
                    }
                ]
            },
        ]
    )
    source = YouTubeTrendSource(api_key="test", http=http)

    items = source.search(
        "beauty tips",
        niche="Beauty",
        niche_keywords=["eyeliner", "makeup"],
        region="US",
        days=14,
        max_results=10,
    )

    assert len(items) == 1
    assert items[0].metadata["views"] == 100000
    assert items[0].url.endswith("abc123")
    assert len(http.calls) == 2
