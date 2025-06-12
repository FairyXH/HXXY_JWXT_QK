import os
import re
import sys
import time
import random
import colorsys
import datetime
import requests
import threading
from colorama import Fore, Style, init
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.common import NoSuchElementException
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

init()


class ThreadColoredPrinter:
    def __init__(self, min_hue_distance=0.3):
        self.thread_local = threading.local()
        self.used_hues = set()
        self.min_hue_distance = min_hue_distance  # 最小色相差（0-1）
        self.lock = threading.Lock()

    def _generate_distinct_color(self):
        """生成与已用颜色有明显差异的随机颜色"""
        with self.lock:
            while True:
                # 在HSV空间中生成随机色调（Hue）
                hue = random.random()

                # 检查与已用颜色的最小差异
                if not self.used_hues or all(
                    min(abs(hue - used), 1 - abs(hue - used)) >= self.min_hue_distance
                    for used in self.used_hues
                ):
                    self.used_hues.add(hue)
                    break

            # 固定高饱和度和亮度确保颜色鲜艳
            saturation = 0.8 + random.random() * 0.2  # 0.8-1.0
            value = 0.7 + random.random() * 0.3  # 0.7-1.0

            # 转换为RGB
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            return f"\033[38;2;{int(r * 255)};{int(g * 255)};{int(b * 255)}m"

    def _get_color(self):
        if not hasattr(self.thread_local, "color"):
            self.thread_local.color = self._generate_distinct_color()
        return self.thread_local.color

    def print(self, *args, **kwargs):
        color = self._get_color()
        print(color, end="")
        print(*args, **kwargs)
        print(Style.RESET_ALL, end="", flush=True)


def log(text, level=0, writes=True):
    level_text = ""
    if level == 0:
        level_text = "INFO"
    elif level == 1:
        level_text = "ERROR"
    elif level == 2:
        level_text = "DEBUG"
    log_text = "[%s %s]%s\n" % (level_text, datetime.datetime.now(), text)
    printer.print(log_text)
    if writes:
        with open(f"{datadir}\\main_log.txt", "a") as f:
            f.write(log_text)


def start(dbg):
    global debug, exe_path, datadir, headless_flag, User_Agent, printer
    printer = ThreadColoredPrinter(min_hue_distance=0.2)
    debug = dbg  # 调试开关,为True时部分功能失效；发布版本时确保为False
    exe_path = os.path.dirname(sys.executable)
    datadir = "data"
    try:
        if not os.path.exists(datadir):
            datadir = f"{exe_path}\\data"
            os.mkdir(datadir)
    except:
        print("数据目录出错,请检查。")
        time.sleep(5)
        sys.exit()
    if not debug:
        os.chdir(exe_path)
    headless_flag = True  # 无头模式
    User_Agent = "Mozilla/5.0 (Linux; Android 15; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.86 Mobile Safari/537.36 wxwork/4.1.36 MicroMessenger/7.0.1 NetType/4G Language/zh Lang/zh ColorScheme/Dark wwmver/3.26.36.632"


def get_captcha_UserInfo_score(token):
    global captcha_score
    captcha_score = 2147483647  # 默认获取失败返回值
    try:
        dama_score_url = "http://api.jfbym.com/api/YmServer/getUserInfoApi"
        data = {
            "token": token,
            "type": "score",
        }
        res = requests.post(url=dama_score_url, data=data)
        if res.status_code == 200:
            if res.json().get("code") == 10001:
                captcha_score = res.json().get("data").get("score")
        return int(captcha_score)
    except Exception as e:
        return captcha_score


def captcha_customapi(
    b64img, token, username=""
):  # 以下对接验证码打码平台示例try:  # 打码平台识别
    try:
        log(
            f"{username} 云码平台剩余积分:%s" % get_captcha_UserInfo_score(token),
            writes=False,
        )
        dama_url = "http://api.jfbym.com/api/YmServer/customApi"
        data = {
            "image": b64img,
            "token": token,
            "type": "50100",
        }
        res = requests.post(url=dama_url, data=data)
        if res.status_code == 200:
            if res.json().get("code") == 10000:
                captcha_code = res.json().get("data").get("data")
                log(f"{username} 获取到验证码为:%s" % captcha_code, writes=False)
                return captcha_code
        return "Fail"
    except:
        log(f"{username} 调用打码平台失败...", writes=False)
        return "Fail"


