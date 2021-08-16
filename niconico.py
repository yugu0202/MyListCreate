from selenium import webdriver
from bs4 import BeautifulSoup
import lxml
import statistics
import sqlite3
import time
import re
import sys
import pathlib
import getpass
import random
import string

IntegrationBuffer()
#初期設定
mode = input("mode>")
if mode == "remove":
    RemoveMain()

tagName = input("tagName>")
if mode == "rmtable":
    return

USER = input("LoginID>")
PASS = getpass.getpass("LoginPassword>")
if mode == "add":
    AddMain()

options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
browser = webdriver.Chrome(cwd+"/lib/chromedriver.exe",chrome_options=options)
browser.implicitly_wait(1)

rootURL = "https://www.nicovideo.jp"
page = 1

#ニコニコ動画へのログイン
def login():
    url_login = "https://account.nicovideo.jp/login"
    browser.get(url_login)
    e = browser.find_element_by_name("mail_tel")
    e.clear()
    e.send_keys(USER)
    e = browser.find_element_by_name("password")
    e.clear()
    e.send_keys(PASS)
    btn = browser.find_element_by_id('login__submit')
    btn.click()

#前回結合していなかったときにbufferと結合しておく
def IntegrationBuffer():
    conn = sqlite3.connect("niconico.db")
    c = conn.cursor()

    for tag in c.execute("select tag from buffer"):
        c.execute("select tableName from tableDB where tag = %s" % tag[0])
        table = c.fetchone()
        c.execute("insert into %s(id,mylistNum) select id,mylistNum from buffer where tag = %s" % (table[0],tag[0]))

    conn.commit()
    conn.close()

#データベースが生成されているかチェックする存在しなければ生成する
def DBcheck(tag):
    conn = sqlite3.connect("niconico.db")
    c = conn.cursor()

    c.execute("select tableName from tableDB where tag = %s" % tag)
    tableName = c.fetchone()

    if not tableName:
        while True:
            name = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            c.execute("select count(*) from sqlite_master where type = 'table' and name = '%s'" % name)
            ch = int(c.fetchone()[0])
            if ch == 0:
                break;

        c.execute("create table %s(id int primary key,mylistNum int)" % name)
        c.execute("insert into tableDB(tag,tableName,mylistCount,mylistName) values (%s,%s,%s,%s)" % (tag,name,0,tag))

    conn.commit()
    conn.close()

#htmlからのデータ取得
def MainScraping(URL,mylistCount,mylistName):
    browser.get(rootURL + URL)
    time.sleep(0.5)
    name = None
    if TagCheck(tagName) == True:
        if mylistCount % 500 == 0:
            mylistName = mylistCreate(mylistName)
        else:
            mylistAdd(mylistName)
        myListCount += 1
    time.sleep(10)
    conn = sqlite3.connect('niconico.db')
    c = conn.cursor()

    #buffer table にデータを残しておく
    c.execute("insert into buffer(id,mylistNum,tag) values (%s,%s,%s)" % (int(URL[9:17]),int(myListCount/500+1),tagName))

    conn.commit()
    conn.close()
    print(URL[9:17]+"finish")

    return mylistCount,mylistName

#マイリスの生成
def mylistCreate(mylistCount):
    mylistName = "%sその%s" % (tagName,str(int(mylistCount/500+1)))
    while True:
        try:
            btn = browser.find_elements_by_css_selector('button.ActionButton.VideoMenuContainer-button')
            btn[0].click()
            btn = browser.find_element_by_xpath('//*[@data-mylist-id="-2"]')
            btn.click()
            e = browser.find_element_by_css_selector('input.AddMylistModal-nameInput')
            e.send_keys(mylistName)
            btn = browser.find_element_by_css_selector('button.ActionButton.AddMylistModal-submit')
            btn.click()
            print("mylistCreate:success")
            break
        except:
            time.sleep(10)
            browser.refresh()

    return mylistName

#マイリス追加
def mylistAdd(mylistName):
    while True:
        try:
            btn = browser.find_elements_by_css_selector('button.ActionButton.VideoMenuContainer-button')
            btn[0].click()
            btn = browser.find_element_by_xpath('//*[@data-mylist-name="%s"]' % mylistName)
            btn.click()
            btn = browser.find_element_by_css_selector("button.ActionButton.AddMylistModal-submit")
            btn.click()
            print("mylistAdd:success")
            break
        except:
            time.sleep(10)
            browser.refresh()

