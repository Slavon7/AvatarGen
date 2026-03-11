import cv2
import numpy as np
import os
import subprocess
import shutil
from pathlib import Path
import argparse
from multiprocessing import Pool, cpu_count, Queue, Process
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue as ThreadQueue
import time
import glob

class FaceCircleVideoProcessor:
    def __init__(self):
        # Завантаження каскаду Haar для детекції обличчя
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        if self.face_cascade.empty():
            print("Попередження: основний каскад не завантажився, пробуємо альтернативний...")
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
    
    def get_video_files(self, input_path):
        """Отримує список всіх відеофайлів з папки або повертає один файл"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        
        input_path = Path(input_path)
        
        if input_path.is_file():
            if input_path.suffix.lower() in video_extensions:
                return [str(input_path)]
            else:
                print(f"Файл {input_path} не є відеофайлом")
                return []
        
        elif input_path.is_dir():
            video_files = []
            for ext in video_extensions:
                pattern = str(input_path / f"*{ext}")
                video_files.extend(glob.glob(pattern))
                pattern = str(input_path / f"*{ext.upper()}")
                video_files.extend(glob.glob(pattern))
            
            video_files = list(set(video_files))
            video_files.sort()
            
            print(f"Знайдено {len(video_files)} відеофайлів в папці {input_path}")
            return video_files
        
        else:
            print(f"Шлях {input_path} не існує")
            return []
    
    def create_output_path(self, input_file, output_dir, mode, effect_type=""):
        """Створює шлях для вихідного файлу"""
        input_path = Path(input_file)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if mode == 'video':
            suffix = f"_circular_{effect_type}" if effect_type else "_circular"
            output_file = output_dir / f"{input_path.stem}{suffix}.mp4"
        elif mode == 'overlay':
            output_file = output_dir / f"{input_path.stem}_overlay.mp4"
        else:
            output_file = output_dir / f"{input_path.stem}_avatars"
        
        return str(output_file)
    
    def detect_faces(self, frame):
        """Детекція обличчя"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        return faces
    
    def calculate_fixed_circle_params(self, input_path, sample_frames=30, padding=0.5):
        """Аналізує перші кадри відео для визначення фіксованих параметрів кола"""
        cap = cv2.VideoCapture(input_path)
        
        if not cap.isOpened():
            return None
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        all_faces = []
        frame_count = 0
        
        print(f"  Аналіз відео для визначення фіксованої позиції кола...")
        
        while frame_count < sample_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            faces = self.detect_faces(frame)
            if len(faces) > 0:
                largest_face = max(faces, key=lambda face: face[2] * face[3])
                all_faces.append(largest_face)
            
            frame_count += 1
        
        cap.release()
        
        if not all_faces:
            print("  ❌ Обличчя не знайдено в аналізованих кадрах")
            return None
        
        # Розрахунок середніх значень
        avg_x = sum(face[0] + face[2]//2 for face in all_faces) // len(all_faces)
        avg_y = sum(face[1] + face[3]//2 for face in all_faces) // len(all_faces)
        avg_size = sum(max(face[2], face[3]) for face in all_faces) // len(all_faces)
        
        # Розрахунок радіусу з padding
        radius = int(avg_size * (1 + padding) / 2)
        
        # Обмеження радіусу розмірами кадру
        max_radius_x = min(avg_x, width - avg_x)
        max_radius_y = min(avg_y, height - avg_y)
        max_radius = min(max_radius_x, max_radius_y)
        
        if radius > max_radius:
            radius = max_radius
            print(f"  Радіус зменшено до {radius} щоб не виходити за межі відео")
        
        print(f"  ✅ Фіксовані параметри кола: центр ({avg_x}, {avg_y}), радіус {radius}")
        
        return (avg_x, avg_y, radius)
    
    def apply_fixed_circular_effect(self, frame, center_x, center_y, radius, effect_type="crop", background_color=(0, 0, 0)):
        """Застосовує круговий ефект з фіксованими параметрами"""
        h, w = frame.shape[:2]
        
        # Створення маски
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), radius, 255, -1)
        
        result = frame.copy()
        
        if effect_type == "crop":
            result[mask == 0] = background_color
        elif effect_type == "blur":
            blurred = cv2.GaussianBlur(frame, (51, 51), 0)
            result = np.where(mask[..., np.newaxis] == 255, frame, blurred)
        elif effect_type == "darken":
            darkened = (frame * 0.3).astype(np.uint8)
            result = np.where(mask[..., np.newaxis] == 255, frame, darkened)
        
        return result
    
    def create_circular_mask_with_overlay(self, foreground_frame, background_frame, 
                                        center_x, center_y, radius, 
                                        overlay_position="center", overlay_size=None,
                                        feather_edges=False, feather_radius=10):
        """Створює композицію з круглого переднього плану та фонового відео"""
        fg_h, fg_w = foreground_frame.shape[:2]
        bg_h, bg_w = background_frame.shape[:2]
        
        # Створюємо маску для вирізання кола з переднього плану
        fg_mask = np.zeros((fg_h, fg_w), dtype=np.uint8)
        cv2.circle(fg_mask, (center_x, center_y), radius, 255, -1)
        
        # Застосовуємо розмиття до країв маски для м'якості
        if feather_edges:
            fg_mask = cv2.GaussianBlur(fg_mask, (feather_radius*2+1, feather_radius*2+1), 0)
        
        # Вирізаємо круглу область з переднього плану
        circular_region = np.zeros_like(foreground_frame)
        circular_region[fg_mask > 0] = foreground_frame[fg_mask > 0]
        
        # Вирізаємо квадратну область навколо кола
        crop_x1 = max(0, center_x - radius)
        crop_y1 = max(0, center_y - radius)
        crop_x2 = min(fg_w, center_x + radius)
        crop_y2 = min(fg_h, center_y + radius)
        
        cropped_circular = circular_region[crop_y1:crop_y2, crop_x1:crop_x2]
        cropped_mask = fg_mask[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Масштабуємо фоновий кадр до потрібного розміру
        if (bg_w, bg_h) != (fg_w, fg_h):
            background_resized = cv2.resize(background_frame, (fg_w, fg_h))
        else:
            background_resized = background_frame.copy()
        
        # Визначаємо позицію накладання на фоні
        if overlay_position == "center":
            overlay_x = (fg_w - (crop_x2 - crop_x1)) // 2
            overlay_y = (fg_h - (crop_y2 - crop_y1)) // 2
        elif overlay_position == "top-left":
            overlay_x = 50
            overlay_y = 50
        elif overlay_position == "top-right":
            overlay_x = fg_w - (crop_x2 - crop_x1) - 50
            overlay_y = 50
        elif overlay_position == "bottom-left":
            overlay_x = 50
            overlay_y = fg_h - (crop_y2 - crop_y1) - 50
        elif overlay_position == "bottom-right":
            overlay_x = fg_w - (crop_x2 - crop_x1) - 50
            overlay_y = fg_h - (crop_y2 - crop_y1) - 50
        else:
            overlay_x = (fg_w - (crop_x2 - crop_x1)) // 2
            overlay_y = (fg_h - (crop_y2 - crop_y1)) // 2
        
        # Масштабуємо вирізану область якщо потрібно
        if overlay_size is not None:
            new_size = (overlay_size, overlay_size)
            cropped_circular = cv2.resize(cropped_circular, new_size)
            cropped_mask = cv2.resize(cropped_mask, new_size)
        
        # Перевіряємо межі накладання
        overlay_h, overlay_w = cropped_circular.shape[:2]
        end_x = min(fg_w, overlay_x + overlay_w)
        end_y = min(fg_h, overlay_y + overlay_h)
        
        if overlay_x < 0:
            cropped_circular = cropped_circular[:, -overlay_x:]
            cropped_mask = cropped_mask[:, -overlay_x:]
            overlay_x = 0
        
        if overlay_y < 0:
            cropped_circular = cropped_circular[-overlay_y:, :]
            cropped_mask = cropped_mask[-overlay_y:, :]
            overlay_y = 0
        
        # Коригуємо розміри якщо вони виходять за межі
        actual_w = end_x - overlay_x
        actual_h = end_y - overlay_y
        
        if actual_w != overlay_w or actual_h != overlay_h:
            cropped_circular = cropped_circular[:actual_h, :actual_w]
            cropped_mask = cropped_mask[:actual_h, :actual_w]
        
        # Накладаємо круглу область на фон
        result = background_resized.copy()
        
        if cropped_mask.size > 0 and cropped_circular.size > 0:
            # Нормалізуємо маску для змішування
            mask_normalized = cropped_mask.astype(np.float32) / 255.0
            
            # Область фону для змішування
            bg_region = result[overlay_y:overlay_y + actual_h, overlay_x:overlay_x + actual_w]
            
            # Змішування з альфа-каналом
            for c in range(3):
                bg_region[:, :, c] = (
                    bg_region[:, :, c].astype(np.float32) * (1 - mask_normalized) +
                    cropped_circular[:, :, c].astype(np.float32) * mask_normalized
                ).astype(np.uint8)
            
            result[overlay_y:overlay_y + actual_h, overlay_x:overlay_x + actual_w] = bg_region
        
        return result
    
    def process_overlay_video(self, foreground_path, background_path, output_path,
                            padding=0.5, overlay_position="center", overlay_size=None,
                            feather_edges=True, keep_audio=True):
        """Створює відео з накладанням круглого вирізу на фон"""
        video_name = Path(foreground_path).name
        print(f"  🎬 Створення накладання для {video_name}")
        
        # Аналізуємо передній план для визначення параметрів кола
        circle_params = self.calculate_fixed_circle_params(foreground_path, padding=padding)
        
        if circle_params is None:
            print(f"  ❌ Не вдалося визначити параметри кола для {video_name}")
            return False
        
        center_x, center_y, radius = circle_params
        
        # Відкриваємо відео
        fg_cap = cv2.VideoCapture(foreground_path)
        bg_cap = cv2.VideoCapture(background_path)
        
        if not fg_cap.isOpened() or not bg_cap.isOpened():
            print(f"  ❌ Помилка відкриття відео")
            return False
        
        # Отримуємо параметри
        fps = int(fg_cap.get(cv2.CAP_PROP_FPS))
        width = int(fg_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(fg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(fg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"    📊 Обробка {total_frames} кадрів...")
        
        # Створення вихідного відео
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_output = output_path.replace('.mp4', '_temp_no_audio.mp4')
        out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
        
        frame_count = 0
        bg_total_frames = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while frame_count < total_frames:
            # Читаємо кадр переднього плану
            fg_ret, fg_frame = fg_cap.read()
            if not fg_ret:
                break
            
            # Читаємо кадр фону (з зациклюванням)
            bg_ret, bg_frame = bg_cap.read()
            if not bg_ret:
                bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                bg_ret, bg_frame = bg_cap.read()
            
            if bg_ret:
                # Створюємо композитний кадр
                composite_frame = self.create_circular_mask_with_overlay(
                    fg_frame, bg_frame, center_x, center_y, radius,
                    overlay_position, overlay_size, feather_edges
                )
                
                out.write(composite_frame)
            
            frame_count += 1
            
            # Показ прогресу
            if frame_count % 60 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"      📹 Прогрес: {progress:.1f}% ({frame_count}/{total_frames})")
        
        # Закриваємо відео
        fg_cap.release()
        bg_cap.release()
        out.release()
        
        print(f"    ✅ Обробка завершена!")
        
        # Додаємо звук
        if keep_audio:
            print(f"    🔊 Додавання звуку...")
            audio_success = self.merge_audio_with_video(temp_output, foreground_path, output_path)
            
            if audio_success:
                print(f"    ✅ Готово зі звуком: {Path(output_path).name}")
            else:
                try:
                    os.rename(temp_output, output_path)
                    print(f"    📹 Готово без звуку: {Path(output_path).name}")
                except:
                    print(f"    📹 Збережено як: {Path(temp_output).name}")
        else:
            try:
                os.rename(temp_output, output_path)
                print(f"    📹 Готово без звуку: {Path(output_path).name}")
            except:
                print(f"    📹 Збережено як: {Path(temp_output).name}")
        
        return True
    
    def process_video_simple(self, input_path, output_path, effect_type="crop", 
                           background_color=(0, 0, 0), padding=0.5, keep_audio=True):
        """Простая обработка видео (однопотокова версія)"""
        video_name = Path(input_path).name
        
        # Аналізуємо відео для визначення фіксованих параметрів
        circle_params = self.calculate_fixed_circle_params(input_path, padding=padding)
        
        if circle_params is None:
            print(f"  ❌ Не вдалося визначити параметри кола для {video_name}")
            return False
        
        center_x, center_y, radius = circle_params
        
        # Відкриваємо відео
        cap = cv2.VideoCapture(input_path)
        
        if not cap.isOpened():
            print(f"  ❌ Помилка: не вдалося відкрити відео {input_path}")
            return False
        
        # Отримання параметрів вхідного відео
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"  📊 Параметри: {width}x{height}, {fps} FPS, {total_frames} кадрів")
        
        # Створення об'єкта для запису відео
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_output = output_path.replace('.mp4', '_temp_no_audio.mp4')
        out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Обробляємо кадр
            processed_frame = self.apply_fixed_circular_effect(
                frame, center_x, center_y, radius, effect_type, background_color
            )
            
            out.write(processed_frame)
            frame_count += 1
            
            # Показ прогресу
            if frame_count % 60 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"    📹 {video_name}: {progress:.1f}% ({frame_count}/{total_frames})")
        
        cap.release()
        out.release()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"  ⚡ Обробка завершена за {processing_time:.2f}с")
        
        # Додаємо звук
        if keep_audio:
            print(f"  🔊 Додавання звуку...")
            audio_success = self.merge_audio_with_video(temp_output, input_path, output_path)
            
            if audio_success:
                print(f"  ✅ Готово зі звуком: {Path(output_path).name}")
            else:
                try:
                    os.rename(temp_output, output_path)
                    print(f"  📹 Готово без звуку: {Path(output_path).name}")
                except:
                    print(f"  📹 Збережено як: {Path(temp_output).name}")
        else:
            try:
                os.rename(temp_output, output_path)
                print(f"  📹 Готово без звуку: {Path(output_path).name}")
            except:
                print(f"  📹 Збережено як: {Path(temp_output).name}")
        
        return True
    
    def extract_circular_avatars(self, input_path, output_dir, output_size=(512, 512), interval=30):
        """Витягує кругові аватари з відео"""
        video_name = Path(input_path).name
        print(f"  🎭 Витягування аватарів з {video_name}...")
        
        cap = cv2.VideoCapture(input_path)
        
        if not cap.isOpened():
            print(f"  ❌ Помилка: не вдалося відкрити відео {input_path}")
            return
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Зберігаємо тільки кожен interval-й кадр
            if frame_count % interval != 0:
                continue
            
            faces = self.detect_faces(frame)
            
            if len(faces) > 0:
                largest_face = max(faces, key=lambda face: face[2] * face[3])
                x, y, w, h = largest_face
                
                # Створення кругового аватара
                h_frame, w_frame = frame.shape[:2]
                center_x = x + w // 2
                center_y = y + h // 2
                radius = int(max(w, h) * 1.3 / 2)
                
                mask = np.zeros((h_frame, w_frame), dtype=np.uint8)
                cv2.circle(mask, (center_x, center_y), radius, 255, -1)
                
                # Вирізання квадратної області
                top_left_x = max(0, center_x - radius)
                top_left_y = max(0, center_y - radius)
                bottom_right_x = min(w_frame, center_x + radius)
                bottom_right_y = min(h_frame, center_y + radius)
                
                face_region = frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
                mask_region = mask[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
                
                if face_region.size > 0:
                    # Зміна розміру
                    face_resized = cv2.resize(face_region, output_size)
                    mask_resized = cv2.resize(mask_region, output_size)
                    
                    # Створення RGBA
                    result = np.zeros((output_size[1], output_size[0], 4), dtype=np.uint8)
                    result[:, :, :3] = face_resized
                    result[:, :, 3] = mask_resized
                    
                    # Збереження
                    output_filename = f"avatar_{frame_count:06d}.png"
                    output_path_full = os.path.join(output_dir, output_filename)
                    cv2.imwrite(output_path_full, result)
                    saved_count += 1
                    
                    if saved_count % 10 == 0:
                        print(f"    📸 Збережено {saved_count} аватарів...")
        
        cap.release()
        print(f"  ✅ Збережено {saved_count} аватарів в {output_dir}")
    
    def merge_audio_with_video(self, video_path, original_video_path, output_path):
        """Об'єднує оброблене відео з аудіо з оригінального відео"""
        if not shutil.which('ffmpeg'):
            return False
        
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', original_video_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    os.remove(video_path)
                except:
                    pass
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def process_multiple_videos(self, input_path, output_dir, mode="video", effect_type="crop",
                              background_color=(0, 0, 0), padding=0.5, keep_audio=True,
                              avatar_size=(512, 512), avatar_interval=30):
        """Обробляє декілька відео з папки або один файл"""
        video_files = self.get_video_files(input_path)
        
        if not video_files:
            print("❌ Відеофайли не знайдено!")
            return
        
        print(f"\n🎬 Початок обробки {len(video_files)} відео(файлів)")
        print(f"📁 Вихідна папка: {output_dir}")
        print(f"⚙️  Режим: {mode}")
        if mode == "video":
            print(f"🎨 Ефект: {effect_type}")
        print("=" * 60)
        
        successful = 0
        failed = 0
        total_start_time = time.time()
        
        for i, video_file in enumerate(video_files, 1):
            print(f"\n📹 [{i}/{len(video_files)}] {Path(video_file).name}")
            
            try:
                # Створюємо шлях для вихідного файлу
                output_path = self.create_output_path(video_file, output_dir, mode, effect_type)
                
                # Перевіряємо, чи не існує вже вихідний файл
                if Path(output_path).exists():
                    print(f"  ⏭️  Файл вже існує, пропускаємо: {Path(output_path).name}")
                    continue
                
                if mode == "video":
                    success = self.process_video_simple(
                        video_file, output_path, effect_type, 
                        background_color, padding, keep_audio
                    )
                else:  # avatars
                    self.extract_circular_avatars(
                        video_file, output_path, avatar_size, avatar_interval
                    )
                    success = True
                
                if success:
                    successful += 1
                    print(f"  ✅ Успішно оброблено!")
                else:
                    failed += 1
                    print(f"  ❌ Помилка обробки!")
                    
            except Exception as e:
                failed += 1
                print(f"  ❌ Критична помилка: {e}")
        
        # Підсумки
        total_time = time.time() - total_start_time
        print("\n" + "=" * 60)
        print(f"🏁 ЗАВЕРШЕНО!")
        print(f"✅ Успішно оброблено: {successful}")
        print(f"❌ Помилок: {failed}")
        print(f"⏱️  Загальний час: {total_time:.2f} секунд")
        print(f"📁 Результати збережено в: {output_dir}")
    
    def process_multiple_overlays(self, foreground_path, background_path, output_dir,
                                padding=0.5, overlay_position="center", overlay_size=None,
                                feather_edges=True, keep_audio=True):
        """Обробляє декілька відео з накладанням фону"""
        foreground_files = self.get_video_files(foreground_path)
        
        if not foreground_files:
            print("❌ Відеофайли переднього плану не знайдено!")
            return
        
        if not os.path.exists(background_path):
            print(f"❌ Фоновий файл не знайдено: {background_path}")
            return
        
        print(f"\n🎬 Початок створення накладань для {len(foreground_files)} відео")
        print(f"📁 Вихідна папка: {output_dir}")
        print(f"🖼️  Фоновий файл: {Path(background_path).name}")
        print(f"📍 Позиція: {overlay_position}")
        if overlay_size:
            print(f"📏 Розмір кола: {overlay_size}px")
        print("=" * 60)
        
        # Створюємо вихідну папку
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        successful = 0
        failed = 0
        total_start_time = time.time()
        
        for i, fg_file in enumerate(foreground_files, 1):
            print(f"\n📹 [{i}/{len(foreground_files)}] {Path(fg_file).name}")
            
            try:
                # Створюємо ім'я вихідного файлу
                output_path = self.create_output_path(fg_file, output_dir, "overlay")
                
                # Перевіряємо, чи не існує вже файл
                if Path(output_path).exists():
                    print(f"  ⏭️  Файл вже існує, пропускаємо: {Path(output_path).name}")
                    continue
                
                # Обробляємо відео
                success = self.process_overlay_video(
                    fg_file, background_path, output_path,
                    padding, overlay_position, overlay_size,
                    feather_edges, keep_audio
                )
                
                if success:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                print(f"  ❌ Критична помилка: {e}")
        
        # Підсумки
        total_time = time.time() - total_start_time
        print("\n" + "=" * 60)
        print(f"🏁 ЗАВЕРШЕНО!")
        print(f"✅ Успішно створено накладань: {successful}")
        print(f"❌ Помилок: {failed}")
        print(f"⏱️  Загальний час: {total_time:.2f} секунд")
        print(f"📁 Результати збережено в: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='Пакетна обробка відео з круговими ефектами для обличчя')
    
    # Основные аргументы
    parser.add_argument('input', help='Шлях до вхідного відео або папки з відео')
    parser.add_argument('background', nargs='?', help='Шлях до фонового відео (для overlay режиму)')
    parser.add_argument('-o', '--output', required=True, help='Папка для збереження результатів')
    
    # Режимы работы
    parser.add_argument('--mode', choices=['video', 'avatars', 'overlay'], default='video',
                       help='Режим: video (створити відео), avatars (витягти аватари), або overlay (накладання на фон)')
    
    # Настройки эффектов
    parser.add_argument('--effect', choices=['crop', 'blur', 'darken'], default='crop',
                       help='Ефект для відео: crop (чорний фон), blur (розмиття), darken (затемнення)')
    parser.add_argument('--bg-color', type=int, nargs=3, default=[0, 0, 0],
                       help='Колір фону для crop ефекту (B G R), за замовчуванням: 0 0 0 (чорний)')
    
    # Настройки overlay
    parser.add_argument('--position', choices=['center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'], 
                       default='center', help='Позиція накладання кола (для overlay режиму)')
    parser.add_argument('--size', type=int, help='Розмір кола на фоні в пікселях (для overlay режиму)')
    parser.add_argument('--no-feather', action='store_true', help='Відключити м\'які краї (для overlay режиму)')
    
    # Настройки аватаров
    parser.add_argument('--avatar-size', type=int, nargs=2, default=[512, 512],
                       help='Розмір аватарів (тільки для режиму avatars)')
    parser.add_argument('--avatar-interval', type=int, default=30,
                       help='Інтервал між кадрами для аватарів (кожен N-й кадр)')
    
    # Общие настройки
    parser.add_argument('--padding', type=float, default=0.5,
                       help='Збільшення кола (0.5 = 50% збільшення), за замовчуванням: 0.5')
    parser.add_argument('--no-audio', action='store_true',
                       help='Не додавати звук до вихідного відео')
    parser.add_argument('--threads', type=int, default=None,
                       help='Кількість потоків для обробки (поки не реалізовано)')
    parser.add_argument('--single-thread', action='store_true',
                       help='Використовувати однопотокову обробку (за замовчуванням)')
    
    args = parser.parse_args()
    
    # Проверяем аргументы
    if args.mode == 'overlay':
        if not args.background:
            print("❌ Помилка: для overlay режиму потрібно вказати фоновий файл!")
            print("Використання: python script.py input_video background_video -o output_folder --mode overlay")
            return
        
        if not os.path.exists(args.background):
            print(f"❌ Помилка: фоновий файл не існує: {args.background}")
            return
    
    # Перевіряємо вхідний шлях
    if not os.path.exists(args.input):
        print(f"❌ Помилка: шлях {args.input} не існує!")
        return
    
    # Створюємо вихідну папку якщо не існує
    Path(args.output).mkdir(parents=True, exist_ok=True)
    
    processor = FaceCircleVideoProcessor()
    
    if args.mode == 'overlay':
        # Режим overlay
        processor.process_multiple_overlays(
            foreground_path=args.input,
            background_path=args.background,
            output_dir=args.output,
            padding=args.padding,
            overlay_position=args.position,
            overlay_size=args.size,
            feather_edges=not args.no_feather,
            keep_audio=not args.no_audio
        )
    else:
        # Запуск пакетной обработки для video и avatars режимов
        processor.process_multiple_videos(
            input_path=args.input,
            output_dir=args.output,
            mode=args.mode,
            effect_type=args.effect,
            background_color=tuple(args.bg_color),
            padding=args.padding,
            keep_audio=not args.no_audio,
            avatar_size=tuple(args.avatar_size),
            avatar_interval=args.avatar_interval
        )

if __name__ == "__main__":
    main()