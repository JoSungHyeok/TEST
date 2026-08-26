import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from datetime import timezone, timedelta
from email.utils import parsedate_to_datetime

st.set_page_config(page_title="주식 뉴스 자동 스크랩", layout="wide")

st.title("📈 주식 뉴스 실시간 자동 수집기")

if "saved_links" not in st.session_state:
    st.session_state.saved_links = set()
if "articles_list" not in st.session_state:
    st.session_state.articles_list = []

with st.sidebar:
    st.header("⚙️ 설정")
    keyword = st.text_input("수집할 키워드/종목명", "주식")
    auto_refresh = st.checkbox("자동 새로고침 (30초 마다)", value=False)
    
    if st.button("목록 초기화 및 재수집"):
        st.session_state.articles_list = []
        st.session_state.saved_links = set()
        st.rerun()

# GMT/UTC 날짜를 한국 표준시(KST, UTC+9)로 정확히 변환
def format_pub_date(pub_date_str):
    if not pub_date_str:
        return "-"
    try:
        dt = parsedate_to_datetime(pub_date_str)
        kst = timezone(timedelta(hours=9))
        return dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return pub_date_str

# 안정적인 구글 뉴스 RSS 수집 함수
def fetch_google_news(search_keyword):
    encoded_keyword = urllib.parse.quote(search_keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    new_articles = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate")
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                pub_date = pub_date_elem.text if pub_date_elem is not None else ""
                
                # 언론사명 꼬리표 정리
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                
                if not title or not link:
                    continue
                
                if link not in st.session_state.saved_links:
                    st.session_state.saved_links.add(link)
                    new_articles.append({
                        "title": title, 
                        "link": link, 
                        "pub_date": format_pub_date(pub_date)
                    })
    except Exception as e:
        st.error(f"뉴스 수집 중 오류: {e}")
        
    return new_articles

@st.fragment(run_every=30 if auto_refresh else None)
def render_news_section():
    new_fetched = fetch_google_news(keyword)
    if new_fetched:
        st.session_state.articles_list = new_fetched + st.session_state.articles_list

    st.subheader(f"'{keyword}' 관련 최신 뉴스 (총 {len(st.session_state.articles_list)}개 수집됨)")

    if not st.session_state.articles_list:
        st.warning("수집된 뉴스가 없습니다. '목록 초기화 및 재수집' 버튼을 눌러주세요.")
    else:
        for idx, item in enumerate(st.session_state.articles_list[:20], 1):
            col1, col2 = st.columns([5, 1.5])
            with col1:
                st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
            with col2:
                st.caption(f"기사 작성일: {item['pub_date']}")

render_news_section()