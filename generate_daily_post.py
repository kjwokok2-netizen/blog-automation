import yfinance as yf
import datetime
import os
import google.generativeai as genai

# ==========================================
# 1. API 키 및 환경 설정 (GitHub Actions Secrets 연동)
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("API 키가 설정되지 않았습니다. GitHub Secrets(GEMINI_API_KEY)를 확인하세요.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_market_data():
    """주요 지수 팩트 데이터 수집"""
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
            else:
                market_data[name] = "데이터를 불러올 수 없습니다 (확인 필요)"
        except Exception:
            market_data[name] = "데이터 수집 중 오류 발생"
            
    return market_data

def get_latest_news():
    """시장 동향을 파악하기 위한 주요 ETF/종목의 최신 팩트 뉴스 헤드라인 수집"""
    target_tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA'] 
    news_summaries = []
    
    for ticker in target_tickers:
        try:
            news = yf.Ticker(ticker).news
            for item in news[:3]: # 각 티커당 최신 뉴스 3개씩 수집
                if 'title' in item:
                    news_summaries.append(f"[{ticker}] {item['title']}")
        except Exception:
            continue
            
    if not news_summaries:
        return "최신 뉴스 데이터를 불러올 수 없습니다."
        
    return "\n".join(news_summaries)

def create_daily_post():
    # GitHub 서버 시간(UTC)을 한국 시간(KST, UTC+9)으로 변환
    utc_now = datetime.datetime.utcnow()
    kst_now = utc_now + datetime.timedelta(hours=9)
    date_str = kst_now.strftime('%Y-%m-%d')
    file_name = f"{date_str}-daily-market-report.md"

    print("📊 시장 데이터 및 최신 뉴스를 수집 중입니다...")
    market_data = get_market_data()
    latest_news = get_latest_news()

    print("🤖 AI가 최신 이슈와 기업 분석 글을 100% 자동으로 작성 중입니다...")
    
    # ==========================================
    # 2. AI 프롬프트 (차트 배제, 팩트 기반 이슈/전망 위주)
    # ==========================================
    prompt = f"""
    당신은 객관적이고 날카로운 통찰력을 가진 월스트리트 주식 애널리스트입니다.
    아래 제공된 오늘(한국 시간 {date_str})의 시장 데이터와 최신 뉴스 헤드라인을 바탕으로 일일 증시 리포트를 작성하십시오.

    [오늘의 시장 데이터]
    - S&P 500: {market_data.get('S&P 500')}
    - NASDAQ: {market_data.get('NASDAQ')}
    - KOSPI: {market_data.get('KOSPI')}

    [최신 글로벌 시장 팩트 뉴스 헤드라인]
    {latest_news}

    [작성 규칙 - 매우 중요]
    1. 차트 분석, 기술적 분석, 파동 이론 등은 **일절** 포함하지 마십시오.
    2. 철저하게 '최근 매크로 이슈', '주요 기업의 펀더멘털 및 비즈니스 동향 분석', '향후 시장 전망' 위주로만 작성하십시오.
    3. 100% 팩트에 기반하여 논리적이고 객관적인 어조(존댓말)로 작성하십시오. 충분한 근거가 없거나 정보가 불확실할 경우 '알 수 없습니다' 또는 '근거가 부족합니다'라고 명시하십시오.
    4. 확실한 근거 없이 시장 전망 등 추측이 포함되는 구간은 반드시 '추측한 내용입니다' 또는 '전망됩니다'라고 밝혀주십시오.
    5. 서론, 본론(주요 이슈 및 기업 분석), 결론(시장 전망)의 구조를 갖추십시오. 마크다운 문법(##, -, ** 등)을 사용하여 가독성을 높이십시오.
    6. 글 하단에 해시태그는 절대 생성하지 마십시오.
    7. 인사말이나 불필요한 부연 설명 없이, 마크다운 형식의 본문 내용만 바로 출력하십시오.
    """

    try:
        response = model.generate_content(prompt)
        ai_content = response.text
    except Exception as e:
        ai_content = f"AI 글쓰기 실패: {e}\n\n(근거가 부족하거나 일시적인 오류로 인해 내용을 생성할 수 없습니다.)"

    # ==========================================
    # 3. 최종 파일 포맷팅 및 마크다운 생성
    # ==========================================
    final_content = f"""---
title: "[{date_str}] 글로벌 증시 주요 이슈 및 기업 분석 리포트"
date: {kst_now.strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: [Market Report]
---

## 📊 {date_str} 주요 증시 마감 지표

- **S&P 500**: {market_data.get('S&P 500')}
- **NASDAQ**: {market_data.get('NASDAQ')}
- **KOSPI**: {market_data.get('KOSPI')}

---

{ai_content}
"""

    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"\n✅ 성공: '{file_name}' 파일이 KST 기준으로 작성 및 생성되었습니다.")

if __name__ == "__main__":
    create_daily_post()
