import azure.cognitiveservices.speech as sp
import webbrowser
from googlesearch import search
import re
import textdistance as td
import collections
import time
import cv2
import dlib
import imutils
import requests
from bs4 import BeautifulSoup
from selenium import webdriver


num_tab = {'uno':1, 'due':2, 'tre':3, 'quattro':4, 'cinque':5, 'sei':6, 'sette':7, 'otto':8, 'nove':9, 'dieci':10, 'undici':11, 'dodici':12,
                'tredici':13, 'quattordici':14, 'quindici':15, 'sedici':16, 'diciassette':17, 'diciotto':18, 'diciannove':19, 'venti':20,
            'one':1, 'two':2, 'three':3, 'four':4, 'five':5, 'six':6, 'seven':7, 'eight':8, 'nine':9, 'ten':10, 'eleven':11, 'twelve':12}


def speechInit():
    speech_key, service_region = 'AZURE-KEY', 'uksouth'
    speech_config = sp.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language='it-IT'
    speech_recognizer = sp.SpeechRecognizer(speech_config=speech_config)
    return speech_recognizer

def speech2query(speech_recognizer):
    result = speech_recognizer.recognize_once()
    print(result.text)

    query = result.text.replace(' ', '+').replace('.','').replace(',','')
    return query


def googleThemAll(query):
    page_dict = dict()
    page_links = list()
    page_names = list()
    i = 0
    for entry in search(query, tld='com', lang='en', tbs='0', num=4, start=0, stop=4):
        page_links.append(entry)

        url = str(entry)
        r = requests.get(url)
        html_content = r.text
        soup = BeautifulSoup(html_content, 'lxml')
        if soup.title == None: continue
        title = soup.title.string
        print(title)
        page_dict[title] = entry

        i+=1
    return page_links, page_names, page_dict


def match(query, page_dict):
    tmp_dict = dict()
    scores = list()
    for title,link in page_dict.items():
        scores.append(td.hamming.normalized_distance(query, title))
        tmp_dict[td.hamming.normalized_distance(query, title)] = link
    collections.OrderedDict(sorted(tmp_dict.items()))
    return next(iter(tmp_dict.values())), scores


def searchMySpeech(driver, speech_recognizer):
    query = speech2query(speech_recognizer)
    token = query.split("+")[0]
    if query == '': return
    if td.hamming.normalized_distance(token.lower(),'google') == 0:
        query = query.replace("'",' ')
        driver = openPage(f'https://google.com/search?q={query[len(token):]}', driver)
        return driver
    page_dict = googleThemAll(query)[2] # taking only the third returned value (the dict)
    pageLink, scores = match(query, page_dict)
    print(scores)
    print(pageLink)
    driver = openPage(pageLink, driver)
    return driver


def openPage(pageLink, driver):
    if driver == None:
        driver = webdriver.Firefox(executable_path=r'/usr/local/bin/geckodriver')
    if driver.current_url == 'about:blank':
        driver.get(pageLink)
    else:
        prev_wind = set(driver.window_handles)
        driver.execute_script("window.open('"+pageLink+"')")
        post_wind = set(driver.window_handles)
        new_window = (post_wind - prev_wind.intersection(post_wind)).pop()
        driver.switch_to.window(new_window)
    return driver


def isFist(frame, fist_cascade):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_gray = cv2.equalizeHist(frame_gray)
    fists = fist_cascade.detectMultiScale(frame_gray, 1.3, 5)
    if len(fists) == 0:
        #print("no fist here")
        return False
    else:
        for (x,y,w,h) in fists:
            frame = cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        return True


def fistDecisions(speech_recognizer, driver):
    print("What should i do? |Chiudi| (to close a tab), |Esci| (to exit from the broswer), |Tab num| (to switch at num tab)")
    token = (speech_recognizer.recognize_once()).text.lower()
    token = token.replace('?','').replace(',','').replace('.','').replace('!','').replace('-','')
    tkn_lst = token.split(' ') if ' ' in token else []
    if token == 'esci' or (token == 'chiudi' and len(driver.window_handles)==1):
        driver.quit()
        driver = None
    elif token == 'chiudi':
        lst_ws = driver.window_handles
        curr = driver.current_window_handle
        curr_id = [i for i,x in enumerate(lst_ws) if x == curr][0]
        print(curr_id)
        driver.close()
        curr_id = curr_id-1 if curr_id >= 1 else curr_id+1
        print(curr_id)
        driver.switch_to_window(lst_ws[curr_id])
    elif len(tkn_lst) >= 2 and tkn_lst[0] == 'tab':
        if tkn_lst[1] in num_tab.keys():
            num = num_tab.get(tkn_lst[1])
            driver.switch_to_window(driver.window_handles[num-1]) if num <= len(driver.window_handles) else print(f"!!WARNING!! Tab number {num} doens't exist.")
        else:
            print("Try again, something gone wrong.")
            return driver
    return driver



def runProject():
    fist_cascade = cv2.CascadeClassifier()
    fist_cascade.load('./fist.xml')
    # <-- hand detector with dlib -->
    detector = dlib.fhog_object_detector("./HandDetector.svm") 
    speech_recognizer = speechInit()
    try :
        win = dlib.image_window()
        driver = None
        cap = cv2.VideoCapture(0)
        fistCount = 0
        while True:
            win.clear_overlay()
            ret, image = cap.read()

            #image = imutils.resize(image, width=800)
            win.set_image(image)

            if isFist(image,fist_cascade):
                print("«-- Fist Found --»")
                if fistCount < 5:
                    fistCount += 1
                elif fistCount == 5 and driver == None:
                    fistCount = 0
                    print("«-- Can't close something that is not open --»")
                elif fistCount == 5 and not(driver == None):
                    fistCount = 0
                    driver = fistDecisions(speech_recognizer, driver)
                continue
            else:
                fistCount = 0


            rects = detector(image)
            win.add_overlay(rects)

            if len(rects) == 0:
                count = 0
                print("NOT detected")
                time.sleep(0.4)
            else:
                count+=1
                print("detected")
                if count==8:
                    driver = searchMySpeech(driver, speech_recognizer)
                    count=0
    except KeyboardInterrupt:
        cap.release()
        driver.quit() if not(driver==None) else None

if __name__ == '__main__':
    runProject()
    