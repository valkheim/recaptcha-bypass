import os
import sys
import time
from optparse import OptionParser

import requests
import selenium
import speech_recognition as sr
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from converter import convert
from recognition import recognize


def wait():
    time.sleep(1)


def clean():
    try:
        os.remove("audio.mp3")
        os.remove("audio.wav")

    except FileNotFoundError as _:
        pass


def get_browser(url: str):
    options = webdriver.FirefoxOptions()
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    browser = webdriver.Firefox(options=options)
    browser.get(url)
    return browser


def get_captcha(browser):
    recaptchaFrame = browser.find_element_by_tag_name("iframe")
    frameName = recaptchaFrame.get_attribute("name")
    browser.switch_to.frame(recaptchaFrame)
    CheckBox = WebDriverWait(browser, 6).until(
        EC.presence_of_element_located((By.ID, "recaptcha-anchor"))
    )
    CheckBox.send_keys(Keys.ENTER)
    browser.switch_to.default_content()
    wait()
    captcha = browser.find_elements_by_tag_name("iframe")[2]
    return captcha


def get_audio(browser, captcha):
    browser.switch_to.frame(captcha)
    audio = browser.find_element_by_css_selector("#recaptcha-audio-button")
    wait()
    audio.send_keys(Keys.ENTER)
    browser.switch_to.default_content()
    voice = browser.find_elements_by_tag_name("iframe")[
        2
    ]  # title = recaptcha challenge
    browser.switch_to.frame(voice)
    wait()
    download = browser.find_element_by_css_selector(".rc-audiochallenge-tdownload-link")
    # download.send_keys(Keys.ENTER)
    audio_url = browser.find_element_by_css_selector(
        ".rc-audiochallenge-tdownload-link"
    ).get_attribute("href")
    return audio_url


def get_wav(audio_url):
    wait()
    req = requests.get(audio_url)
    with open("audio.mp3", "wb") as f:
        f.write(req.content)

    os.system("ffmpeg -i audio.mp3 audio.wav -y > /dev/null 2>&1")


def serialize_voice():
    filename = os.path.expanduser("audio.wav")
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)


def resolve_captcha(browser):
    captcha = get_captcha(browser)
    audio_url = get_audio(browser, captcha)
    get_wav(audio_url)
    answer = serialize_voice()
    result = browser.find_element_by_css_selector("#audio-response")
    result.send_keys(answer, Keys.ENTER)
    wait()
    res = browser.find_element_by_css_selector(".rc-audiochallenge-error-message")
    failure = "please solve more" in browser.page_source
    if failure:
        return None

    return answer


if __name__ == "__main__":
    target_url = "https://www.google.com/recaptcha/api2/demo"
    clean()
    browser = get_browser(target_url)
    try:
        answer = resolve_captcha(browser)
        print("answer:", answer)

    except Exception as err:
        print(err, file=sys.stderr)

    browser.quit()
