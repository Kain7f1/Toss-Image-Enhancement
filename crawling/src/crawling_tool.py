import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
import datetime
import utility_module as util

header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }


#####################################
# 본문에서 new_row를 얻어오는 함수
def get_new_row_from_main_content(url_row):
    is_comment = 0  # 본문이므로 0
    try:
        with requests.Session() as session:
            response = session.get(url_row['url'], headers=header)
        soup = BeautifulSoup(response.text, "html.parser")
        content = util.preprocess_content_dc(soup.find('div', {"class": "write_div"}).text)
        content = url_row['title'] + " " + content
        new_row = [url_row['date'], url_row['title'], url_row['url'], url_row['media'], content, is_comment]
    except Exception as e:
        print("[오류가 발생하여 반복합니다] ", e)
        new_row = get_new_row_from_main_content(url_row)
    return new_row


#####################################
# 기능 : url을 받아 reply_list를 리턴합니다
# 리턴값 : reply_list
def get_reply_list(url):
    try:
        driver = get_driver()
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        reply_list = soup.find_all("li", {"class": "ub-content"})
        driver.quit()
    except Exception as e:
        print("[오류가 발생하여 반복합니다] ", e)
        reply_list = get_reply_list(url)
    return reply_list


#####################################
# 기능 : 댓글 html코드를 받아서, 댓글의 date를 리턴합니다
# 리턴값 : 2023-10-06 형식의 문자열
def get_reply_date(reply):
    temp_date = reply.find("span", {"class": "date_time"}).text.replace(".", "-")  # 댓글 등록 날짜 추출
    if temp_date[:2] == "20":  # 작년 이전은 "2022.09.07 10:10:54" 형식임
        date = temp_date[:10]
    else:  # 올해는 "09.30 10:10:54" 형식임
        date = str(datetime.datetime.now().year) + "-" + temp_date[:5]  # 올해 년도를 추가함
    return date


#####################################
# 기능 : 무시해야하는 댓글이면, True를 반환하고, 필요한 댓글이면 False를 반환합니다
def is_ignore_reply(reply):
    if reply.select_one("p.del_reply"):
        print("[삭제된 코멘트입니다]")
        return True
    elif reply.find('span', {'data-nick': '댓글돌이'}):
        print("[댓글돌이는 무시합니다]")
        return True
    elif reply.find('div', {'class': 'comment_dccon'}):
        print("[디시콘은 무시합니다]")
        return True
    else:
        return False


#############################
# get_driver()
# 기능 : driver를 반환합니다
# 리턴값 : driver
# 사용법 : driver = get_driver() 쓰고 driver.get(url) 처럼 사용합니다
def get_driver():
    CHROME_DRIVER_PATH = "C:/Users/chromedriver.exe"    # (절대경로) Users 폴더에 chromedriver.exe를 설치했음
    # driver 설정
    options = webdriver.ChromeOptions()                 # (옵션)
    # options.add_argument("--start-maximized")         # 창이 최대화 되도록 열리게 한다.
    options.add_argument("headless")                  # 창이 없이 크롬이 실행이 되도록 만든다
    options.add_argument("disable-infobars")            # 안내바가 없이 열리게 한다.
    options.add_argument("disable-gpu")                 # 크롤링 실행시 GPU를 사용하지 않게 한다.
    options.add_argument("--disable-dev-shm-usage")     # 공유메모리를 사용하지 않는다
    options.add_argument("--disable-extensions")        # 확장팩을 사용하지 않는다.
    driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=options)
    return driver


##############################
# get_gall_id()
# 기능 : gall_url을 받아 gall_id를 리턴한다
def get_gall_id(gall_url):
    return re.search(r'id=([\w_]+)', gall_url).group(1)


##############################
# get_gall_type()
# 기능 : 메이저갤러리인지 마이너갤러리인지 미니갤러리인지 판단한다
# 리턴값 : 메이저갤러리('major'), 마이너갤러리('minor'), 미니갤러리('mini')
def get_url_base(gall_url):
    if "mgallery" in gall_url:
        url_base = "https://gall.dcinside.com/mgallery"
    elif "mini" in gall_url:
        url_base = "https://gall.dcinside.com/mini"
    else:
        url_base = "https://gall.dcinside.com"
    return url_base


###############################
# get_max_num()
# 기능 : 검색결과 중 가장 큰 글번호를 구하여 리턴한다
# 리턴값 : max_num
def get_max_num(keyword, gall_id, url_base):
    search_url = f"{url_base}/board/lists/?id={gall_id}&s_type=search_subject_memo&s_keyword={keyword}"
    with requests.Session() as session:
        response = session.get(search_url, headers=header)
    soup = BeautifulSoup(response.text, "html.parser")  # 페이지의 soup
    box = soup.select("div.gall_listwrap tr.ub-content")        # 글만 있는 box
    first_content = ''
    # 검색 범위를 정하는 작업
    for content in box:
        # 광고는 제거한다 : 광고글은 글쓴이가 "운영자"이다
        if content.find('td', class_='gall_writer').get_text() == "운영자":
            continue
        # 광고를 제외한 가장 첫번째 글
        first_content = content.select_one("td.gall_num").get_text()
        break
    max_num = int(int(first_content)/10000+1)*10000      # max_num  의 글번호까지 검색한다
    return max_num


################################
# get_last_page()
# 기능 : [dcinside] 갤러리 내에서 검색결과의 마지막 페이지가 몇인지 리턴 (검색한 직후의 url이어야 함)
# 리턴값 : max_page(int)
def get_last_page(url):
    try:
        with requests.Session() as session:
            response = session.get(url, headers=header)
        soup = BeautifulSoup(response.text, "html.parser").find("div", class_="bottom_paging_wrap re")
        filtered_a_tags = [a for a in soup.find_all('a') if not a.find('span', class_='sp_pagingicon')]
        num_button_count = len(filtered_a_tags) + 1    # 숫자 버튼의 개수

        if num_button_count >= 16:    # 한번에 15 page씩 나와서, page가 16개 이상이면 >> 버튼이 생기면서 a태그가 17개가 된다 / 이때의 페이징 처리
            last_page_url = soup.find_all("a")[-2]['href']                          # 맨 마지막 페이지로 가는 버튼의 url
            last_page = re.search(r'page=(\d+)', last_page_url).group(1)     # 정규식으로 page 부분의 숫자만 추출
            last_page = int(last_page)                                              # 맨 마지막 페이지
        else:
            last_page = num_button_count
    except Exception as e:
        print("[오류가 발생하여 반복합니다] ", e)
        last_page = get_last_page(url)
    return last_page
