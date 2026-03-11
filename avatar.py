from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import random

def handle_all_modals(driver, timeout=5):
    """
    Универсальная функция для закрытия всех возможных модальных окон
    """
    modals_closed = 0
    
    # Список возможных селекторов для закрытия модалок
    close_selectors = [
        # Кнопка Cancel в Pippit модалке
        '//button[.//span[text()="Cancel"]]',
        # Кнопка Close
        '//button[.//span[text()="Close"]]',
        # Кнопка X для закрытия
        '//button[contains(@class, "close") or contains(@aria-label, "close")]',
        # Общие селекторы для кнопок закрытия
        '//div[contains(@class, "modal")]//button[contains(@class, "close")]',
        '//div[contains(@class, "lv-modal")]//button',
        # ESC альтернатива
        '//div[contains(@class, "modal-wrapper")]',
    ]
    
    for selector in close_selectors:
        try:
            close_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            close_button.click()
            print(f"✅ Закрыли модалку через селектор: {selector}")
            modals_closed += 1
            time.sleep(1)
            break
        except:
            continue
    
    # Если ничего не сработало, пробуем ESC
    if modals_closed == 0:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            print("✅ Попытались закрыть модалку через ESC")
            time.sleep(1)
        except:
            pass
    
    return modals_closed > 0

def wait_for_modals_to_disappear(driver, max_wait=10):
    """
    Ожидаем исчезновения всех модальных окон
    """
    modal_selectors = [
        '//div[contains(@class, "lv-modal-wrapper")][@style*="display: block"]',
        '//div[contains(@class, "modal") and not(contains(@style, "display: none"))]',
        '//div[contains(@class, "loading-mbT0kx")]'
    ]
    
    for selector in modal_selectors:
        try:
            WebDriverWait(driver, max_wait).until(
                EC.invisibility_of_element_located((By.XPATH, selector))
            )
            print(f"✅ Модалка исчезла: {selector}")
        except:
            print(f"⚠️ Модалка все еще видна или не найдена: {selector}")

