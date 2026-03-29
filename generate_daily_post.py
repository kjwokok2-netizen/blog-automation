import yfinance as yf
import datetime
import os
import google.generativeai as genai

# API 키 설정
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("API 키가 없습니다. GitHub Secrets를 확인하세요.")

genai.configure(api_key=API_KEY)

# 모델 설정 (에러 방지를 위해 명칭 보정)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_market_data():
    tickers = {'S&P 500': '^GSPC', 'NASDAQ': '^IXIC', 'KOSPI': '^KS11'}
    market_data = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="2d")
            if len(hist) >= 2:
                close_today = hist['Close'].iloc[-1]
                close_yest = hist['Close'].iloc[-2]
                change = close_today - close_yest
                change_pct = (change / close_yest) * 100
                market_data[name] = f"{close_today:,.2f} ({'+' if change > 0 else ''}{change:.2f}, {'+' if change > 0 else ''}{change_pct:.2f}%)"
            else: market_data[name] = "데이터 지연"
        except: market_data[name] = "수집 오류"
    return market_data

def get_latest_news():
    target_tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA']
    news_summaries = []
    for ticker in target_tickers:
        try:
            news = yf.Ticker(ticker).news
            for item in news[:2]:
                news_summaries.append(f"[{ticker}] {item['title']}")
        except: continue
    return "\n".join(news_summaries)

def create_daily_post():
    # 한국 시간 설정
    utc_now = datetime.datetime.utcnow()
    kst_now = utc_now + datetime.timedelta(hours=9)
    date_str = kst_now.strftime('%Y-%m-%d')
    
    # 블로그 인식을 위해 _posts 폴더에 저장 (폴더 없으면 생성)
    if not os.path.exists('_posts'):
        os.makedirs('_posts')
    file_name = f"_posts/{date_str}-daily-market-report.md"

    market_data = get_market_data()
    latest_news = get_latest_news()

    prompt = f"""
    당신은 월스트리트 전문가입니다. 다음 데이터를 바탕으로 리포트를 작성하세요.
    데이터: {market_data}
    뉴스: {latest_news}
    
    [규칙]
    1. 차트/파동 분석 절대 금지.
    2. 최근 매크로 이슈, 기업 펀더멘털, 시장 전망만 다룰 것.
    3. 100% 팩트 중심, 불확실하면 '근거 부족' 명시.
    4. 해시태그 금지, 존댓말 사용.
    5. 마크다운 형식으로 본문만 출력.
    """

    try:
        response = model.generate_content(prompt)
        ai_content = response.text
    except Exception as e:
        ai_content = f"내용 생성 실패: {str(e)}"

    final_content = f"""---
layout: post
title: "[{date_str}] 글로벌 증시 이슈 및 기업 분석 리포트"
date: {kst_now.strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: [Market-Report]
---

## 📊 {date_str} 주요 증시 지표
- **S&P 500**: {market_data.get('S&P 500')}
- **NASDAQ**: {market_data.get('NASDAQ')}
- **KOSPI**: {market_data.get('KOSPI')}

---

{ai_content}
"""
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(final_content)

if __name__ == "__main__":
    create_daily_post()
