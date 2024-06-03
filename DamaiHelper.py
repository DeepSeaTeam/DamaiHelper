# coding: utf-8
from json import loads
from os.path import exists
from pickle import dump, load
from time import sleep, time
import os
import subprocess
import sys
import winreg
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def is_chrome_installed():
    """检查 Chrome 浏览器是否已安装"""
    # 检查默认安装路径
    default_install_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    if any(os.path.exists(path) for path in default_install_paths):
        return True
    
    # 检查注册表
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
            chrome_path = winreg.QueryValueEx(key, "client")  # 读取 Chrome 路径
            return True
    except FileNotFoundError:
        return False

def install_chrome(installer_path):
    """运行 Chrome 安装程序"""
    try:
        print("正在安装 Chrome 浏览器...")
        subprocess.run([installer_path], check=True)
        print("Chrome 浏览器安装完成。")
    except subprocess.CalledProcessError as e:
        print(f"安装失败: {e}")
        sys.exit(1)



class Concert(object):
    def __init__(self, date, session, price, real_name, nick_name, ticket_num, viewer_person, damai_url, target_url,
                 driver_path):
        self.date = date  # 日期序号
        self.session = session  # 场次序号优先级
        self.price = price  # 票价序号优先级
        self.real_name = real_name  # 实名者序号
        self.status = 0  # 状态标记
        self.time_start = 0  # 开始时间
        self.time_end = 0  # 结束时间
        self.num = 0  # 尝试次数
        self.ticket_num = ticket_num  # 购买票数
        self.viewer_person = viewer_person  # 观影人序号优先级
        self.nick_name = nick_name  # 用户昵称
        self.damai_url = damai_url  # 大麦网官网网址
        self.target_url = target_url  # 目标购票网址
        self.driver_path = driver_path  # 浏览器驱动地址
        self.driver = None

    def isClassPresent(self, item, name, ret=False):
        try:
            result = item.find_element(by=By.CLASS_NAME, value=name)
            if ret:
                return result
            else:
                return True
        except:
            return False

    # 获取账号的cookie信息
    def get_cookie(self):
        self.driver.get(self.damai_url)
        print("###请点击登录###")
        self.driver.find_element(by=By.CLASS_NAME, value='login-user').click()
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:  # 等待网页加载完成
            sleep(1)
        print("###请扫码登录###")
        while self.driver.title == '大麦登录':  # 等待扫码完成
            sleep(1)
        dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))
        print("###Cookie保存成功###")

    def set_cookie(self):
        try:
            cookies = load(open("cookies.pkl", "rb"))  # 载入cookie
            for cookie in cookies:
                cookie_dict = {
                    'domain': '.damai.cn',  # 必须有，不然就是假登录
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    "expires": "",
                    'path': '/',
                    'httpOnly': False,
                    'HostOnly': False,
                    'Secure': False}
                self.driver.add_cookie(cookie_dict)
            print("###载入Cookie###")
        except Exception as e:
            print(e)

    def login(self):
        print("###开始登录###")
        self.driver.get(self.target_url)
        WebDriverWait(self.driver, 10, 0.1).until(EC.title_contains('商品详情'))
        self.set_cookie()

    def enter_concert(self):
        self.time_start = time()  # 记录开始时间
        print("###打开浏览器，进入大麦网###")
        if not exists('cookies.pkl'):  # 如果不存在cookie.pkl,就获取一下
            service = Service(self.driver_path)
            self.driver = webdriver.Chrome(service=service)
            self.get_cookie()
            print("###成功获取Cookie，重启浏览器###")
            self.driver.quit()

        options = webdriver.ChromeOptions()
        # 禁止图片、js、css加载
        prefs = {"profile.managed_default_content_settings.images": 2,
                 "profile.managed_default_content_settings.javascript": 1,
                 'permissions.default.stylesheet': 2}
        mobile_emulation = {"deviceName": "Nexus 6"}
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        # 就是这一行告诉chrome去掉了webdriver痕迹，令navigator.webdriver=false，极其关键
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--log-level=3')

        # 更换等待策略为不等待浏览器加载完全就进行下一步操作
        capa = DesiredCapabilities.CHROME
        # normal, eager, none
        capa["pageLoadStrategy"] = "eager"
        service = Service(self.driver_path)
        self.driver = webdriver.Chrome(service=service, options=options, desired_capabilities=capa)
        # 登录到具体抢购页面
        self.login()
        self.driver.refresh()

    def click_util(self, btn, locator):
        while True:
            btn.click()
            try:
                return WebDriverWait(self.driver, 1, 0.1).until(EC.presence_of_element_located(locator))
            except:
                continue

    # 实现购买函数

    def choose_ticket(self):
        print("###进入抢票界面###")
        # 如果跳转到了确认界面就算这步成功了，否则继续执行此步
        while self.driver.title.find('订单确认') == -1:
            self.num += 1  # 尝试次数加1

            if self.driver.current_url.find("buy.damai.cn") != -1:
                break

            # 判断页面加载情况 确保页面加载完成
            try:
                WebDriverWait(self.driver, 10, 0.1).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
            except:
                raise Exception(u"***Error: 页面加载超时***")

            # 判断root元素是否存在
            try:
                box = WebDriverWait(self.driver, 1, 0.1).until(
                    EC.presence_of_element_located((By.ID, 'root'))
                )
            except:
                raise Exception(u"***Error: 页面中ID为root的整体布局元素不存在或加载超时***")

            # 检查并处理温馨提示遮罩
            try:
                health_info = WebDriverWait(self.driver, 1, 0.1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'health-info-content'))
                )
                print("---检测到温馨提示遮罩---")
                health_info_box = health_info.find_element(by=By.ID, value='health-info-html-box')
                # 模拟向上滑动，阅读温馨提示内容
                print("---正在模拟向上滑动阅读温馨提示内容---")
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", health_info_box)
                sleep(0.5)  # 等待滑动完成
                print("---模拟滑动完成---")
                # 点击“知道了”按钮
                print("---正在点击“知道了”按钮---")
                know_button = health_info.find_element(by=By.CLASS_NAME, value='button')
                know_button.click()
                print("---“知道了”按钮点击成功---")
            except TimeoutException:
                print("---不存在温馨提示遮罩---")
            except NoSuchElementException as e:
                print(f"***Error: 温馨提示遮罩操作异常：{e}***")

            # 检查并处理实名制观演提示遮罩
            try:
                realname_info = WebDriverWait(self.driver, 1, 0.1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'realname-content'))
                )
                print("---检测到实名制观演提示遮罩---")
                # 点击“知道了”按钮
                print("---正在点击“知道了”按钮---")
                known_button = realname_info.find_element(by=By.CLASS_NAME, value='known')
                known_button.click()
                print("---“知道了”按钮点击成功---")
            except TimeoutException:
                print("---不存在实名制观演提示遮罩---")
            except NoSuchElementException as e:
                print(f"***Error: 实名制观演提示遮罩操作异常：{e}***")

            try:
                buybutton = box.find_element(by=By.CLASS_NAME, value='buy__button')
                buybutton_text = buybutton.text
                print("---定位购买按钮成功---")
            except Exception as e:
                raise Exception(f"***Error: 定位购买按钮失败***: {e}")

            if "即将开抢" in buybutton_text:
                self.status = 2
                raise Exception("---尚未开售，刷新等待---")

            if "缺货" in buybutton_text:
                raise Exception("---已经缺货，刷新等待---")

            sleep(0.1)
            buybutton.click()
            print("---点击购买按钮---")
            box = WebDriverWait(self.driver, 1, 0.1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.sku-pop-wrapper')))

            try:
                # 日期选择
                toBeClicks = []
                try:
                    date = WebDriverWait(self.driver, 1, 0.1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'bui-dm-sku-calendar')))
                except Exception as e:
                    date = None
                if date is not None:
                    date_list = date.find_elements(
                        by=By.CLASS_NAME, value='bui-calendar-day-box')
                    for i in self.date:
                        j = date_list[i - 1]
                        toBeClicks.append(j)
                        break
                    for i in toBeClicks:
                        i.click()
                        sleep(0.05)

                # 选定场次
                session = WebDriverWait(self.driver, 1, 0.1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'sku-times-card')))  # 日期、场次和票档进行定位
                session_list = session.find_elements(
                    by=By.CLASS_NAME, value='bui-dm-sku-card-item')

                toBeClicks = []
                for i in self.session:  # 根据优先级选择一个可行场次
                    if i > len(session_list):
                        i = len(session_list)
                    j = session_list[i - 1]

                    k = self.isClassPresent(j, 'item-tag', True)
                    if k:  # 如果找到了带presell的类
                        if k.text == '无票':
                            continue
                        elif k.text == '预售':
                            toBeClicks.append(j)
                            break
                        elif k.text == '惠':
                            toBeClicks.append(j)
                            break
                    else:
                        toBeClicks.append(j)
                        break

                # 多场次的场要先选择场次才会出现票档
                for i in toBeClicks:
                    i.click()
                    sleep(0.05)

                # 选定票档
                toBeClicks = []
                price = WebDriverWait(self.driver, 1, 0.1).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'sku-tickets-card')))  # 日期、场次和票档进行定位

                price_list = price.find_elements(
                    by=By.CLASS_NAME, value='bui-dm-sku-card-item')  # 选定票档
                for i in self.price:
                    if i > len(price_list):
                        i = len(price_list)
                    j = price_list[i - 1]

                    k = self.isClassPresent(j, 'item-tag', True)
                    if k:  # 存在notticket代表存在缺货登记，跳过
                        continue
                    else:
                        toBeClicks.append(j)
                        break

                for i in toBeClicks:
                    i.click()
                    sleep(0.1)

                buybutton = box.find_element(
                    by=By.CLASS_NAME, value='sku-footer-buy-button')
                # sleep(1.0)
                buybutton_text = buybutton.text
                if buybutton_text == "":
                    raise Exception(u"***Error: 提交票档按钮文字获取为空,适当调整 sleep 时间***")

                try:
                    WebDriverWait(self.driver, 1, 0.1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'bui-dm-sku-counter')))
                except:
                    raise Exception(u"***购票按钮未开始***")

            except Exception as e:
                raise Exception(f"***Error: 选择日期or场次or票档不成功***: {e}")

            try:
                ticket_num_up = box.find_element(
                    by=By.CLASS_NAME, value='plus-enable')
            except:
                if buybutton_text == "选座购买":  # 选座购买没有增减票数键
                    buybutton.click()
                    self.status = 5
                    print("###请自行选择位置和票价###")
                    break
                elif buybutton_text == "提交缺货登记":
                    raise Exception(u'###票已被抢完，持续捡漏中...或请关闭程序并手动提交缺货登记###')
                else:
                    raise Exception(u"***Error: ticket_num_up 位置找不到***")

            if buybutton_text == "立即预订" or buybutton_text == "立即购买" or buybutton_text == '确定':
                for i in range(self.ticket_num - 1):  # 设置增加票数
                    ticket_num_up.click()
                buybutton.click()
                self.status = 4
                WebDriverWait(self.driver, 2, 0.1).until(
                    EC.title_contains("确认"))
                break
            else:
                raise Exception(f"未定义按钮：{buybutton_text}")

    def check_order(self):
        if self.status in [3, 4, 5]:
            # 选择观影人
            toBeClicks = []
            WebDriverWait(self.driver, 5, 0.1).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="dmViewerBlock_DmViewerBlock"]/div[2]/div/div')))
            people = self.driver.find_elements(
                By.XPATH, '//*[@id="dmViewerBlock_DmViewerBlock"]/div[2]/div/div')
            sleep(0.2)

            for i in self.viewer_person:
                if i > len(people):
                    break
                j = people[i - 1]
                j.click()
                sleep(0.05)

            WebDriverWait(self.driver, 5, 0.1).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="dmOrderSubmitBlock_DmOrderSubmitBlock"]/div[2]/div/div[2]/div[2]/div[2]')))
            comfirmBtn = self.driver.find_element(
                By.XPATH, '//*[@id="dmOrderSubmitBlock_DmOrderSubmitBlock"]/div[2]/div/div[2]/div[2]/div[2]')
            sleep(0.5)
            comfirmBtn.click()
            # 判断title是不是支付宝
            print("###正在跳转到支付宝付款界面###")

            while True:
                try:
                    WebDriverWait(self.driver, 5, 0.1).until(
                        EC.title_contains('支付宝'))
                    print("###订单提交成功###")
                    self.status = 6
                    self.time_end = time()
                    break
                except:
                    # 通过人工判断订单提交状态
                    step = input(
                        "\n###\n1.成功跳转到支付宝付款页面\n2.未知，没跳转到支付宝界面，尝试重新抢票\n3.未知，退出脚本\n###\n请输入当前状态：")
                    if step == '1':
                        # 成功
                        print("订单提交成功")
                        self.status = 6
                        self.time_end = time()
                        break
                    elif step == '2':
                        # 失败，进入下一轮抢票
                        print("尝试重新抢票")
                        return True
                    elif step == '3':
                        # 退出脚本
                        print("脚本退出成功")
                        return False
                    else:
                        raise Exception(u'***Error: 未知输入***')