def get_login_info(username, password, captcha_token):
    def is_element_present(browser, xpath):
        try:
            browser.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False

    def mkdir(path):
        if not os.path.isdir(path):
            if os.path.isfile(path):
                os.remove(path)
            os.mkdir(path)

    log(f"{username} 开始获取Cookies", writes=False)
    global headless_flag, captcha_score
    options = Options()
    if headless_flag:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    options.add_argument(f"--user-agent={User_Agent}")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")  # 允许不安全本地连接
    # browser_data = f"{datadir}\\browser_data"
    # browser_data_user = f"{browser_data}\\{username}"
    # mkdir(browser_data)
    # mkdir(browser_data_user)
    # log(f'{username} 使用浏览器数据:{os.path.abspath(browser_data_user)}')
    # options.add_argument(f"--user-data-dir={browser_data_user}")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    seleniumwire_options = {
        "verify_ssl": False,  # 不验证 SSL 证书
    }
    driver_path = "%s\\msedgedriver.exe" % exe_path
    service = Service(executable_path=driver_path)
    browser = webdriver.Edge(
        service=service,
        options=options,
        seleniumwire_options=seleniumwire_options,
    )
    browser.set_window_size(640, 720)
    browser.set_page_load_timeout(10)
    browser.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        },
    )
    try:
        log("%s 正在登录教务系统:" % username, writes=False)
        browser.get("https://jwxth5.hxxy.edu.cn/njwhd/loginSso")
        WebDriverWait(browser, 10).until(
            ec.presence_of_element_located((By.XPATH, '//*[@id="username"]'))
        )
        username_input = browser.find_element(By.XPATH, '//*[@id="username"]')
        username_input.clear()
        username_input.send_keys(username)
        password_input = browser.find_element(By.XPATH, '//*[@id="password"]')
        password_input.clear()
        password_input.send_keys(password)
        captcha_b64_base = browser.find_element(
            By.XPATH, '//*[@id="fm1"]/div[1]/div/section/div/div[2]/img'
        ).get_attribute("src")
        log(f"{username} 正在识别登录验证码", writes=False)
        captcha_code = captcha_customapi(
            captcha_b64_base, captcha_token, username=username
        )
        captcha_timeout = 0  # 超时
        while captcha_code == "Fail":
            log(f"{username} 识别失败,刷新验证码...", writes=False)
            captcha_timeout += 1
            browser.find_element(
                By.XPATH, '//*[@id="fm1"]/div[1]/div/section/div/div[2]/img'
            ).click()  # 点击刷新验证码
            time.sleep(0.5)
            captcha_b64_base = browser.find_element(
                By.XPATH, '//*[@id="fm1"]/div[1]/div/section/div/div[2]/img'
            ).get_attribute("src")
            captcha_code = captcha_customapi(
                captcha_b64_base, captcha_token, username=username
            )
            if captcha_timeout > 10:
                break
        captcha_input = browser.find_element(By.XPATH, '//*[@id="captcha"]')
        captcha_input.clear()
        captcha_input.send_keys(captcha_code)
        browser.find_element(By.XPATH, '//*[@id="fm1"]/input[3]').click()
        if is_element_present(browser, '//*[@id="fm1"]/div[1]/span'):
            log(f"{username} 验证码错误", writes=False)
            return "False"
        log(f"{username} 登录完成,正在授权教务系统访问", writes=False)
    except Exception as e:
        pass
    WebDriverWait(browser, 10).until(
        ec.presence_of_element_located(
            (
                By.XPATH,
                '//*[@id="app"]/div/div[1]/div/div[4]/div/div[2]/div/div/div[5]/div',
            )
        )
    )
    try:
        WebDriverWait(browser, 10).until(
            ec.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="app"]/div/div[1]/div/div[4]/div/div[2]/div/div/div[5]/div/span[2]',
                )
            )
        )
    except:
        pass
    while len(browser.get_cookies()) == 0:
        browser.refresh()
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        try:
            browser.find_element(
                By.XPATH,
                '//*[@id="app"]/div/div[1]/div/div[4]/div/div[2]/div/div/div[5]/div/span[2]',
            ).click()
        except:
            pass
        time.sleep(1)
    token = ""
    session_time = ""
    pattern = re.compile(r'https?://[^"]+\.\d+\.js')
    for i in browser.requests:
        req_url = i.url
        if "/jsxsd/qzapp/wxgetXklc" in req_url:
            headers = i.headers
            token = headers.get("token")
        if pattern.search(req_url):
            session_time = req_url.split(".")[-2]

    cookies = browser.get_cookies()
    cookie = [item["name"] + "=" + item["value"] for item in cookies]
    cookie_str = ";".join(item for item in cookie)
    resu = (cookie_str, token, session_time)  # 返回的内容
    log("%s 成功获取登录信息:%s" % (username, resu), writes=False)
    browser.close()
    return resu


