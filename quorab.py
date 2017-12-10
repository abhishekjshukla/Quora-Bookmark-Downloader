

from selenium import webdriver
import time
import pyperclip
import pdfkit
from bs4 import BeautifulSoup
from urllib.request import urlopen


brow=webdriver.Chrome()
brow.get("https://www.quora.com/bookmarked_answers")
wait_inp=input("\n\n\t\tPress Enter after Bookmark page is Fully Loaded\n\n")


first_question=brow.find_element_by_class_name("question_link").text
brow.get("https://www.quora.com/bookmarked_answers?order=desc")


while True:
	brow.execute_script("window.scrollTo(0, document.body.scrollHeight);")
	currentQuestion=brow.find_elements_by_class_name("question_link")
	currentQuestion=currentQuestion[len(currentQuestion)-1].text
	if(first_question == currentQuestion):
		break


elem_share=brow.find_elements_by_link_text("Share")

options = {
	'page-size': 'Letter',
	'dpi': 450,
	'javascript-delay':10000
}


l=len(elem_share)
j=0
for i in range(l):
	try:
		elem_share[i].click()
		time.sleep(3)
		elem_copy=brow.find_element_by_link_text("Copy Link")
		elem_copy.click()
		ans_url=pyperclip.paste()
		conn=urlopen(ans_url)
		soup = BeautifulSoup(conn.read(),"html.parser")
		title=soup.find('a',class_="question_link").text
		pdfkit.from_url(ans_url,title+'.pdf',options=options)
	except:
		j+=1
		print("Fail",j)
	
print("Conversion Completed")







