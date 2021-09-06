from selenium import webdriver
from bs4 import BeautifulSoup
import lxml
import sqlite3
import time
import os
import random
import string
import tkinter as tk
import Twindow
import requests
import urllib

cwd = os.path.split(os.path.realpath(__file__))[0]
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

header = {"User-Agent":"Hiziki"}

rootURL = "https://www.nicovideo.jp"
page = 1

#ニコニコ動画へのログイン
def login(browser):
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
def StartUp():
	conn = sqlite3.connect("niconico.db")
	c = conn.cursor()

	#buffer table に追加されているデータのタグ情報でfor分を回す
	for mylistName in c.execute("select mylistName from buffer"):
		#そのタグのテーブルを探す
		c.execute("select tableName from tableDB where mylistName = '%s'" % mylistName[0])
		table = c.fetchone()[0]
		#buffer table のデータをタグテーブルに移す
		c.execute("insert into %s(id,mylistNum) select id,mylistNum from buffer where mylistName = '%s'" % (table,mylistName[0]))
		#タグテーブルのデータ数を出す
		c.execute("select count(*) from %s" % table)
		#マイリスト登録数を更新する
		c.execute("update tableDB set mylistCount = %s where mylistName = '%s'" % (c.fetchone()[0],mylistName[0]))

	#buffer table 内のデータを全て削除する
	c.execute("delete from buffer")
	conn.commit()
	conn.close()

#データベースが生成されているかチェックする存在しなければ生成する
def DBcheck(mylistName):
	conn = sqlite3.connect("niconico.db")
	c = conn.cursor()

	#タグテーブル名の取得
	c.execute("select tableName from tableDB where mylistName = '%s'" % mylistName)
	tableName = c.fetchone()

	#タグテーブルが無かった場合
	if not tableName:
		#ランダムな文字列を生成
		while True:
			name = ''.join(random.choices(string.ascii_letters, k=10))
			#そのテーブルが存在するかをチェック
			c.execute("select count(*) from sqlite_master where type = 'table' and name = '%s'" % name)
			ch = int(c.fetchone()[0])
			if ch == 0:
				break

		#テーブルの生成
		c.execute("create table %s(id int primary key,mylistNum int)" % name)
		#インデックスを生成して検索速度をあげる
		c.execute("create index idindex%s on %s(id)" % (name,name))
		#テーブルDBにデータを追加する
		c.execute("insert into tableDB values ('%s','%s',%s)" % (mylistName,name,0))

	conn.commit()
	conn.close()

#htmlからのデータ取得
def MainScraping(URL,title,mylistCount,mylistName,browser):
	if int(mylistCount/500) >= 1:
		name = "%sその%s" % (mylistName,int(mylistCount/500)+1)
	else:
		name = mylistName
	chkCp = [x for x in chkTagList]
	excCp = [x for x in excTagList]
	browser.get(rootURL + URL)
	time.sleep(0.5)
	#タグ固定のチェック
	if TagCheck(title,chkCp,excCp,browser) == True:
		if mylistCount % 500 == 0 and not mylistChk(name,browser):
			#マイリストの生成
			mylistCreate(name,browser)
			browser.get(rootURL + URL)
			time.sleep(0.5)

		#マイリストへ追加
		mylistAdd(name,browser)
		mylistCount += 1

	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#buffer table にデータを残しておく
	c.execute("insert into buffer(id,mylistNum,mylistName) values ('%s','%s','%s')" % (int(URL[9:17]),int(mylistCount/500),mylistName))

	conn.commit()
	conn.close()

	time.sleep(10)
	print(URL[9:17]+"finish")

	return mylistCount

def mylistChk(name,browser):
	while True:
		try:
			btn = browser.find_elements_by_css_selector('button.ActionButton.VideoMenuContainer-button')
			btn[0].click()
		except:
			time.sleep(10)
			browser.refresh()
			continue
		try:
			browser.find_element_by_xpath('//*[@data-mylist-name="%s"]' % name)
		except:
			break
		else:
			btn[0].click()
			print("mylistChk:True")
			return True
	btn[0].click()
	print("mylistChk:False")
	return False

