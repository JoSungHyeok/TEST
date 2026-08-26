import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

st.set_page_config(
    page_title="주식 뉴스 자동 스크랩", 
    layout="wide"
)

# 사이드바 화살표 아이콘을 '🔍 검색' 버튼으로 교체
st.markdown("""
    <style>
        [data-testid="collapsedControl"] svg {
            display: none !important;
        }
        [data-testid="collapsedControl"] button::after {
            content: "🔍 검색";
            font-size: 14px;
            font-weight: bold;
            color: #333;
        }
        [data-testid="collapsedControl"] button {
            width: auto !important;
            padding: 4px 12px !important;
            border: 1px solid #ccc !important;
            border-radius: 6px !important;
            background-color: #f8f9fa !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 뉴스 실시간 자동 수집기")

# 세션 상태 초기화
if "saved_links" not in st.session_state:
    st.session_state.saved_links = set()
if "articles_list" not in st.session_state:
    st.session_state.articles_list = []

# 상단 컨트롤 영역
col_input, col_check, col_btn = st.columns([3.5, 1.2, 1])

with col_input:
    keyword = st.text_input("검색어", " ", placeholder="키워드를 입력 후 Enter를 누르세요", label_visibility="collapsed")
with col_check:
    auto_refresh = st.checkbox("30초 자동 새로고침", value=False)
with col_btn:
    if st.button("목록 초기화", use_container_width=True):
        st.session_state.articles_list = []
        st.session_state.saved_links = set()
        st.rerun()

st.divider()

# 연도-월-일 시:분까지 명확히 파싱하는 함수
def parse_pub_date(pub_date_str):
    if not pub_date_str:
        return datetime.min.replace(tzinfo=timezone.utc), "-"
    try:
        dt = parsedate_to_datetime(pub_date_str)
        kst = timezone(timedelta(hours=9))
        dt_kst = dt.astimezone(kst)
        # YYYY-MM-DD HH:MM 서식 지정 (예: 2026-08-26 16:50)
        formatted_str = dt_kst.strftime("%Y-%m-%d %H:%M")
        return dt_kst, formatted_str
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc), pub_date_str

# 1. 키워드 검색 뉴스 수집
def fetch_search_news(search_keyword):
    if not search_keyword.strip():
        return []
    
    encoded_keyword = urllib.parse.quote(search_keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
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
                
                if title and link and link not in st.session_state.saved_links:
                    st.session_state.saved_links.add(link)
                    dt_obj, formatted_date = parse_pub_date(pub_date_raw)
                    new_articles.append({
                        "title": title, 
                        "link": link, 
                        "dt": dt_obj,
                        "pub_date": formatted_date
                    })
    except Exception as e:
        st.error(f"검색 뉴스 수집 중 오류: {e}")
        
    return new_articles

# 2. 메인 헤드라인 뉴스 수집
@st.cache_data(ttl=300)
def fetch_main_headlines():
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    headlines = []
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
                    headlines.append({
                        "title": title, 
                        "link": link, 
                        "dt": dt_obj,
                        "pub_date": formatted_date
                    })
            headlines.sort(key=lambda x: x["dt"], reverse=True)
    except Exception as e:
        st.error(f"메인 뉴스 수집 중 오류: {e}")
        
    return headlines

# 화면 출력부
tab1, tab2 = st.tabs(["🔍 키워드 검색 뉴스", "📰 구글 메인 헤드라인"])

with tab1:
    @st.fragment(run_every=30 if auto_refresh else None)
    def render_search_section():
        new_fetched = fetch_search_news(keyword)
        if new_fetched:
            all_articles = new_fetched + st.session_state.articles_list
            all_articles.sort(key=lambda x: x["dt"], reverse=True)
            st.session_state.articles_list = all_articles

        st.subheader(f"'{keyword}' 검색 결과 (총 {len(st.session_state.articles_list)}개)")

        if not st.session_state.articles_list:
            st.info("수집된 키워드 뉴스가 없습니다. 상단 검색창에 키워드를 입력해 주세요.")
        else:
            for idx, item in enumerate(st.session_state.articles_list[:20], 1):
                col1, col2 = st.columns([4.5, 2])
                with col1:
                    st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
                with col2:
                    st.caption(f"작성일: {item['pub_date']}")

    render_search_section()

with tab2:
    st.subheader("🔥 실시간 주요 헤드라인 뉴스")
    main_news = fetch_main_headlines()
    
    if not main_news:
        st.warning("메인 뉴스를 불러올 수 없습니다.")
    else:
        for idx, item in enumerate(main_news[:15], 1):
            col1, col2 = st.columns([4.5, 2])
            with col1:
                st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
            with col2:
                st.caption(f"작성일: {item['pub_date']}")