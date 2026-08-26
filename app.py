import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from email.utils import parsedate_to_datetime

st.set_page_config(page_title="주식 뉴스 자동 스크랩", layout="wide")

st.title("📈 주식 뉴스 실시간 자동 수집기 (Google News 엔진)")

# 세션 상태 초기화
if "saved_links" not in st.session_state:
    st.session_state.saved_links = set()
if "articles_list" not in st.session_state:
    st.session_state.articles_list = []

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    keyword = st.text_input("수집할 키워드/종목명", "주식")
    auto_refresh = st.checkbox("자동 새로고침 (30초 마다)", value=False)
    
    if st.button("목록 초기화 및 재수집"):
        st.session_state.articles_list = []
        st.session_state.saved_links = set()
        st.rerun()

# RSS 날짜 문자열을 알기 쉬운 날짜/시간 포맷으로 변환하는 함수
def format_pub_date(pub_date_str):
    if not pub_date_str:
        return "-"
    try:
        dt = parsedate_to_datetime(pub_date_str)
        # 예: 08-26 15:30 형태로 변환
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return pub_date_str

# 구글 뉴스 RSS 수집 함수
def fetch_google_news(search_keyword):
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
            items = root.findall(".//item")
            
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate") # 기사 작성 날짜 태그
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                pub_date = pub_date_elem.text if pub_date_elem is not None else ""
                
                # 구글 뉴스 제목의 '- 언론사명' 제거
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                
                if not title or not link:
                    continue
                
                # 중복 체크
                if link not in st.session_state.saved_links:
                    st.session_state.saved_links.add(link)
                    new_articles.append({
                        "title": title, 
                        "link": link, 
                        "pub_date": format_pub_date(pub_date) # 변환된 기사 발행일자
                    })
        else:
            st.error(f"응답 오류 (상태 코드: {response.status_code})")
    except Exception as e:
        st.error(f"뉴스 수집 중 오류 발생: {e}")
        
    return new_articles

# 뉴스 데이터 가져오기 실행
new_fetched = fetch_google_news(keyword)
if new_fetched:
    st.session_state.articles_list = new_fetched + st.session_state.articles_list

# 메인 화면 출력
st.subheader(f"'{keyword}' 관련 최신 뉴스 (총 {len(st.session_state.articles_list)}개 수집됨)")

if not st.session_state.articles_list:
    st.warning("수집된 뉴스가 없습니다. 키워드를 확인하시거나 '목록 초기화 및 재수집' 버튼을 눌러주세요.")
else:
    for idx, item in enumerate(st.session_state.articles_list[:20], 1):
        col1, col2 = st.columns([5, 1.5])
        with col1:
            st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
        with col2:
            st.caption(f"기사 작성일: {item['pub_date']}")

# 자동 새로고침 옵션
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()