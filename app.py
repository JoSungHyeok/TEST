import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import time

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

# 파이썬 내장 XML 파서를 활용한 뉴스 수집 함수 (추가 라이브러리 설치 불필요)
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
            # 파이썬 내장 xml 파서로 데이터 해석
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                
                # 구글 뉴스 제목의 '- 언론사명' 부분 깔끔하게 제거
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
                        "time": time.strftime("%H:%M:%S")
                    })
        else:
            st.error(f"응답 오류 (상태 코드: {response.status_code})")
    except Exception as e:
        st.error(f"뉴스 수집 중 오류 발생: {e}")
        
    return new_articles

# 뉴스 데이터 가져오기 실행
new_fetched = fetch_google_news(keyword)
if new_fetched:
    # 가장 최근 기사가 위로 오도록 추가
    st.session_state.articles_list = new_fetched + st.session_state.articles_list

# 메인 화면 출력
st.subheader(f"'{keyword}' 관련 최신 뉴스 (총 {len(st.session_state.articles_list)}개 수집됨)")

if not st.session_state.articles_list:
    st.warning("수집된 뉴스가 없습니다. 키워드를 확인하시거나 '목록 초기화 및 재수집' 버튼을 눌러주세요.")
else:
    for idx, item in enumerate(st.session_state.articles_list[:20], 1):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"**{idx}. [{item['title']}]({item['link']})**")
        with col2:
            st.caption(f"수집시간: {item['time']}")

# 자동 새로고침 옵션
if auto_refresh:
    time.sleep(30)
    st.rerun()