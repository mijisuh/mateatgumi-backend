# 코드의 전체적인 흐름
"""
1. 초기 설정
    - 기존 json 파일(indong_restaurants_progress.json)체크 및 데이터 로드
    - Chrome 드라이버 시작

2. 메인 크롤링 루프
    - 네이버 지도 검색 페이지 접속
    - current_page 변수로 페이지 추적(1~5 페이지)
    - searchIframe으로 전환
        - iframe 이란 웹페이지 안에 들어있는 또 다른 웹페이지
        - 동적으로 생성되는 컨텐츠를 담는 독립적인 문서
        - 동적인 컨텐츠에 접근하기 위해서는 해당 iframe으로 전환이 필요해서 Selenium이 적합함.

        - ex) 메인 페이지(최상위) 
        - searchIframe(음식점 목록)
        - entryIframe(음식점 상세정보)

3. 첫 페이지만 스크롤
    - 76개의 음식점이 로드될 때까지 스크롤

4. 음식점 정보 처리
    - 각 음식점 정보 수집
    - 상세 정보는 entryIframe에서 수집
    - 수집된 정보는 즉시 json 파일에 저장

5. 다음 페이지 이동
    - 다음 페이지 버튼 찾아 클릭
    - current_page 증가
    - 1~4 과정 반복

이 과정을 100개의 음식점을 수집하거나 5페이지까지 완료할 때까지 반복함.
        
"""


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import os
import random

