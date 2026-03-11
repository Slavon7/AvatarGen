import time
from selenium.webdriver.common.by import By

def slow_type(element, text, delay=0.1):
    for char in text:
        element.send_keys(char)
        time.sleep(delay)

def handle_pippit_modal(driver, timeout=10):
    """
    Проверяет и закрывает модалку "Install Pippit app?", если она появилась.
    """
    try:
        print("🔍 Перевіряємо наявність вікна 'Install Pippit app?'...")
        time.sleep(timeout)
        cancel_button = driver.find_element(
            By.XPATH,
            '//button[.//span[text()="Cancel"]]'
        )
        cancel_button.click()
        print("🔘 Натиснули кнопку 'Cancel' у модалці 'Install Pippit app?'")
        time.sleep(1)
    except Exception:
        print("ℹ️ Модальне вікно 'Install Pippit app?' не зʼявилося або вже зникло.")