#マイリスの生成
def mylistCreate(name,browser):
	while True:
		try:
			createURL = "https://www.nicovideo.jp/my/mylist"
			browser.get(createURL)
			btn = browser.find_element_by_css_selector('button.ModalActionButton.MylistsContainer-actionItem')
			btn.click()
			e = browser.find_element_by_name('title')
			e.clear()
			e.send_keys(name)
			btn = browser.find_element_by_css_selector('label.RadioItem-label')
			btn.click()
			btn = browser.find_element_by_css_selector('button.ModalContent-footerSubmitButton')
			btn.click()
			print("mylistCreate:success")
			break
		except:
			time.sleep(10)
			browser.refresh()

#マイリス追加
def mylistAdd(name,browser):
	while True:
		try:
			btn = browser.find_elements_by_css_selector('button.ActionButton.VideoMenuContainer-button')
			btn[0].click()
			btn = browser.find_element_by_xpath('//*[@data-mylist-name="%s"]' % name)
			btn.click()
			btn = browser.find_element_by_css_selector("button.ActionButton.AddMylistModal-submit")
			btn.click()
			print("mylistAdd:success")
			break
		except:
			time.sleep(10)
			browser.refresh()

#タグ固定のチェック
def TagCheck(title,chkTags,excTags,browser):
	while True:
		check = False
		if not browser.page_source:
			time.sleep(1)
			browser.refresh()
			continue
		soup = BeautifulSoup(browser.page_source, "lxml")

		access = soup.find("h1").text
		print(access,title)
		if access != title:
			print("error")
			time.sleep(70)
			browser.refresh()
			continue

		#タグ情報を取得(タグロック済み、ニコニコ大百科あり)
		lookTagList = soup.select(".TagItem.is-locked.is-nicodicAvailable")
		lookTagList.extend(soup.select(".TagItem.is-locked"))

		for lookTag in lookTagList:
			tagName = lookTag.find("a",{"class":"Link TagItem-name"}).text
			if tagName.lower() in excTags:
				return check
			if tagName.lower() in chkTags:
				chkTags.remove(tagName.lower())
		break
	if not chkTags:
		check = True
	print("TagCheck:"+str(check))
	return check

#データベースへの登録
def DataBaseAdd(tableName):
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#bufferからタグテーブルにデータを移す
	c.execute("insert into %s select id,mylistNum from buffer" % tableName)

	#buffer table 内のデータを全て削除する
	c.execute("delete from buffer")

	conn.commit()
	conn.close()

#過去に登録したことがあるか
def Authentication(tableName,id):
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#タグテーブルからIDを検索
	c.execute("select id from %s where id = '%s'" % (tableName,id))
	ch = c.fetchone()
	#除外テーブルからIDを検索
	c.execute("select id from rmTable where id = '%s'" % id)
	check = c.fetchone()

	print(check,ch)
	#除外テーブル、タグテーブルに該当した場合
	if check or ch:
		print("Authentication:True")
		return True
	#どちらも該当しなかった場合
	else:
		print("Authentication:False")
		return False

#追加処理-発火ポイント
def Add():
	DBcheck(mylistName)

	#chrome driver の起動
	browser = webdriver.Chrome(cwd+"/lib/chromedriver.exe",chrome_options=options)
	browser.implicitly_wait(1)

	#mylistCount,mylistNameの取得
	#ここでタグ固有のデータベース名を取得する
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#おおもとのテーブルからテーブル名、マイリスト登録数、マイリスト名を取得
	c.execute("select tableName,mylistCount from tableDB where mylistName = '%s'" % mylistName)
	confList = c.fetchone()

	conn.close()

	tableName = confList[0]
	mylistCount = confList[1]

	page = 1

	login(browser)
	response = requests.get("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search?q={}&targets=tagsExact&fields=contentId,title&_sort=%2BstartTime&_offset={}&_limit=100&_context=Hiziki".format(" ".join(chkTagList),0),headers=header).json()
	DataList = [["/watch/"+movieInfo["contentId"],movieInfo["title"]] for movieInfo in response["data"]]
	Maxloop = response["meta"]["totalCount"]//100

	i = 1
	while(i != Maxloop):
		time.sleep(1)
		i += 1
		response = requests.get("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search?q={}&targets=tagsExact&fields=contentId,title&_sort=%2BstartTime&_offset={}&_limit=100&_context=Hiziki".format(" ".join(chkTagList),i*100),headers=header).json()
		DataList.extend([["/watch/"+movieInfo["contentId"],movieInfo["title"]] for movieInfo in response["data"]])

	for data in DataList:
		print(data[0][9:17]+"start")
		#マイリスト追加済みかどうか
		if Authentication(tableName,int(data[0][9:17])) == True:
			continue

		mylistCount = MainScraping(data[0],data[1],mylistCount,mylistName,browser)

	#データベースにbufferのデータを移す
	DataBaseAdd(tableName)
	browser.quit()

