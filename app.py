import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(page_title="뉴스 자동 스크랩", layout="wide")

st.title("📈 뉴스 실시간 자동 수집기")

# 2. 세션 상태 초기화
if "saved_titles" not in st.session_state:
    st.session_state.saved_titles = set()
if "articles_list" not in st.session_state:
    st.session_state.articles_list = []
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = ""

# 실시간 인기글 전용 세션 상태
if "trending_saved_titles" not in st.session_state:
    st.session_state.trending_saved_titles = set()
if "trending_articles" not in st.session_state:
    st.session_state.trending_articles = []


# 3. 유틸리티 함수
def parse_pub_date(pub_date_str):
    """날짜 문자열 파싱 및 한국 표준시(KST) 변환"""
    if not pub_date_str:
        return datetime.min.replace(tzinfo=timezone.utc), "-"
    try:
        dt = parsedate_to_datetime(pub_date_str)
        kst = timezone(timedelta(hours=9))
        dt_kst = dt.astimezone(kst)
        return dt_kst, dt_kst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc), pub_date_str


def fetch_search_news(search_keyword):
    """키워드 검색 뉴스 수집 (중복 제외 및 누적)"""
    if not search_keyword.strip() or search_keyword == "검색어를 입력하고 Enter를 누르세요":
        return []

    encoded_keyword = urllib.parse.quote(search_keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    new_articles = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date_raw = item.findtext("pubDate", "")

                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]

                clean_title = title.strip()
                if clean_title and link and clean_title not in st.session_state.saved_titles:
                    st.session_state.saved_titles.add(clean_title)
                    dt_obj, formatted_date = parse_pub_date(pub_date_raw)
                    new_articles.append(
                        {
                            "title": clean_title,
                            "link": link,
                            "dt": dt_obj,
                            "pub_date": formatted_date,
                        }
                    )
    except Exception as e:
        st.error(f"검색 뉴스 수집 중 오류: {e}")

    return new_articles


def fetch_trending_news():
    """구글 트렌드 실시간 인기 검색어 RSS 수집 (중복 제외 및 누적)"""
    url = "https://trends.google.co.kr/trending/rss?geo=KR"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    new_articles = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                trend_title = item.findtext("title", "")
                pub_date_raw = item.findtext("pubDate", "")
                
                news_items = item.findall("{https://trends.google.com/trending/rss}news_item")
                if news_items:
                    for news in news_items:
                        title = news.findtext("{https://trends.google.com/trending/rss}news_item_title", "")
                        link = news.findtext("{https://trends.google.com/trending/rss}news_item_url", "")
                        clean_title = title.strip() if title else trend_title.strip()
                        
                        if clean_title and clean_title not in st.session_state.trending_saved_titles:
                            st.session_state.trending_saved_titles.add(clean_title)
                            dt_obj, formatted_date = parse_pub_date(pub_date_raw)
                            new_articles.append({
                                "title": f"[{trend_title}] {clean_title}",
                                "link": link if link else "https://trends.google.co.kr",
                                "dt": dt_obj,
                                "pub_date": formatted_date
                            })
                else:
                    link = item.findtext("link", "")
                    clean_title = trend_title.strip()
                    if clean_title and clean_title not in st.session_state.trending_saved_titles:
                        st.session_state.trending_saved_titles.add(clean_title)
                        dt_obj, formatted_date = parse_pub_date(pub_date_raw)
                        new_articles.append({
                            "title": clean_title,
                            "link": link,
                            "dt": dt_obj,
                            "pub_date": formatted_date
                        })
    except Exception as e:
        st.error(f"실시간 인기글 수집 중 오류: {e}")

    return new_articles