def sel_ke(headers, sessionTime, rotationId, noticeId, courseId, username):
    log(f"{username} 执行选课:{rotationId}-->{noticeId}-->{courseId}", writes=False)
    Sel_url = "https://jwxth5.hxxy.edu.cn/jsxsd/qzapp/wxxkOper"
    Sel_data = {
        "classificationCode": "01",
        "rotationId": rotationId,
        "courseId": courseId,
        "noticeId": noticeId,
        "selectedNoticeId": "",
        "splitIdentification": "",
        "selectedSplitIdentification": "",
        "courseInformation": "",
        "classTeacher": "",
        "classWeek": "",
        "classSessions": "",
        "filteringConflicts": "",
        "restrictedSelection": "",
        "sessionTime": sessionTime,
        "fullCourse": "",
        "compulsorySemester": "false",
        "compulsorySelection": "false",
        "compulsoryGrades": "false",
        "selectionGrades": "false",
        "departmentCurriculum": "false",
        "generalCourseCategories": "",
        "courseQualification": "true",
        "data_enccryptStr": "",
    }
    Sel_result = requests.post(Sel_url, data=Sel_data, headers=headers)
    if Sel_result.status_code == 200:
        Sel_result = Sel_result.json()
        if Sel_result["errorCode"] == "fail":
            log(f"{username} 选课失败,原因:{Sel_result['errorMessage']}", writes=True)
        else:
            success_msg = f"{username} 选课成功,结果:{Sel_result}"
            log(success_msg, writes=True)
            os.popen(f'msg * "{success_msg}"')  # 仅Windows系统,弹窗提醒
    else:
        log(f"{username} 选课失败,网络错误。", writes=False)


def ke_info(headers, sessionTime, searchs, username):
    KList_url = "https://jwxth5.hxxy.edu.cn/jsxsd/qzapp/wxgetXklc"
    KList_data = {"isnew": 1}
    Klist_result = requests.post(KList_url, headers=headers, data=KList_data)
    if Klist_result.status_code == 200:
        if Klist_result.json()["errorCode"] == "success":
            Klist_data = Klist_result.json()["data"]
            if len(searchs) == 0:
                log(
                    f"{username} 未设置抢课,仅输出课程信息(选课列表):{Klist_result.text}",
                    writes=False,
                )
            for i in Klist_data:
                rotationid = i["rotationid"]
                rotationname = i["rotationname"]
                wxinitXscache_url = (
                    "https://jwxth5.hxxy.edu.cn/jsxsd/qzapp/wxinitXscache"
                )
                wxinitXscache_data = {"rotationId": rotationid}
                wxinitXscache_result = requests.post(
                    wxinitXscache_url, headers=headers, data=wxinitXscache_data
                )
                if wxinitXscache_result.status_code == 200:
                    wxinitXscache_result = wxinitXscache_result.json()
                    if not wxinitXscache_result["errorCode"] == "fail":
                        wxinitXscache_result_data = wxinitXscache_result["data"]
                        sessionTime = wxinitXscache_result_data["sessionTime"]
                        classification_list = wxinitXscache_result_data[
                            "classificationList"
                        ]
                        log(
                            f"{username} 监控选课:{rotationname},检索课程:{searchs}",
                            writes=False,
                        )
                        for j in classification_list:
                            log(
                                f"{username} 遍历 {rotationname}-->{j['classificationName']}",
                                writes=False,
                            )
                            CanSele_url = (
                                "https://jwxth5.hxxy.edu.cn/jsxsd/qzapp/wxgetKcList?"
                            )
                            CanSele_data = {
                                "classificationCode": j["classificationCode"],
                                "rotationId": rotationid,
                                "courseId": "",
                                "noticeId": "",
                                "splitIdentification": "",
                                "courseInformation": "",
                                "classTeacher": "",
                                "classWeek": "",
                                "classSessions": "",
                                "filteringConflicts": "",
                                "restrictedSelection": "",
                                "sessionTime": sessionTime,
                                "fullCourse": "",
                                "compulsorySemester": "false",
                                "compulsorySelection": "false",
                                "compulsoryGrades": "false",
                                "selectionGrades": "false",
                                "departmentCurriculum": "false",
                                "generalCourseCategories": "",
                                "courseQualification": "true",
                                "data_enccryptStr": "",
                            }
                            CanSele_result = requests.post(
                                CanSele_url, headers=headers, data=CanSele_data
                            )
                            if CanSele_result.status_code == 200:
                                if CanSele_result.json()["errorCode"] == "success":
                                    if not len(searchs) == 0:
                                        for i in CanSele_result.json()["data"]:
                                            courseName = i["courseName"]
                                            groupName = i["groupName"]
                                            courseNumber = i["courseNumber"]
                                            noticeId = i["noticeId"]
                                            courseId = i["courseId"]
                                            search_flag = True
                                            for search in searchs:
                                                if search in str(i):
                                                    search_flag = True
                                                    log(
                                                        f"{username} {rotationname}-->您搜索的课程信息(满足条件:{search}):{ [courseName,groupName,courseNumber,noticeId]}",
                                                        writes=False,
                                                    )
                                                    sel_ke(
                                                        headers,
                                                        sessionTime,
                                                        rotationid,
                                                        noticeId,
                                                        courseId,
                                                        username,
                                                    )
                                            else:
                                                if not search_flag:
                                                    log(
                                                        f"{username} 在类 {rotationname}-->未搜索到您需要的课程: {searchs}",
                                                        writes=False,
                                                    )
                                    else:
                                        log(
                                            f"{username} {rotationname}-->未设置抢课,仅输出课程信息(二级列表):{CanSele_result.text}",
                                            writes=False,
                                        )

                                else:
                                    err_msg = CanSele_result.json()["errorMessage"]
                                    log(
                                        f"{username} 可选课程列表获取失败:{err_msg}",
                                        writes=False,
                                    )
                                    if "重新登录" in err_msg:
                                        return False
                    else:
                        log(
                            f"{username} {rotationname}-->{wxinitXscache_result['errorMessage']}",
                            writes=False,
                        )
                else:
                    log(f"{username} 网络请求失败。", writes=False)
        else:
            log(f"{username} 没有可用选课", writes=False)
        return True