def save_progress(data, filename='indong_restaurants_progress.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n중간 저장 완료: {filename} (총 {len(data)}개 저장됨)")

def take_break(saved_count):
    if saved_count > 0 and saved_count % 30 == 0:
        pause_time = random.uniform(20, 30)
        print(f"\n{saved_count}개 수집 완료. {pause_time:.1f}초 휴식 시작...")
        time.sleep(pause_time)
        print("휴식 완료. 다시 시작합니다.")

def get_reviews(driver, wait, review_type="recommend", count=10):
    reviews = {}
    try:
        collected_reviews = 0
        
        if review_type == "recent":
            try:
                print("최신순으로 전환 시도")
                sort_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Tx_h4")))
                buttons = sort_container.find_elements(By.CSS_SELECTOR, "a.zMIkw")
                if len(buttons) >= 2:
                    recent_button = buttons[1]
                    driver.execute_script("arguments[0].click();", recent_button)
                    time.sleep(3)
                    print("최신순 전환 완료")
                else:
                    print("최신순 버튼을 찾을 수 없음")
            except Exception as e:
                print(f"최신순 전환 실패: {str(e)}")
                return {f'review{i}': "리뷰 정보 없음" for i in range(1, count + 1)}
        
        while collected_reviews < count:
            try:
                review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pui__vn15t2")))
                for review in review_elements[collected_reviews:]:
                    if collected_reviews >= count:
                        break
                    review_text = review.text.strip()
                    if review_text:
                        collected_reviews += 1
                        reviews[f'review{collected_reviews}'] = review_text
                        print(f"{review_type} 리뷰 {collected_reviews}개 수집")
                
                if collected_reviews >= count:
                    break
                    
                try:
                    more_button = driver.find_element(By.CSS_SELECTOR, "span.TeItc")
                    driver.execute_script("arguments[0].click();", more_button)
                    print(f"더보기 버튼 클릭 (현재 {collected_reviews}개 수집)")
                    time.sleep(2)
                except:
                    print("더 이상 더보기 버튼이 없음")
                    break
                    
            except Exception as e:
                print(f"리뷰 수집 중 오류: {str(e)}")
                break
        
        for i in range(len(reviews) + 1, count + 1):
            reviews[f'review{i}'] = "리뷰 정보 없음"
            
    except Exception as e:
        print(f"전체 리뷰 수집 중 오류: {str(e)}")
        reviews = {f'review{i}': "리뷰 정보 없음" for i in range(1, count + 1)}
    
    return reviews

def crawl_naver_map():
    # 기존 데이터 로드
    if os.path.exists('indong_restaurants_progress.json'):
        with open('indong_restaurants_progress.json', 'r', encoding='utf-8') as f:
            restaurant_data = json.load(f)
            print(f"기존 데이터 로드 완료: {len(restaurant_data)}개")
    else:
        restaurant_data = {}
    
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)
    
    try:
        driver.get("https://map.naver.com/p/search/인동동%20맛집")
        time.sleep(3)
        print("페이지 로딩 완료")
        
        current_page = 1
        while len(restaurant_data) < 100 and current_page <= 5:  # 최대 5페이지까지
            print(f"\n===== {current_page}페이지 처리 시작 =====")
            
            # searchIframe으로 전환
            driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))
            time.sleep(3)
            
            # 첫 페이지에서만 스크롤
            if current_page == 1:
                print("스크롤 시작")
                previous_count = 0
                scroll_attempts = 0
                
                while True:
                    restaurants = driver.find_elements(By.CSS_SELECTOR, "li.UEzoS")
                    current_count = len(restaurants)
                    print(f"현재 {current_count}개의 음식점 로드됨 (새로 추가: {current_count - previous_count}개)")
                    
                    if current_count >= 76:
                        print("최대 개수(76개)에 도달")
                        break
                    
                    # 마지막 항목으로 스크롤
                    last_restaurant = restaurants[-1]
                    driver.execute_script("arguments[0].scrollIntoView(true);", last_restaurant)
                    time.sleep(2)
                    
                    if current_count == previous_count:
                        scroll_attempts += 1
                        if scroll_attempts >= 10:
                            print("최대 스크롤 시도 횟수 도달")
                            break
                    else:
                        scroll_attempts = 0
                    
                    previous_count = current_count
            
            # 현재 페이지의 음식점 처리
            restaurants = driver.find_elements(By.CSS_SELECTOR, "li.UEzoS")
            for restaurant in restaurants:
                if len(restaurant_data) >= 100:
                    break
                
                try:
                    name_element = restaurant.find_element(By.CSS_SELECTOR, "span.TYaxT")
                    name = name_element.text.strip()
                    
                    if name in restaurant_data:
                        print(f"이미 수집된 음식점 건너뛰기: {name}")
                        continue
                    
                    print(f"\n처리 중인 음식점({len(restaurant_data) + 1}/100): {name}")
                    take_break(len(restaurant_data))
                    
                    name_element.click()
                    time.sleep(3)
                    
                    # 상세정보 iframe으로 전환
                    driver.switch_to.default_content()
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))
                    time.sleep(2)
                    
                    # 기본 정보 수집
                    try:
                        category = driver.find_element(By.CSS_SELECTOR, "span.lnJFt").text
                    except:
                        category = "정보 없음"
                    
                    try:
                        tel = driver.find_element(By.CSS_SELECTOR, "span.xlx7Q").text
                    except:
                        tel = "정보 없음"
                    
                    try:
                        feature = driver.find_element(By.CSS_SELECTOR, "div.O8qbU.Uv6Eo div.vV_z_ div.xPvPE").text
                    except:
                        feature = "정보 없음"
                    
                    try:
                        location = driver.find_element(By.CSS_SELECTOR, "span.LDgIH").text
                    except:
                        location = "정보 없음"
                    
                    # 리뷰 수집
                    review_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='review']")))
                    driver.execute_script("arguments[0].click();", review_tab)
                    time.sleep(2)
                    
                    recommend_reviews = get_reviews(driver, wait, "recommend", 10)
                    recent_reviews = get_reviews(driver, wait, "recent", 40)
                    
                    # 데이터 저장
                    restaurant_data[name] = {
                        "reviews": {
                            "recommend": recommend_reviews,
                            "recent": recent_reviews
                        },
                        "category": category,
                        "tel": tel,
                        "feature": feature,
                        "location": location
                    }
                    
                    save_progress(restaurant_data)
                    print(f"저장 완료: {name} (현재 {len(restaurant_data)}개)")
                    
                    # 목록으로 돌아가기
                    driver.switch_to.default_content()
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"음식점 처리 중 오류 발생: {str(e)}")
                    driver.switch_to.default_content()
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))
                    continue
            
            # 다음 페이지로 이동
            if len(restaurant_data) < 100 and current_page < 5:
                try:
                    pagination_buttons = driver.find_elements(By.CSS_SELECTOR, "a.mBN2s")
                    next_page_button = None
                    
                    for button in pagination_buttons:
                        if button.text.strip() == str(current_page + 1):
                            next_page_button = button
                            break
                    
                    if next_page_button:
                        print(f"\n{current_page + 1}페이지로 이동")
                        driver.execute_script("arguments[0].click();", next_page_button)
                        print("페이지 로딩 대기 (5초)")
                        time.sleep(5)
                        current_page += 1
                    else:
                        print("\n마지막 페이지 도달")
                        break
                
                except Exception as e:
                    print(f"페이지 전환 중 오류: {str(e)}")
                    break
        
        print(f"\n크롤링 완료! 총 {len(restaurant_data)}개의 음식점 정보 저장됨")
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        save_progress(restaurant_data)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_naver_map()