def fetch_rss_news(url):
    """일반 RSS 헤드라인 단발 조회"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date_raw = item.findtext("pubDate", "")

                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]

                if title and link:
                    dt_obj, formatted_date = parse_pub_date(pub_date_raw)
                    articles.append(
                        {
                            "title": title.strip(),
                            "link": link,
                            "dt": dt_obj,
                            "pub_date": formatted_date,
                        }
                    )
            articles.sort(key=lambda x: x["dt"], reverse=True)
    except Exception as e:
        st.error(f"뉴스 수집 중 오류: {e}")

    return articles


# 4. 상단 컨트롤 레이아웃
col_input, col_refresh, col_reset = st.columns([3.8, 1.1, 1.1])

with col_input:
    keyword = st.text_input(
        "검색어",
        value="",
        placeholder="검색어를 입력하고 Enter를 누르세요",
        label_visibility="collapsed",
    )

with col_refresh:
    refresh_clicked = st.button("🔄 새로고침", use_container_width=True)

with col_reset:
    if st.button("🗑️ 검색목록 초기화", use_container_width=True):
        st.session_state.articles_list = []
        st.session_state.saved_titles = set()
        st.session_state.last_keyword = ""
        st.rerun()

# 상단 '🔄 새로고침' 클릭 시 모든 수집 리스트를 초기화하여 최신 데이터로 다시 스크랩
if refresh_clicked:
    st.session_state.articles_list = []
    st.session_state.saved_titles = set()
    st.session_state.trending_articles = []
    st.session_state.trending_saved_titles = set()
    st.rerun()

# 검색어 변경 제어
if keyword != st.session_state.last_keyword:
    st.session_state.articles_list = []
    st.session_state.saved_titles = set()
    st.session_state.last_keyword = keyword

# 5. 백그라운드 인기글 스크랩 실행
new_trending = fetch_trending_news()
if new_trending:
    all_trending = new_trending + st.session_state.trending_articles
    all_trending.sort(key=lambda x: x["dt"], reverse=True)
    st.session_state.trending_articles = all_trending

st.divider()

# 6. 메인 화면 탭 구성
tab1, tab2, tab3 = st.tabs(
    [
        "📰 구글 메인 헤드라인",
        "🔍 키워드 검색 뉴스",
        "🔥 실시간 인기 트렌드 뉴스",
    ]
)

with tab1:
    st.subheader("📰 구글 주요 메인 헤드라인")
    main_news = fetch_rss_news(
        "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    )

    if not main_news:
        st.warning("메인 뉴스를 불러올 수 없습니다.")
    else:
        for idx, item in enumerate(main_news[:15], 1):
            col1, col2 = st.columns([4.5, 2])
            with col1:
                st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
            with col2:
                st.caption(f"작성일: {item['pub_date']}")

with tab2:
    if keyword.strip():
        new_fetched = fetch_search_news(keyword)
        if new_fetched:
            all_articles = new_fetched + st.session_state.articles_list
            all_articles.sort(key=lambda x: x["dt"], reverse=True)
            st.session_state.articles_list = all_articles

    st.subheader(
        f"'{keyword}' 검색 결과 (총 {len(st.session_state.articles_list)}개 스크랩됨)"
    )

    if not st.session_state.articles_list:
        st.info(
            "수집된 키워드 뉴스가 없습니다. 상단 검색창에 키워드를 입력해 주세요."
        )
    else:
        for idx, item in enumerate(st.session_state.articles_list[:30], 1):
            col1, col2 = st.columns([4.5, 2])
            with col1:
                st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
            with col2:
                st.caption(f"작성일: {item['pub_date']}")

with tab3:
    st.subheader(
        f"🔥 누적 수집된 실시간 인기 트렌드 뉴스 (총 {len(st.session_state.trending_articles)}개)"
    )

    if not st.session_state.trending_articles:
        st.info("수집된 실시간 인기 뉴스가 없습니다.")
    else:
        for idx, item in enumerate(st.session_state.trending_articles[:50], 1):
            col1, col2 = st.columns([4.5, 2])
            with col1:
                st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
            with col2:
                st.caption(f"작성일: {item['pub_date']}")