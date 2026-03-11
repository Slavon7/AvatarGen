from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from concurrent.futures import ThreadPoolExecutor
import time
import traceback

from auth import login
from avatar import choose_or_create_avatar
from script_editor import edit_script
from export import export_video
from text_loader import get_all_text_ids
from config import load_config

def ensure_no_blocking_modals(driver):
    """
    Гарантированно убираем все блокирующие модалки перед важными операциями
    """
    print("🛡️ Финальная проверка на блокирующие модалки...")
    
    # Проверяем наличие блокирующих элементов
    blocking_selectors = [
        '//div[contains(@class, "lv-modal-wrapper")][@style*="display: block"]',
        '//div[@tabindex="-1" and contains(@class, "modal")]',
        '//div[contains(@class, "modal") and not(contains(@style, "display: none"))]',
        '//div[contains(@class, "pippit-modal")]'  # Добавляем специфичный селектор для Pippit
    ]
    
    modals_found = 0
    
    for selector in blocking_selectors:
        try:
            blocking_elements = driver.find_elements(By.XPATH, selector)
            if blocking_elements:
                modals_found += len(blocking_elements)
                print(f"🚨 Найдено блокирующих элементов: {len(blocking_elements)} по селектору: {selector}")
                
                for element in blocking_elements:
                    # Пытаемся закрыть разными способами
                    try:
                        # Ищем кнопку Cancel
                        cancel_btn = element.find_element(By.XPATH, './/button[.//span[text()="Cancel"]]')
                        cancel_btn.click()
                        print("✅ Закрыли через кнопку Cancel")
                        time.sleep(1)
                        continue
                    except:
                        pass
                    
                    try:
                        # Ищем кнопку Close
                        close_btn = element.find_element(By.XPATH, './/button[.//span[text()="Close"] or contains(@class, "close")]')
                        close_btn.click()
                        print("✅ Закрыли через кнопку Close")
                        time.sleep(1)
                        continue
                    except:
                        pass
                    
                    try:
                        # Скрываем через JavaScript
                        driver.execute_script("arguments[0].style.display = 'none';", element)
                        print("✅ Скрыли модалку через JavaScript")
                        time.sleep(1)
                    except:
                        pass
        except Exception as e:
            print(f"Ошибка при проверке селектора {selector}: {e}")
            continue
    
    # Если найдены модалки, пытаемся закрыть через ESC
    if modals_found > 0:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            print("✅ Попытались закрыть модалки через ESC")
            time.sleep(2)
        except:
            pass
        
        # Дополнительная попытка через клик вне модалки
        try:
            driver.execute_script("document.body.click();")
            time.sleep(1)
        except:
            pass
    
    print(f"✅ Проверка завершена. Найдено и обработано модалок: {modals_found}")
    return modals_found == 0

def safe_choose_avatar(driver):
    """
    Безопасный выбор аватара с обработкой всех модальных окон
    """
    try:
        print("🎭 Начинаем выбор аватара...")
        success = choose_or_create_avatar(driver)
        
        if success:
            print("✅ Аватар выбран успешно")
        else:
            print("⚠️ Возможны проблемы при выборе аватара")
        
        # Критически важно: убираем все модалки после выбора аватара
        print("🔧 Обработка модальных окон после выбора аватара...")
        
        # Делаем несколько попыток очистки
        for attempt in range(5):
            print(f"Попытка очистки #{attempt + 1}")
            
            if ensure_no_blocking_modals(driver):
                print("✅ Все модалки закрыты")
                break
            else:
                print(f"⚠️ Есть открытые модалки, повторяем попытку {attempt + 1}")
                time.sleep(2)
        
        # Финальная стабилизация
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при выборе аватара: {e}")
        traceback.print_exc()
        return False

def safe_edit_script(driver, text_id):
    """
    Безопасное редактирование скрипта с предварительной очисткой модалок
    """
    try:
        print(f"📝 Начинаем редактирование скрипта для {text_id}...")
        
        # Предварительная очистка модалок
        ensure_no_blocking_modals(driver)
        
        # Дополнительная пауза
        time.sleep(2)
        
        # Попытка редактирования
        edit_script(driver, text_id=text_id)
        print("✅ Скрипт отредактирован успешно")
        return True
        
    except Exception as e:
        if "click intercepted" in str(e).lower():
            print("🚨 Клик перехвачен модалкой! Выполняем экстренную очистку...")
            
            # Сохраняем скриншот для диагностики
            try:
                driver.save_screenshot(f"error_modal_intercept_{text_id}_{int(time.time())}.png")
                print("📸 Скриншот ошибки сохранен")
            except:
                pass
            
            # Экстренная очистка
            for attempt in range(3):
                print(f"Экстренная попытка #{attempt + 1}")
                ensure_no_blocking_modals(driver)
                time.sleep(3)
                
                try:
                    edit_script(driver, text_id=text_id)
                    print("✅ Скрипт отредактирован после экстренной очистки")
                    return True
                except Exception as retry_e:
                    if attempt == 2:  # Последняя попытка
                        print(f"❌ Не удалось отредактировать скрипт даже после экстренной очистки: {retry_e}")
                        raise
                    else:
                        print(f"⚠️ Попытка {attempt + 1} неудачна, повторяем...")
                        continue
        else:
            print(f"❌ Ошибка при редактировании скрипта: {e}")
            raise