#レギュ違反DB登録
def IdAdd(id):
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#削除テーブルに登録する
	c.execute("insert into rmTable values ('%s')" % id)

	conn.commit()
	conn.close()

#動画データのマイリス保存先検索
def Check(id):
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#除外登録済みのデータを探す
	c.execute("select id from rmTable where id = '%s'" % id)
	rmed = c.fetchone()

	#削除登録済みだった場合
	if rmed:
		return "removed"

	ans = []

	#マイリスト追加済みかを探す
	for tData in c.execute("select tableName,mylistName from tableDB"):
		c.execute("select mylistNum from %s where id = '%s'" % (tData[0],id))
		myNum = c.fetchone()

		if myNum:
			ans.append([tData[1],myNum[0]]) #[[mylistName,mylistNum]...]

	#マイリスト追加済みだった場合
	if ans:
		return ans
	#追加されていなかった場合
	else:
		return None

#削除発火ポイント
def Remove():
	#削除登録するID
	passids = twin.RmIds()

	root = tk.Tk()
	root.title("hiZiKi")
	rwin = Twindow.Rwindow(root)
	#この内部処理をtkinterに回そう(もう一度立ち上げなおす)
	for passid in passids:
		#そのIDがどこのタグで登録済みチェックする
		answer = Check(passid)

		#削除登録済みだった場合
		if answer == "removed":
			rwin.AddTxt("%s:This ID is registered"%passid)
			print("This ID is registered")
		#削除登録されていなかった場合
		elif not answer:
			rwin.AddTxt("%s:Register this ID"%passid)
			print("Register this ID")
			#IDを除外登録する
			IdAdd(passid)
		#既にマイリスト追加済みだった場合
		else:
			rwin.AddTxt("%s:Already added"%passid)
			rwin.AddTxt("Please delete it manually")
			rwin.AddTxt("mylistName")
			print("Already added\nPlease delete it manually\nmylistName")
			for mylist in answer:
				if mylist[1] != 0:
					rwin.AddTxt("%sその%s"%(mylist[0],mylist[1]+1))
					print("\t%sその%s\n" % (mylist[0],mylist[1]+1))
				else:
					rwin.AddTxt("%s"%mylist[0])
					print("\t%s\n" % mylist[0])
				#IDを除外登録する
				IdAdd(passid)

	root.mainloopop()

#テーブルの削除
def RmTable():
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	#タグ用テーブル名の取得
	c.execute("select tableName from tableDB where tag = '%s'" % tagName)
	tableName = c.fetchone()[0]
	print(tableName)

	if not tableName:
		print("There is no table\n")
		return

	#テーブルと登録データの削除
	c.execute("drop table %s" % tableName)
	c.execute("delete from tableDB where tag = '%s'" % tagName)
	c.execute("delete from buffer where tag = '%s'" % tagName)

	conn.commit()
	conn.close()
	print("drop table")

#これ修正必要
def NameChange():
	conn = sqlite3.connect('niconico.db')
	c = conn.cursor()

	mylistName = input("mylistName>")

	#タグ用テーブル名の取得
	c.execute("update tableDB set mylistName = '%s' where tag = '%s'" % (mylistName,tagName))

	conn.commit()
	conn.close()

StartUp()

root = tk.Tk()
root.title("hiZiKi")

twin = Twindow.Twindow(root)

#mode選択
mode = twin.Mode()

#マイリスト除外登録
if mode == "rm":
	Remove()

'''
#機能移行予定
#テーブルの削除
if mode == "rmtable":
	RmTable()

if mode == "namechange":
	NameChange()
'''

#マイリスト追加
if mode == "add":
	#探すタグの指定
	chkTagList,excTagList = twin.Tags()
	#ニコニコログイン用のデータの取得
	USER,PASS = twin.LoginData()
	mylistName = twin.MylistName()
	Add()
