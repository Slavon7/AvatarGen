from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from text_loader import load_script_text
from config import load_config
from utils import handle_pippit_modal
import time
import random
import traceback

config = load_config()
ENABLE_SUBTITLES = config.get("ENABLE_SUBTITLES", True)

def edit_script(driver, text_id=None):
    wait = WebDriverWait(driver, 20)

    # Відкриття вкладки "Edit script"
    edit_script_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "lv-tabs-header-title")]//div[contains(text(), "Edit script")]'))
    )
    edit_script_btn.click()

    if not ENABLE_SUBTITLES:
        print("Субтитри вимкнено в конфігурації. Вимикаємо тумблер і пропускаємо редагування тексту.")
        try:
            toggle = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@role="switch"]'))
            )
            if toggle.get_attribute("aria-checked") == "true":
                toggle.click()
                print("Субтитри вимкнено")
            else:
                print("Субтитри вже вимкнено")
        except Exception as e:
            print(f"Не вдалося вимкнути субтитри: {e}")
        return

    # Вибір стилю субтитрів
    try:
        time.sleep(3)
        subtitle_styles = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//div[contains(@class, "item-wrapper-cdf_Hd")]')
            )
        )
        print(f"Знайдено стилів субтитрів: {len(subtitle_styles)}")
        if subtitle_styles:
            random_style = random.choice(subtitle_styles)
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", random_style)
            time.sleep(1)
            try:
                random_style.click()
                print("Стиль субтитрів обрано (клік)")
            except:
                driver.execute_script("arguments[0].click();", random_style)
                print("Стиль субтитрів обрано через JavaScript")
            time.sleep(2)
    except Exception as e:
        print(f"Помилка при виборі стилю субтитрів: {e}")

    # Заміна тексту скрипту
    try:
        edit_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "edit-btn-GoT4yt")]')))
        edit_button.click()
        print("Кнопка Edit натиснута")
        time.sleep(5)  # Увеличиваем время ожидания

        # ИСПРАВЛЕННЫЙ СЕЛЕКТОР - ищем contenteditable div
        script_editor_selectors = [
            '//div[@contenteditable="true" and contains(@class, "tiptap")]',
            '//div[@contenteditable="true" and contains(@class, "editor-core")]',
            '//div[@contenteditable="true" and contains(@class, "ProseMirror")]',
            '//div[@contenteditable="true"]'
        ]
        
        script_editor = None
        for selector in script_editor_selectors:
            try:
                print(f"Пробуем селектор: {selector}")
                script_editor = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                print(f"✅ Найден редактор с селектором: {selector}")
                break
            except Exception as e:
                print(f"Селектор {selector} не сработал: {e}")
                continue
        
        if script_editor is None:
            print("❌ Редактор не найден. Выводим отладочную информацию:")
            # Ищем все contenteditable элементы
            contenteditable_elements = driver.find_elements(By.XPATH, '//div[@contenteditable="true"]')
            print(f"Найдено contenteditable элементов: {len(contenteditable_elements)}")
            
            for i, elem in enumerate(contenteditable_elements):
                try:
                    class_attr = elem.get_attribute('class')
                    text_content = elem.text[:50] + "..." if len(elem.text) > 50 else elem.text
                    print(f"Element {i}: class='{class_attr}', text='{text_content}'")
                except:
                    print(f"Element {i}: не удалось получить атрибуты")
            
            # Сохраняем HTML для анализа
            with open("debug_editor.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("HTML сохранен в debug_editor.html")
            return
        
        # Очистка и ввод текста в contenteditable div
        try:
            # Прокручиваем к элементу
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", script_editor)
            time.sleep(1)
            
            # Кликаем для активации фокуса
            script_editor.click()
            time.sleep(1)
            
            # Очищаем содержимое через JavaScript (более надежно для contenteditable)
            driver.execute_script("arguments[0].innerHTML = '';", script_editor)
            time.sleep(1)
            
            # Альтернативная очистка через клавиши
            script_editor.send_keys(Keys.CONTROL + "a")
            script_editor.send_keys(Keys.DELETE)
            time.sleep(1)
            
            # Загружаем текст
            script_text, _ = load_script_text(text_id=text_id)
            print(f"Загружен текст длиной: {len(script_text)} символов")
            
            # Вставляем текст
            # Для contenteditable лучше использовать JavaScript
            escaped_text = script_text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            driver.execute_script(f"arguments[0].innerText = '{escaped_text}';", script_editor)
            
            # Альтернативный способ через send_keys (если JS не работает)
            # script_editor.send_keys(script_text)
            
            print(f"Текст скрипту замінено для мови: {text_id}")
            
            # Проверяем, что текст действительно введен
            current_text = script_editor.get_attribute("innerText") or script_editor.get_attribute("textContent")
            print(f"Длина введенного текста: {len(current_text) if current_text else 0}")
            
            # Создаем событие input для уведомления системы об изменении
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', {
                    bubbles: true,
                    cancelable: true,
                }));
            """, script_editor)
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Ошибка при вводе текста: {e}")
            traceback.print_exc()
            return

        # Кнопка Save
        try:
            save_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save-btn-tCRoYv")]'))
            )
            save_button.click()
            print("Кнопка Save натиснута")

            # Очікування індикатора завантаження
            try:
                print("Чекаємо на появу індикатора завантаження...")
                loading_indicator = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "loading-wP3Q9T")]'))
                )
                print("Индикатор загрузки появился, ожидаем его исчезновения...")
                WebDriverWait(driver, 60).until(
                    EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "loading-wP3Q9T")]'))
                )
                print("Індикатор зник. Збережено.")
                
                # Дополнительная проверка на класс is-rewriting
                try:
                    WebDriverWait(driver, 10).until_not(
                        EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "is-rewriting")]'))
                    )
                    print("Процесс перезаписи завершен")
                except:
                    print("Таймаут ожидания завершения перезаписи (это нормально)")
                
                time.sleep(2)
            except Exception as e:
                print(f"Проблема с індикатором: {e}")

            # Чекаємо і натискаємо Cancel, якщо з'явилось вікно "Install Pippit app?"
            handle_pippit_modal(driver)

        except Exception as e:
            print(f"Основная кнопка Save не найдена: {e}")
            try:
                save_button_alt = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//button[.//span[text()="Save"]]'))
                )
                save_button_alt.click()
                print("Альтернативная кнопка Save натиснута")
            except Exception as e2:
                print(f"Альтернативная кнопка Save не найдена: {e2}")
                
    except Exception as e:
        print(f"Помилка при заміні тексту скрипту: {e}")
        traceback.print_exc()

    # Повернення на вкладку "Choose avatar"
    try:
        choose_avatar_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//div[@class="lv-tabs-header-title"]//div[contains(text(), "Choose avatar")]')
            )
        )
        choose_avatar_tab.click()
        print("✅ Повернулись на вкладку 'Choose avatar'")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Не вдалося повернутись на вкладку 'Choose avatar': {e}")

        # Якщо причина — перекриття елементом, пробуємо закрити модалку і повторити клік
        if "click intercepted" in str(e):
            print("🔁 Можливо, модалка 'Install Pippit app?' заважає кліку. Пробуємо закрити її.")
            handle_pippit_modal(driver)

            # Повторна спроба натиснути на вкладку
            try:
                choose_avatar_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//div[@class="lv-tabs-header-title"]//div[contains(text(), "Choose avatar")]')
                    )
                )
                choose_avatar_tab.click()
                print("✅ Повторна спроба вдалася — перейшли на вкладку 'Choose avatar'")
                time.sleep(2)
            except Exception as retry_e:
                print(f"❌ Повторна спроба також не вдалася: {retry_e}")