#タグ固定のチェック
def TagCheck(tag):
    while True:
        check = False
        if not browser.page_source:
            time.sleep(1)
            browser.refresh()
            continue
        soup = BeautifulSoup(browser.page_source, "lxml")
        #タグ情報を取得(タグロック済み、ニコニコ大百科あり)
        lookTagList = soup.select(".TagItem.is-locked.is-nicodicAvailable")
        lookTagList.extend(soup.select(".TagItem.is-locked"))

        if not lookTagList:
            access = soup.find("h1").text
            print(access)
            if access == "短時間での連続アクセスはご遠慮ください":
                time.sleep(70)
                browser.refresh()
                continue
            else:
                break
        for lookTag in lookTagList:
            tagName = lookTag.find("a",{"class":"Link TagItem-name"}).text
            if tagName.lower() == tag.lower():
                check = True
                break
        print("TagCheck:"+str(check))
        break
    return check

#データベースへの登録
def DataBaseAdd(tableName):
    conn = sqlite3.connect('niconico.db')
    c = conn.cursor()

    c.execute("insert into %s(id,mylistNum) select id,mylistNum from buffer" % tableName)

    conn.commit()
    conn.close()

#過去に登録したことがあるか
def Authentication(tableName,id):
    #Pivotの読み込み
    with open(jsonPath) as d:
        f = d.read()
        data = json.loads(f)

    conn = sqlite3.connect('niconico.db')
    c = conn.cursor()

    c.execute("select id from %s where id = %s" % (tableName,id))
    ch = c.fetchone()
    c.execute("select id from rmTable where id = %s" % id)
    check = ch + c.fetchone()

    print(check)
    if check:
        print("Authentication:True")
        return True
    else:
        print("Authentication:False")
        return False

#追加処理-発火ポイント
def AddMain():
    DBcheck(tagName)
    #mylistCount,mylistNameの取得
    #ここでタグ固有のデータベース名を取得する
    conn = sqlite3.connect('niconico.db')
    c = conn.cursor()

    c.execute("select tableName,mylistCount,mylistName from tableDB where tag = %s" % tagName)
    confList = c.fetchone()

    conn.close()

    tableName = confList[0]
    mylistCount = confList[1]
    mylistName = confList[2]

    page = 1

    login()

    checkurl = "https://www.nicovideo.jp/tag/%s?page=%s&sort=f&order=a" % (tagName,page)

    browser.get(checkurl)

    while True:
        soup = BeautifulSoup(browser.page_source, "lxml")
        maindiv = soup.find("div",{"class":"contentBody video uad videoList videoList01"})
        if not maindiv:
            print("finish")
            break
        rawList = maindiv.select(".itemThumbWrap")

        URLs = []

        for raw in rawList:
            URLs.append(raw.get("href"))

        URLs = [x for x in URLs if x != "#" and "api" not in x]

        for URL in URLs:
            print(URL[9:17]+"start")
            if Authentication(tableName,int(URL[9:17])) == True:
                continue
            mylistCount,mylistName = MainScraping(URL,mylistCount,mylistName)

        page += 1
        checkurl = "https://www.nicovideo.jp/tag/%s?page=%s&sort=f&order=a" % (tagName,page)
        browser.get(checkurl)
        time.sleep(10)

    DataBaseAdd(tableName)
    browser.quit()

#レギュ違反DB登録
def IdAdd(id):
    conn = sqlite3.connect('niconico.db')
    c = conn.cursor()

    c,execute("insert into rmTable(id) valeus (%s)" % id)

    conn.commit()
    conn.close()
    print(pivot)
    print(pivotPoint)

#動画データのマイリス保存先検索
def Check(id):
    conn = sqlite3.connect('niconico.db')
    c = conn.cursor()

    c.execute("select id from rmTable where id = %s" % id)
    rmed = c.fetchone()

    if rmed:
        return "removed"

    ans = []

    for tag in c.execute("select tag,tableName,mylistName from tableDB"):
        c.execute("select mylistNum from %s where id = %s" % (tag[1],id))
        myNum = c.fetchone()

        if myNum:
            ans.append([tag[2],myNum[0]]) #[[mylistName,mylistNum]...]

    if ans:
        return ans
    else:
        return None

#削除発火ポイント
def RemoveMain():
    passid = int(input("id>"))
    answer = Check(passid)
    if answer = "removed":
        print("This ID is registered")
    else if not answer:
        print("Register this ID")
        IdAdd(passid)
    else:
        print("Already added\nPlease delete it manually\nmylistName")
        for mylist in answer:
            print("\t%sその%s" % (mylist[0],mylist[1]))
            IdAdd(passid)
