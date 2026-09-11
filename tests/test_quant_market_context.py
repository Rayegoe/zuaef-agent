"""Bounded market-wide evidence contract tests (Task Boundary Repair P2)."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from zuaef_quant import market_context


class FakeFrame:
    """Tiny pandas-like stand-in: the adapter only needs ``to_dict``."""

    def __init__(self, rows):
        self._rows = [dict(row) for row in rows]

    def to_dict(self, orient="records"):
        if orient != "records":
            raise TypeError("unsupported orient")
        return [dict(row) for row in self._rows]


def _complete_akshare(news_rows: int = 3) -> SimpleNamespace:
    index_rows = [
        {"名称": "上证指数", "代码": "000001", "最新价": 3200.5, "涨跌幅": -1.2,
         "成交额": 500_000_000_000, "最新行情时间": "2026-09-11 15:00:00"},
        {"名称": "深证成指", "代码": "399001", "最新价": 10000.0, "涨跌幅": -1.5,
         "成交额": 600_000_000_000, "最新行情时间": "2026-09-11 15:00:00"},
        {"名称": "创业板指", "代码": "399006", "最新价": 2000.0, "涨跌幅": -2.0,
         "成交额": 200_000_000_000, "最新行情时间": "2026-09-11 15:00:00"},
        {"名称": "沪深300", "代码": "000300", "最新价": 3800.0, "涨跌幅": -1.1,
         "成交额": 300_000_000_000, "最新行情时间": "2026-09-11 15:00:00"},
        {"名称": "科创50", "代码": "000688", "最新价": 900.0, "涨跌幅": -2.5,
         "成交额": 50_000_000_000, "最新行情时间": "2026-09-11 15:00:00"},
    ]
    spot_rows = [
        {"涨跌幅": 1.0, "成交额": 10},
        {"涨跌幅": -2.0, "成交额": 20},
        {"涨跌幅": 0.0, "成交额": 30},
        {"涨跌幅": None, "成交额": None},
    ]
    sector_rows = [
        {"板块名称": "煤炭", "涨跌幅": 3.2},
        {"板块名称": "石油", "涨跌幅": 2.4},
        {"板块名称": "券商", "涨跌幅": -4.5},
        {"板块名称": "软件", "涨跌幅": -3.8},
        {"板块名称": "银行", "涨跌幅": -1.2},
    ]
    global_rows = [
        {"名称": "恒生指数", "代码": "HSI", "最新价": 25000, "涨跌幅": -1.6,
         "最新行情时间": "2026-09-11 16:00:00"},
        {"名称": "日经225", "代码": "N225", "最新价": 38000, "涨跌幅": -2.1,
         "最新行情时间": "2026-09-11 15:00:00"},
        {"名称": "韩国KOSPI", "代码": "KS11", "最新价": 2600, "涨跌幅": -1.9,
         "最新行情时间": "2026-09-11 15:00:00"},
        {"名称": "美元指数", "代码": "UDI", "最新价": 105.4, "涨跌幅": 0.8,
         "最新行情时间": "2026-09-11 05:00:00"},
    ]
    futures_rows = [
        {"名称": "布伦特原油", "最新价": 92.3, "涨跌幅": 4.2,
         "最新行情时间": "2026-09-11 05:00:00"},
        {"名称": "WTI原油", "最新价": 89.1, "涨跌幅": 4.0,
         "最新行情时间": "2026-09-11 05:00:00"},
    ]
    rate_rows = [
        {"日期": "2026-09-10", "美国国债收益率10年": 4.1},
        {"日期": "2026-09-11", "美国国债收益率10年": 4.3},
    ]
    em_news = [
        {
            "标题": f"全球宏观快讯 {i}",
            "发布时间": "2026-09-11 08:00:00",
            "链接": f"https://example.com/news/{i}",
        }
        for i in range(news_rows)
    ]
    return SimpleNamespace(
        stock_zh_index_spot_em=lambda symbol="沪深重要指数": FakeFrame(index_rows),
        stock_zh_a_spot_em=lambda: FakeFrame(spot_rows),
        stock_market_activity_legu=lambda: FakeFrame(
            [{"item": "上涨", "value": "3000家"}, {"item": "下跌", "value": "1800家"}]
        ),
        stock_board_industry_name_em=lambda: FakeFrame(sector_rows),
        index_global_spot_em=lambda: FakeFrame(global_rows),
        futures_global_spot_em=lambda: FakeFrame(futures_rows),
        bond_zh_us_rate=lambda start_date="19901219": FakeFrame(rate_rows),
        stock_info_global_em=lambda: FakeFrame(em_news),
        # fallbacks raise so "complete" fixture does not accidentally use them
        stock_zh_index_spot_sina=lambda: (_ for _ in ()).throw(RuntimeError("no fallback")),
        stock_info_global_cls=lambda symbol="全部": (_ for _ in ()).throw(RuntimeError("no fallback")),
    )


def test_complete_bounded_contract(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "akshare", _complete_akshare(news_rows=8))
    data = market_context.collect(limit=7)

    assert data["as_of"]
    assert data["evidence_scope"] == "A_SHARE_MARKET_WIDE"
    assert [row["name"] for row in data["a_share"]["indices"]] == [
        "上证指数", "深证成指", "创业板指", "沪深300", "科创50"
    ]
    assert data["a_share"]["breadth"] == {
        "up": 1, "down": 1, "flat": 1, "advance_decline_ratio": 1.0
    }
    assert data["a_share"]["turnover"]["total_cny"] == 60.0
    sectors = data["a_share"]["sectors"]
    assert len(sectors["leaders"]) <= 5
    assert len(sectors["laggards"]) <= 5
    assert sectors["leaders"][0]["name"] == "煤炭"
    assert sectors["laggards"][0]["name"] == "券商"
    assert data["external"]["energy"]["brent"]["level"] == 92.3
    assert data["external"]["energy"]["wti"]["change_pct"] == 4.0
    assert data["external"]["rates"]["us_10y"]["value_pct"] == 4.3
    assert data["external"]["fx"]["dollar_index"]["level"] == 105.4
    assert {row["name"] for row in data["external"]["asia_indices"]} >= {
        "恒生指数", "日经225", "韩国KOSPI"
    }
    assert data["missing"] == []
    # News is bounded and carries no article bodies.
    assert len(data["news"]) == 7
    assert data["news"][0]["source"] == "东方财富"
    assert data["news"][0]["published_at"] == "2026-09-11 08:00:00"
    assert data["news"][0]["url"].startswith("https://")


def test_news_count_is_bounded_to_hard_max(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "akshare", _complete_akshare(news_rows=40))
    data = market_context.collect(limit=999)
    assert len(data["news"]) == market_context.MAX_NEWS


def test_missing_values_stay_missing_and_never_become_candidate_data(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(),  # every optional feed is unavailable
    )
    data = market_context.collect()
    assert data["evidence_scope"] == "A_SHARE_MARKET_WIDE"
    assert data["a_share"]["indices"] == []
    assert data["a_share"]["breadth"]["up"] is None
    assert data["a_share"]["breadth"]["down"] is None
    assert data["a_share"]["turnover"]["total_cny"] is None
    assert data["a_share"]["sectors"]["leaders"] == []
    assert data["external"]["energy"]["brent"] is None
    assert data["external"]["rates"]["us_10y"] is None
    assert data["news"] == []
    assert "a_share.indices" in data["missing"]
    assert "a_share.breadth" in data["missing"]
    assert "a_share.turnover" in data["missing"]
    assert "news" in data["missing"]
    # No candidate-pool/account fallback, no fabricated zero breadth.
    serialized = str(data)
    assert "CANDIDATE_POOL" not in serialized
    assert "TRADING_ACCOUNT" not in serialized
    assert "universe_count" not in serialized


def test_index_null_fields_remain_null(tmp_path, monkeypatch):
    ak = _complete_akshare()
    ak.stock_zh_index_spot_em = lambda symbol="沪深重要指数": FakeFrame(
        [
            {"名称": "上证指数", "代码": "000001", "最新价": None,
             "涨跌幅": None, "成交额": None, "最新行情时间": None}
        ]
    )
    monkeypatch.setitem(sys.modules, "akshare", ak)
    data = market_context.collect()
    sh = data["a_share"]["indices"][0]
    assert sh["name"] == "上证指数"
    assert sh["level"] is None
    assert sh["change_pct"] is None
    assert sh["turnover_cny"] is None
    assert sh["observed_at"] is None


def test_network_fallback_feeds_fill_sectors_external_and_dollar_proxy(
    tmp_path, monkeypatch
):
    """The deployment's EastMoney push2 endpoint is often blocked; bounded
    non-EastMoney fallbacks must fill what akshare can still provide without
    fabricating anything."""

    def fake_hist(symbol):
        return FakeFrame(
            [
                {"date": "2026-09-10", "close": 100.0},
                {"date": "2026-09-11", "close": 98.0},
            ]
        )

    ak = SimpleNamespace(
        stock_board_industry_summary_ths=lambda: FakeFrame(
            [{"板块": "证券", "涨跌幅": -3.6}, {"板块": "煤炭", "涨跌幅": 1.2}]
        ),
        stock_hk_index_spot_sina=lambda: FakeFrame(
            [{"代码": "HSI", "名称": "恒生指数", "最新价": 24805.6, "涨跌幅": -0.6}]
        ),
        index_global_hist_sina=fake_hist,
        bond_zh_us_rate=lambda start_date="19901219": FakeFrame(
            [{"日期": "2026-09-10", "美国国债收益率10年": 4.3}]
        ),
        currency_boc_sina=lambda symbol="美元", start_date="", end_date="": FakeFrame(
            [
                {"日期": "2026-09-10", "央行中间价": 6.80},
                {"日期": "2026-09-11", "央行中间价": 6.79},
            ]
        ),
    )
    monkeypatch.setitem(sys.modules, "akshare", ak)
    data = market_context.collect()
    sectors = data["a_share"]["sectors"]
    assert sectors["count"] == 2
    assert sectors["laggards"][0]["name"] == "证券"
    assert data["external"]["fx"]["dollar_index"]["name"] == "USD/CNY proxy"
    assert data["external"]["fx"]["dollar_index"]["proxy"] == "currency_boc_sina"
    names = {row["name"] for row in data["external"]["asia_indices"]}
    assert {"恒生指数", "日经225", "韩国KOSPI"} <= names
    assert "external.asia_indices" not in data["missing"]