if __name__ == '__main__':
    # 检查 Chrome 是否已安装
    if not is_chrome_installed():
            print("Chrome 浏览器未安装，将尝试自动安装。")
            installer_path = os.path.join(os.path.dirname(__file__), "ChromeSetup.exe")
            if os.path.exists(installer_path):
                install_chrome(installer_path)
            else:
                print("Chrome 安装程序未找到，请手动安装 Chrome 浏览器。")
                sys.exit(1)

    # 设置 WebDriver 路径和目标 URL
    driver_path = "./chromedriver.exe"  # 替换为实际的 ChromeDriver 路径
    target_url = input("请输入手机APP端目标购票网址: ").strip()

    # 验证 URL 是否合法
    if not target_url.startswith("https://m.damai.cn"):
        print("输入的 URL 不合法，程序将退出。")
        exit(1)

    # 创建 WebDriver Service
    service = Service(executable_path=driver_path)

    # 其他配置信息，这里使用硬编码作为示例
    date = [1]  # 示例日期序号
    session = [1, 2]  # 示例场次序号优先级
    price = [1, 2]  # 示例票价序号优先级
    real_name = [1]  # 示例实名者序号
    nick_name = ""  # 用户昵称
    ticket_num = 1  # 购买票数
    viewer_person = [1]  # 观影人序号优先级
    damai_url = "https://www.damai.cn"  # 大麦网官网网址

    # 初始化 Concert 实例
    con = Concert(date, session, price, real_name, nick_name, ticket_num, viewer_person, damai_url, target_url, driver_path)
    con.enter_concert()  # 确保这个方法初始化了 WebDriver
    max_attempts = 5  # 设置最大尝试次数
    attempts = 0

    # 循环执行抢票流程，直到成功或手动停止
    while attempts < max_attempts:
        try:
            # 尝试抢票
            con.choose_ticket()

            # 检查订单状态
            retry = con.check_order()
            if not retry:
                print("抢票成功，无需重试。")
                break  # 抢票成功，退出循环

            attempts += 1
            print(f"重试次数 {attempts}/{max_attempts}，正在等待重试...")

            sleep(10)  # 等待10秒，可以根据需要调整等待时间

        except Exception as e:
            print(f"发生异常：{e}")
            con.driver.get(con.target_url)  # 刷新到目标 URL
            continue  # 继续下一次循环
            
        
    # 抢票成功后的操作...
    if con.status == 6:
        print("### 经过%d轮奋斗，耗时%.1f秒，成功为您抢票！请及时确认订单信息并完成支付！###" % (
            con.num, round(con.time_end - con.time_start, 3)))
        input("按 Enter 键退出脚本")