def choose_or_create_avatar(driver):
    wait = WebDriverWait(driver, 20)
    
    try:
        # Випадковий вибір аватара
        # Знаходимо всі контейнери аватарів
        avatar_containers = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, '//div[contains(@class, "container-osrlL5")]'))
        )
        
        # Виводимо кількість знайдених аватарів
        print(f"Знайдено аватарів: {len(avatar_containers)}")

        # Обираємо випадковий аватар
        if avatar_containers:
            random_avatar = random.choice(avatar_containers)
            
            # Отримуємо ім'я аватара для логування
            try:
                avatar_name = random_avatar.find_element(By.XPATH, './/div[contains(@class, "name-JDuJIY")]').text
                print(f"Обрано аватар: {avatar_name}")
            except:
                print("Не вдалося отримати ім'я аватара")
            
            # Прокручуємо до аватара щоб він був видимим
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", random_avatar)
            time.sleep(2)
            
            # Натискаємо кнопку "Apply" для обраного аватара
            try:
                apply_button = random_avatar.find_element(By.XPATH, './/button[.//span[text()="Apply"]]')
                
                # Убеждаемся что кнопка видима и кликабельна
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(apply_button))
                
                apply_button.click()
                print("Кнопка Apply натиснута")
            except Exception as e:
                print(f"Помилка при натисканні кнопки Apply: {e}")
                # Пробуємо альтернативний метод натискання
                try:
                    apply_button = random_avatar.find_element(By.XPATH, './/button[.//span[text()="Apply"]]')
                    driver.execute_script("arguments[0].click();", apply_button)
                    print("Кнопка Apply натиснута за допомогою JavaScript")
                except Exception as e2:
                    print(f"Не вдалося натиснути кнопку Apply навіть через JavaScript: {e2}")
                    return False

            # Очікуємо появи індикатора завантаження з текстом "Changing avatar..."
            try:
                loading_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "loading-mbT0kx")]//span[contains(text(), "Changing avatar")]'))
                )
                print("Знайдено індикатор завантаження. Очікуємо завершення...")
                
                # Функція для перевірки відсотка завантаження
                def get_progress():
                    try:
                        progress_element = driver.find_element(By.XPATH, '//span[contains(@class, "progress-FVdlMV")]')
                        return progress_element.text
                    except:
                        return "Не вдалося отримати прогрес"
                
                # Періодично перевіряємо прогрес
                max_wait_time = 120  # максимальний час очікування у секундах
                wait_interval = 3    # інтервал перевірки
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    progress = get_progress()
                    print(f"Прогрес завантаження: {progress}")
                    
                    # Перевіряємо, чи зник елемент завантаження
                    try:
                        driver.find_element(By.XPATH, '//div[contains(@class, "loading-mbT0kx")]')
                        time.sleep(wait_interval)
                    except:
                        print("Завантаження завершено!")
                        break
                
                # Дополнительное ожидание стабилизации
                time.sleep(3)
                
            except Exception as e:
                print(f"Помилка при очікуванні завантаження: {e}")

            # ================== КРИТИЧЕСКИ ВАЖНО ==================
            # После завершения загрузки аватара ОБЯЗАТЕЛЬНО закрываем все модалки
            print("🔧 Начинаем обработку модальных окон после смены аватара...")
            
            # Пытаемся закрыть модалки несколько раз
            for attempt in range(3):
                print(f"Попытка {attempt + 1} закрыть модалки...")
                
                if handle_all_modals(driver, timeout=3):
                    print("✅ Модалка закрыта")
                else:
                    print("ℹ️ Модалки не найдены или уже закрыты")
                
                # Ждем исчезновения модалок
                wait_for_modals_to_disappear(driver, max_wait=5)
                
                # Проверяем, есть ли еще видимые модалки
                try:
                    visible_modal = driver.find_element(By.XPATH, '//div[contains(@class, "lv-modal-wrapper")][@style*="display: block"]')
                    print(f"⚠️ Обнаружена видимая модалка, попытка {attempt + 1}")
                    time.sleep(2)
                except:
                    print("✅ Все модалки закрыты")
                    break
            
            # Финальная проверка и принудительное закрытие если нужно
            try:
                # Ищем любые блокирующие элементы
                blocking_elements = driver.find_elements(By.XPATH, '//div[@tabindex="-1" and contains(@class, "modal")]')
                if blocking_elements:
                    print(f"🚨 Найдены блокирующие элементы: {len(blocking_elements)}")
                    # Пытаемся кликнуть вне модалки или нажать ESC
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(2)
            except:
                pass
            
            print("✅ Обработка модальных окон завершена")
            
        else:
            print("Аватари не знайдені!")
            return False
            
    except Exception as e:
        print(f"❌ Общая ошибка в choose_or_create_avatar: {e}")
        return False
    
    return True

# Дополнительная функция для вызова перед edit_script
def ensure_no_blocking_modals(driver):
    """
    Гарантированно убираем все блокирующие модалки перед важными операциями
    """
    print("🛡️ Финальная проверка на блокирующие модалки...")
    
    # Проверяем наличие блокирующих элементов
    blocking_selectors = [
        '//div[contains(@class, "lv-modal-wrapper")][@style*="display: block"]',
        '//div[@tabindex="-1" and contains(@class, "modal")]',
        '//div[contains(@class, "modal") and not(contains(@style, "display: none"))]'
    ]
    
    for selector in blocking_selectors:
        try:
            blocking_element = driver.find_element(By.XPATH, selector)
            print(f"🚨 Найден блокирующий элемент: {selector}")
            
            # Пытаемся закрыть разными способами
            try:
                # Ищем кнопку закрытия внутри
                close_btn = blocking_element.find_element(By.XPATH, './/button[contains(@class, "close") or .//span[text()="Cancel"] or .//span[text()="Close"]]')
                close_btn.click()
                print("✅ Закрыли через кнопку внутри модалки")
            except:
                # Кликаем вне модалки
                try:
                    driver.execute_script("arguments[0].style.display = 'none';", blocking_element)
                    print("✅ Скрыли модалку через JavaScript")
                except:
                    pass
            
            time.sleep(1)
        except:
            continue
    
    # Последняя попытка через ESC
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)
    except:
        pass
    
    print("✅ Проверка завершена")