def ke_main(usn, pwd, cls, captcha_token):
    while True:
        try:
            get_logon = get_login_info(usn, pwd, captcha_token)
        except Exception as e:
            log(f"{usn} 登录失败,10秒后重试:\n{e}", writes=False)
            time.sleep(10)
            continue
        cookies = get_logon[0]
        token = get_logon[1]
        session_time = get_logon[2]
        headers = {"User-Agent": User_Agent, "token": token, "Cookie": cookies}
        while True:
            try:
                if not ke_info(headers, session_time, cls, usn):
                    log(f"{usn} 登录状态失效,将重新登录。", writes=False)
                    break
            except:
                break
            time.sleep(1)
        time.sleep(3)


def main():
    start(False)  # 初始化,传入True时为调试模式(不改变运行地址)
    cloud_captcha_token_txt = f"{datadir}\\cloud_captcha_token.txt"
    captcha_token = ""
    if os.path.isfile(cloud_captcha_token_txt):
        with open(cloud_captcha_token_txt, "r") as f:
            captcha_token = f.read()
    else:
        with open(cloud_captcha_token_txt, "w") as f:
            f.write("token")
        log(
            f"未找到云码Token。请在 {cloud_captcha_token_txt} 中填写云码平台Token。",
            writes=False,
        )
        time.sleep(10)
        sys.exit(0)
    user_database = f"{datadir}\\userinfo.txt"
    run_info = []
    if os.path.isfile(user_database):
        with open(user_database, "r") as f:
            for i in f.readlines():
                if not i[0] == "#":
                    run_info.append(i)
    else:
        with open(user_database, "w") as f:
            f.write(
                "#请在本文件内写入抢课的账户信息，一行一个。格式：账号,密码,课程1*课程2*课程3。课程可有多个，星号隔开。课程信息可以是课名模糊搜索,也可是课程编码等。"
            )
        log(f"未找到秒抢用户信息。请在 {user_database} 中填写。", writes=False)
        time.sleep(10)
    for i in run_info:
        if "\n" in i:
            i = i.replace("\n", "")
        i = i.split(",")
        if len(i) > 2 and not i[-1] == "":
            Thread = threading.Thread(
                target=ke_main,
                args=(i[0], i[1], tuple([j for j in i[2].split("*")]), captcha_token),
            )
        else:
            Thread = threading.Thread(
                target=ke_main, args=(i[0], i[1], (), captcha_token)
            )
        Thread.start()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
