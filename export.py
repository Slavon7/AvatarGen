from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from text_loader import get_default_text_id
from config import load_config
import time

config = load_config()
WITH_WATERMARK = config.get("WITH_WATERMARK", True)
RESOLUTION = config.get("RESOLUTION", "1080p")
QUALITY = config.get("QUALITY", "Better quality")
FRAMERATE = config.get("FRAMERATE", "30fps")
FORMAT = config.get("FORMAT", "MP4")

def export_video(driver, with_watermark=True, video_name=""):
    wait = WebDriverWait(driver, 20)

    # Натискаємо кнопку експорту
    export_button = wait.until(
        EC.element_to_be_clickable((
            By.XPATH,
            '//button[contains(@class, "export-button") and .//div[text()="Export video"]]'
        ))
    )
    export_button.click()
    time.sleep(2)

    try:
        got_it_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(@class, 'btn-Cf0Te3') and .//span[text()='Got it']]"
            ))
        )
        got_it_button.click()
        print("Натиснуто кнопку 'Got it'")
    except Exception as e:
        print(f"Кнопка 'Got it' не знайдена або не клікабельна: {e}")

    # Встановити назву відео
    try:
        name_input = wait.until(
            EC.presence_of_element_located((By.ID, "form-name_input"))
        )
        video_name = video_name or "Untitled"
        name_input.clear()
        name_input.send_keys(video_name)
        print(f"Назва відео встановлена: {video_name}")
        time.sleep(1)
    except Exception as e:
        print(f"Помилка при зміні назви відео: {e}")

    # Вибір опції водяного знаку
    try:
        watermark_dropdown = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.lv-select.lv-select-single"))
        )
        watermark_dropdown.click()
        print("Випадаючий список ватермарки відкрито")
        time.sleep(1)

        desired_option_text = "With watermark" if WITH_WATERMARK else "No watermark"

        watermark_options = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '//li[@role="option"]'))
        )

        for option in watermark_options:
            if desired_option_text in option.text.strip():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.5)
                option.click()
                print(f'Обрано опцію: {desired_option_text}')
                break
        time.sleep(1)
    except Exception as e:
        print(f"Помилка при виборі опції ватермарки: {e}")

    # Вибір роздільної здатності (resolution)
    try:
        # Знайти і клікнути на селектор резолюшена
        resolution_dropdown = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "lv-select-view")][.//span[contains(text(),"p")]]'))
        )
        resolution_dropdown.click()
        print("Випадаючий список роздільної здатності відкрито")
        time.sleep(1)

        # Вибрати потрібне значення
        resolution_options = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '//li[@role="option"]//span'))
        )

        for option in resolution_options:
            if RESOLUTION in option.text.strip():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.5)
                option.click()
                print(f"Обрана роздільна здатність: {RESOLUTION}")
                break

        time.sleep(1)
    except Exception as e:
        print(f"Помилка при виборі роздільної здатності: {e}")

    # Вибір якості відео
    try:
        # Знайти і клікнути на селектор якості
        quality_dropdown = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//div[contains(@class, "lv-select-view") and .//span[text()="Recommended" or text()="Better quality" or text()="Faster export"]]'
            ))
        )
        quality_dropdown.click()
        print("Випадаючий список якості відкрито")
        time.sleep(1)

        # Отримуємо всі варіанти
        quality_options = wait.until(
            EC.presence_of_all_elements_located((
                By.XPATH,
                '//li[@role="option"]'
            ))
        )

        for option in quality_options:
            if QUALITY.lower() in option.text.strip().lower():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.5)
                option.click()
                print(f"Обрано якість: {QUALITY}")
                break

        time.sleep(1)
    except Exception as e:
        print(f"Помилка при виборі якості відео: {e}")

            # Вибір частоти кадрів (frame rate)
    try:
        # Знайти і клікнути на селектор frame rate
        framerate_dropdown = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//div[contains(@class, "lv-select-view") and .//span[contains(text(),"fps")]]'
            ))
        )
        framerate_dropdown.click()
        print("Випадаючий список частоти кадрів відкрито")
        time.sleep(1)

        # Отримати всі варіанти
        framerate_options = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '//li[@role="option"]'))
        )

        for option in framerate_options:
            if FRAMERATE.lower() in option.text.strip().lower():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.5)
                option.click()
                print(f"Обрано частоту кадрів: {FRAMERATE}")
                break

        time.sleep(1)
    except Exception as e:
        print(f"Помилка при виборі частоти кадрів: {e}")

    # Вибір формату відео
    try:
        format_dropdown = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//div[contains(@class, "lv-select-view") and .//span[contains(text(),"MP4") or contains(text(),"MOV")]]'
            ))
        )
        format_dropdown.click()
        print("Випадаючий список формату відео відкрито")
        time.sleep(1)

        format_options = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '//li[@role="option"]'))
        )

        for option in format_options:
            if FORMAT.lower() in option.text.strip().lower():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.5)
                option.click()
                print(f"Обрано формат відео: {FORMAT}")
                break

        time.sleep(1)
    except Exception as e:
        print(f"Помилка при виборі формату відео: {e}")

    # Кнопка Download
    download_button = wait.until(
        EC.element_to_be_clickable((
            By.XPATH,
            '//button[contains(@class, "export") and .//span[text()="Download"]]'
        ))
    )
    download_button.click()

    try:
        got_it_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(@class, 'lv-btn') and .//span[text()='Got it']]"
            ))
        )
        got_it_button.click()
        print("Натиснуто кнопку 'Got it'")
        time.sleep(5)
    except Exception as e:
        print(f"Кнопка 'Got it' не знайдена або не клікабельна: {e}")

    time.sleep(10)
    print("Експорт завершено")