def safe_export_video(driver, with_watermark, video_name):
    """
    Безопасный экспорт видео с обработкой модалок
    """
    try:
        print(f"🎬 Начинаем экспорт видео: {video_name}")
        
        # Очистка модалок перед экспортом
        ensure_no_blocking_modals(driver)
        time.sleep(1)
        
        export_video(driver, with_watermark=with_watermark, video_name=video_name)
        print("✅ Видео экспортировано успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте видео: {e}")
        traceback.print_exc()
        return False

def process_texts(text_ids_slice, repeat_count, base_url, with_watermark):
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    
    # Добавляем дополнительные опции для стабильности
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    
    successful_videos = 0
    total_videos = len(text_ids_slice) * repeat_count
    
    try:
        print(f"🚀 Запуск процесса для {len(text_ids_slice)} языков, {repeat_count} повторов")
        print(f"Всего видео к созданию: {total_videos}")
        
        driver.get(base_url)
        
        # Авторизация
        try:
            login(driver)
            print("✅ Авторизация прошла успешно")
        except Exception as e:
            print(f"❌ Ошибка авторизации: {e}")
            return

        for repeat_index in range(repeat_count):
            print(f"\n{'='*50}")
            print(f"ІТЕРАЦІЯ #{repeat_index + 1}/{repeat_count}")
            print(f"{'='*50}")
            
            for i, text_id in enumerate(text_ids_slice):
                print(f"\n{'-'*30}")
                print(f"Генерація відео {i+1}/{len(text_ids_slice)} для мови: {text_id}")
                print(f"Повтор: {repeat_index + 1}/{repeat_count}")
                print(f"Прогресс: {successful_videos}/{total_videos} видео создано")
                print(f"{'-'*30}")
                
                try:
                    # 1. Безопасный выбор аватара
                    if not safe_choose_avatar(driver):
                        print("❌ Пропускаем из-за ошибки выбора аватара")
                        continue
                    
                    # 2. Безопасное редактирование скрипта
                    if not safe_edit_script(driver, text_id):
                        print("❌ Пропускаем из-за ошибки редактирования скрипта")
                        continue
                    
                    # 3. Безопасный экспорт видео
                    video_name = f"{text_id}_v{repeat_index + 1}"
                    if safe_export_video(driver, with_watermark, video_name):
                        successful_videos += 1
                        print(f"✅ Видео {video_name} создано успешно!")
                    else:
                        print(f"❌ Ошибка создания видео {video_name}")
                    
                    # Пауза между видео для стабильности
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"❌ Критическая ошибка при обработке {text_id}: {e}")
                    traceback.print_exc()
                    
                    # Сохраняем состояние для диагностики
                    try:
                        driver.save_screenshot(f"critical_error_{text_id}_{int(time.time())}.png")
                    except:
                        pass
                    
                    continue
        
        print(f"\n🎉 ЗАВЕРШЕНО! Успешно создано: {successful_videos}/{total_videos} видео")
        
    except Exception as e:
        print(f"❌ Критическая ошибка процесса: {e}")
        traceback.print_exc()
    finally:
        try:
            driver.quit()
            print("✅ Браузер закрыт")
        except:
            print("⚠️ Ошибка при закрытии браузера")

def chunk_list(lst, n):
    """Разбить список lst на n примерно равных частей"""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

if __name__ == "__main__":
    print("🎬 Запуск генератора видео...")
    
    try:
        TEXT_IDS = get_all_text_ids()
        config = load_config()
        BASE_URL = config.get("BASE_URL", "https://pippit.capcut.com")
        WITH_WATERMARK = config.get("WITH_WATERMARK", True)
        REPEAT_COUNT = config.get("REPEAT_COUNT", 1)

        n_threads = int(config.get("THREADS", 1))
        if n_threads < 1:
            n_threads = 1

        print(f"📋 Настройки:")
        print(f"   - Языков: {len(TEXT_IDS)}")
        print(f"   - Повторов: {REPEAT_COUNT}")
        print(f"   - Потоков: {n_threads}")
        print(f"   - URL: {BASE_URL}")
        print(f"   - С водяным знаком: {WITH_WATERMARK}")
        print(f"   - Всего видео к созданию: {len(TEXT_IDS) * REPEAT_COUNT * n_threads}")

        chunks = chunk_list(TEXT_IDS, n_threads)

        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                print(f"🚀 Запуск потока {i+1} с языками: {chunk}")
                futures.append(executor.submit(process_texts, chunk, REPEAT_COUNT, BASE_URL, WITH_WATERMARK))
            
            # Ждем завершения всех потоков
            for i, future in enumerate(futures):
                try:
                    future.result()
                    print(f"✅ Поток {i+1} завершен успешно")
                except Exception as e:
                    print(f"❌ Поток {i+1} завершен с ошибкой: {e}")

        print("🎉 ВСЕ ПОТОКИ ЗАВЕРШЕНЫ!")
        
    except Exception as e:
        print(f"❌ Критическая ошибка запуска: {e}")
        traceback.print_exc()