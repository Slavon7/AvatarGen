from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from config import load_config
import time

config = load_config()
EMAIL = config["EMAIL"]
PASSWORD = config["PASSWORD"]

def find_avatar_video(driver):
    """
    Пробуем разные способы найти и нажать Avatar video
    """
    
    strategies = [
        # Стратегия 1: Оригинальный селектор
        lambda: driver.find_element(By.XPATH, '//div[@class="featureItem-muTBA6 featureItemClickable-UOMJKh"]//div[text()="Avatar video"]'),
        
        # Стратегия 2: Поиск по частичному тексту
        lambda: driver.find_element(By.XPATH, '//div[contains(@class, "featureItem") and contains(@class, "featureItemClickable")]//div[contains(text(), "Avatar")]'),
        
        # Стратегия 3: Поиск только по title
        lambda: driver.find_element(By.XPATH, '//div[@class="lv-typography featureTitle-iOW9Ff" and contains(text(), "Avatar")]'),
        
        # Стратегия 4: Поиск по изображению
        lambda: driver.find_element(By.XPATH, '//img[contains(@src, "avatar")]//ancestor::div[contains(@class, "featureItem")]'),
        
        # Стратегия 5: CSS селектор с проверкой текста
        lambda: next((item for item in driver.find_elements(By.CSS_SELECTOR, '.featureItem-muTBA6.featureItemClickable-UOMJKh') if "avatar" in item.text.lower()), None),
    ]
    
    for i, strategy in enumerate(strategies, 1):
        try:
            print(f"🔍 Попытка найти Avatar video - стратегия {i}...")
            
            # Ждем загрузки элементов
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "featureItem-muTBA6"))
            )
            
            element = strategy()
            
            if element:
                # Прокручиваем к элементу
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)
                
                # Пробуем клик
                try:
                    element.click()
                    print(f"✅ Avatar video найден и нажат (стратегия {i})")
                    return True
                except:
                    driver.execute_script("arguments[0].click();", element)
                    print(f"✅ Avatar video найден и нажат через JS (стратегия {i})")
                    return True
                    
        except Exception as e:
            print(f"❌ Стратегия {i} не сработала: {e}")
            continue
    
    # Отладочная информация
    print("🔍 Отладка - доступные элементы:")
    try:
        all_elements = driver.find_elements(By.XPATH, '//div[contains(@class, "featureItem")]')
        for i, elem in enumerate(all_elements[:10]):  # Показываем первые 10
            try:
                text = elem.text.strip()
                if text:
                    print(f"  {i+1}. '{text}'")
            except:
                pass
    except:
        pass
    
    return False

def login(driver):
    wait = WebDriverWait(driver, 20)

    try:
        # Шаг 1: Кнопка входу
        print("🔍 Ищем кнопку Log in...")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[span[text()="Log in"]]'))
        )
        login_button.click()
        print("✅ Кнопка Log in нажата")

        # Шаг 2: Continue with email
        print("🔍 Ищем кнопку Continue with email...")
        continue_with_email = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//div[span[text()="Continue with email"]]'
            ))
        )
        continue_with_email.click()
        print("✅ Continue with email нажата")

        # Шаг 3: Ввод email
        print("🔍 Ищем поле email...")
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                '//input[@placeholder="Enter email"]'
            ))
        )
        email_input.clear()
        email_input.send_keys(EMAIL)
        print("✅ Email введен")

        # Шаг 4: Ввод пароля
        print("🔍 Ищем поле пароля...")
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                '//input[@placeholder="Enter password"]'
            ))
        )
        password_input.clear()
        password_input.send_keys(PASSWORD)
        print("✅ Пароль введен")

        # Шаг 5: Continue
        print("🔍 Ищем кнопку Continue...")
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//button[span[text()="Continue"]]'
            ))
        )
        continue_button.click()
        print("✅ Continue нажата")

        # Шаг 6: Закрытие модального окна (опционально)
        print("🔍 Пытаемся закрыть модальное окно...")
        
        close_selectors = [
            '//span[contains(@class, "lv-modal-close-icon")]',
            '//button[contains(@class, "close")]',
            '//div[contains(@class, "modal-close")]',
            '//span[contains(@class, "close")]',
            '//*[@data-testid="close-button"]',
            '//button[@aria-label="Close"]'
        ]
        
        modal_closed = False
        for selector in close_selectors:
            try:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                close_button.click()
                print(f"✅ Модальное окно закрыто селектором: {selector}")
                modal_closed = True
                break
            except TimeoutException:
                continue
        
        if not modal_closed:
            print("⚠️ Модальное окно не найдено или уже закрыто")
            # Пробуем нажать Escape
            try:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                print("✅ Нажата клавиша Escape")
            except:
                pass

        # Ждем загрузки страницы после логина
        time.sleep(3)
        
        # Шаг 7: Поиск Avatar video
        print("🔍 Ищем Avatar video...")
        
        if find_avatar_video(driver):
            print("✅ Avatar video найден и нажат!")
            time.sleep(5)
        else:
            print("❌ Не удалось найти Avatar video")
            # Попробуем подождать и поискать еще раз
            print("🔄 Ждем еще 5 секунд и пробуем снова...")
            time.sleep(5)
            
            if find_avatar_video(driver):
                print("✅ Avatar video найден при повторной попытке!")
                time.sleep(5)
            else:
                print("❌ Avatar video так и не найден")
                
                # Показываем текущий URL для отладки
                current_url = driver.current_url
                print(f"🌐 Текущий URL: {current_url}")
                
                # Попробуем найти любые кнопки с "Avatar" в тексте
                try:
                    avatar_elements = driver.find_elements(By.XPATH, '//*[contains(text(), "Avatar")]')
                    if avatar_elements:
                        print(f"🔍 Найдено {len(avatar_elements)} элементов с 'Avatar':")
                        for i, elem in enumerate(avatar_elements[:5]):
                            try:
                                print(f"  {i+1}. {elem.text} (тег: {elem.tag_name})")
                            except:
                                pass
                        
                        # Пробуем кликнуть первый найденный
                        try:
                            avatar_elements[0].click()
                            print("✅ Кликнули на первый элемент с 'Avatar'")
                        except Exception as e:
                            print(f"❌ Не удалось кликнуть: {e}")
                except Exception as e:
                    print(f"❌ Ошибка поиска элементов с Avatar: {e}")

    except TimeoutException as e:
        print(f"❌ Timeout ошибка на этапе авторизации: {e}")
        # Показываем текущее состояние страницы
        try:
            page_source_snippet = driver.page_source[:500]
            print(f"🔍 Начало HTML страницы: {page_source_snippet}")
        except:
            pass
        raise
    except Exception as e:
        print(f"❌ Общая ошибка авторизации: {e}")
        raise