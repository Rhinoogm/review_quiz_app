# 파일명: keep_alive.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# 본인의 Streamlit 앱 URL로 반드시 변경하세요.
URL = "https://quizappbegood.streamlit.app/"

def ping_streamlit():
    # 가상 환경(헤드리스)에서 크롬을 실행하기 위한 필수 옵션들입니다.
    # 출처: Selenium 공식 문서 (Headless Chrome 설정)
    chrome_options = Options()
    chrome_options.add_argument('--headless') # 화면 없이 백그라운드에서 실행
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"접속 시도 중: {URL}")
        driver.get(URL)
        
        # Streamlit의 빈 HTML이 로드된 후, 내부 JavaScript가 실행되고 
        # WebSocket이 연결될 때까지 충분히 대기합니다. (10초)
        time.sleep(10) 
        print("정상적으로 페이지 렌더링 및 웹소켓 연결이 완료되었습니다.")
        
    except Exception as e:
        print(f"접속 중 오류 발생: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    ping_streamlit()