import customtkinter as ctk
import subprocess
import json
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import os
import threading
from pathlib import Path

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)

class ConfigEditor(ctk.CTk):

    def run_main_script(self):
        try:
            subprocess.Popen(["python", "main.py"])
        except Exception as e:
            print("Ошибка при запуске main.py:", e)

    def __init__(self):
        super().__init__()
        self.title("CapCut Video Generator & Video Processor")
        self.geometry("600x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config = load_config()
        
        # Добавляем настройки для видеопроцессора, если их нет
        video_defaults = {
            "VIDEO_INPUT_PATH": "",
            "VIDEO_OUTPUT_PATH": "",
            "VIDEO_BACKGROUND_PATH": "",
            "VIDEO_MODE": "video",
            "VIDEO_EFFECT": "crop",
            "VIDEO_BG_COLOR_R": 0,
            "VIDEO_BG_COLOR_G": 0,
            "VIDEO_BG_COLOR_B": 0,
            "VIDEO_PADDING": 0.5,
            "VIDEO_THREADS": 4,
            "VIDEO_SINGLE_THREAD": False,
            "VIDEO_NO_AUDIO": False,
            "VIDEO_AVATAR_SIZE_W": 512,
            "VIDEO_AVATAR_SIZE_H": 512,
            "VIDEO_AVATAR_INTERVAL": 30,
            "VIDEO_OVERLAY_POSITION": "center",
            "VIDEO_OVERLAY_SIZE": 300,
            "VIDEO_FEATHER_EDGES": True
        }
        
        for key, value in video_defaults.items():
            if key not in self.config:
                self.config[key] = value

        # Главное меню с кнопками переключения
        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.pack(fill="x", pady=10)

        ctk.CTkButton(self.nav_frame, text="Main", command=self.show_main).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(self.nav_frame, text="Video Processor", command=self.show_video).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(self.nav_frame, text="Settings", command=self.show_settings).pack(side="left", padx=10, pady=10)

        # Три фрейма
        self.main_frame = ctk.CTkFrame(self)
        self.video_frame = ctk.CTkScrollableFrame(self)  # Скроллируемый фрейм для видео настроек
        self.settings_frame = ctk.CTkFrame(self)

        self.create_main_frame()
        self.create_video_frame()
        self.create_settings_frame()

        self.show_main()  # Показываем главный экран по умолчанию
        
        # Процессы для отслеживания
        self.process = None
        self.video_process = None

    def create_main_frame(self):
        # Поля
        self.email_entry = self.create_labeled_entry(self.main_frame, "Email:", self.config.get("EMAIL", ""), 0)
        self.password_entry = self.create_labeled_entry(self.main_frame, "Password:", self.config.get("PASSWORD", ""), 1)
        self.baseurl_entry = self.create_labeled_entry(self.main_frame, "Base URL:", self.config.get("BASE_URL", ""), 2)
        self.repeat_entry = self.create_labeled_entry(self.main_frame, "Repeat Count:", str(self.config.get("REPEAT_COUNT", 1)), 3)
        self.threads_entry = self.create_labeled_entry(self.main_frame, "Threads:", str(self.config.get("THREADS", 1)), 4)

        # Switch
        self.subtitles_switch = self.create_labeled_switch(self.main_frame, "Enable Subtitles", self.config.get("ENABLE_SUBTITLES", True), 5)
        self.watermark_switch = self.create_labeled_switch(self.main_frame, "With Watermark", self.config.get("WITH_WATERMARK", True), 6)

        # Dropdown
        self.resolution_dropdown = self.create_labeled_dropdown(self.main_frame, "Resolution", ["360p", "480p", "720p", "1080p", "2k", "4k"], self.config.get("RESOLUTION", "1080p"), 7)
        self.quality_dropdown = self.create_labeled_dropdown(self.main_frame, "Quality", ["Recommended", "Better quality", "Faster export"], self.config.get("QUALITY", "Recommended"), 8)
        self.framerate_dropdown = self.create_labeled_dropdown(self.main_frame, "Framerate", ["24fps","25fps", "30fps", "50fps", "60fps"], self.config.get("FRAMERATE", "30fps"), 9)
        self.format_dropdown = self.create_labeled_dropdown(self.main_frame, "Format", ["MP4", "MOV"], self.config.get("FORMAT", "MP4"), 10)
        
        # Save
        ctk.CTkButton(self.main_frame, text="Save Config", command=self.save_main).grid(row=11, column=0, columnspan=2, pady=30)

        ctk.CTkButton(self.main_frame, text="Run Script", command=self.run_main_script).grid(row=12, column=0, padx=(10,10), pady=(10, 10))
        ctk.CTkButton(self.main_frame, text="Stop Script", command=self.stop_main_script).grid(row=12, column=1, padx=(10,10), pady=(10, 10))

    def create_video_frame(self):
        """Создание вкладки для обработки видео"""
        row = 0
        
        # Заголовок
        ctk.CTkLabel(self.video_frame, text="🎬 Video Face Circle Processor", 
                    font=ctk.CTkFont(size=20, weight="bold")).grid(row=row, column=0, columnspan=3, pady=20)
        row += 1
        
        # Секция путей к файлам
        ctk.CTkLabel(self.video_frame, text="📁 File Paths", 
                    font=ctk.CTkFont(size=16, weight="bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(20,10))
        row += 1
        
        # Путь к входному видео/папке
        self.video_input_entry = self.create_file_selector(
            self.video_frame, "Input Video/Folder:", self.config.get("VIDEO_INPUT_PATH", ""), 
            row, is_folder=True, file_types=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v")]
        )
        row += 1
        
        # Путь к выходной папке
        self.video_output_entry = self.create_file_selector(
            self.video_frame, "Output Folder:", self.config.get("VIDEO_OUTPUT_PATH", ""), 
            row, is_folder=True, select_folder=True
        )
        row += 1
        
        # Путь к фоновому видео (для overlay режима)
        self.video_background_entry = self.create_file_selector(
            self.video_frame, "Background Video (for overlay):", self.config.get("VIDEO_BACKGROUND_PATH", ""), 
            row, file_types=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v")]
        )
        row += 1
        
        # Секция основных настроек
        ctk.CTkLabel(self.video_frame, text="⚙️ Main Settings", 
                    font=ctk.CTkFont(size=16, weight="bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(20,10))
        row += 1
        
        # Режим работы
        self.video_mode_dropdown = self.create_labeled_dropdown(
            self.video_frame, "Mode:", ["video", "avatars", "overlay"], 
            self.config.get("VIDEO_MODE", "video"), row
        )
        row += 1
        
        # Эффект (для video режима)
        self.video_effect_dropdown = self.create_labeled_dropdown(
            self.video_frame, "Effect:", ["crop", "blur", "darken"], 
            self.config.get("VIDEO_EFFECT", "crop"), row
        )
        row += 1
        
        # Padding
        self.video_padding_entry = self.create_labeled_entry(
            self.video_frame, "Circle Padding (0.5 = 50%):", 
            str(self.config.get("VIDEO_PADDING", 0.5)), row
        )
        row += 1
        
        # Количество потоков
        self.video_threads_entry = self.create_labeled_entry(
            self.video_frame, "Threads:", 
            str(self.config.get("VIDEO_THREADS", 4)), row
        )
        row += 1
        
        # Секция цвета фона
        ctk.CTkLabel(self.video_frame, text="🎨 Background Color (for crop effect)", 
                    font=ctk.CTkFont(size=16, weight="bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(20,10))
        row += 1
        
        # RGB цвета
        color_frame = ctk.CTkFrame(self.video_frame)
        color_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)
        
        ctk.CTkLabel(color_frame, text="R:").grid(row=0, column=0, padx=5)
        self.video_bg_r_entry = ctk.CTkEntry(color_frame, width=60)
        self.video_bg_r_entry.insert(0, str(self.config.get("VIDEO_BG_COLOR_R", 0)))
        self.video_bg_r_entry.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(color_frame, text="G:").grid(row=0, column=2, padx=5)
        self.video_bg_g_entry = ctk.CTkEntry(color_frame, width=60)
        self.video_bg_g_entry.insert(0, str(self.config.get("VIDEO_BG_COLOR_G", 0)))
        self.video_bg_g_entry.grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(color_frame, text="B:").grid(row=0, column=4, padx=5)
        self.video_bg_b_entry = ctk.CTkEntry(color_frame, width=60)
        self.video_bg_b_entry.insert(0, str(self.config.get("VIDEO_BG_COLOR_B", 0)))
        self.video_bg_b_entry.grid(row=0, column=5, padx=5)
        row += 1
        
        # Секция настроек аватаров
        ctk.CTkLabel(self.video_frame, text="🎭 Avatar Settings", 
                    font=ctk.CTkFont(size=16, weight="bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(20,10))
        row += 1
        
        # Размер аватаров
        avatar_size_frame = ctk.CTkFrame(self.video_frame)
        avatar_size_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)
        
        ctk.CTkLabel(avatar_size_frame, text="Avatar Size:").grid(row=0, column=0, padx=5)
        self.video_avatar_w_entry = ctk.CTkEntry(avatar_size_frame, width=80)
        self.video_avatar_w_entry.insert(0, str(self.config.get("VIDEO_AVATAR_SIZE_W", 512)))
        self.video_avatar_w_entry.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(avatar_size_frame, text="x").grid(row=0, column=2, padx=5)
        self.video_avatar_h_entry = ctk.CTkEntry(avatar_size_frame, width=80)
        self.video_avatar_h_entry.insert(0, str(self.config.get("VIDEO_AVATAR_SIZE_H", 512)))
        self.video_avatar_h_entry.grid(row=0, column=3, padx=5)
        row += 1
        
        # Интервал для аватаров
        self.video_avatar_interval_entry = self.create_labeled_entry(
            self.video_frame, "Avatar Interval (every Nth frame):", 
            str(self.config.get("VIDEO_AVATAR_INTERVAL", 30)), row
        )
        row += 1
        
        # Секция настроек overlay
        ctk.CTkLabel(self.video_frame, text="🖼️ Overlay Settings", 
                    font=ctk.CTkFont(size=16, weight="bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(20,10))
        row += 1
        
        # Позиция overlay
        self.video_overlay_position_dropdown = self.create_labeled_dropdown(
            self.video_frame, "Overlay Position:", 
            ["center", "top-left", "top-right", "bottom-left", "bottom-right"], 
            self.config.get("VIDEO_OVERLAY_POSITION", "center"), row
        )
        row += 1
        
        # Размер overlay
        self.video_overlay_size_entry = self.create_labeled_entry(
            self.video_frame, "Overlay Size (pixels):", 
            str(self.config.get("VIDEO_OVERLAY_SIZE", 300)), row
        )
        row += 1
        
        # Секция дополнительных опций
        ctk.CTkLabel(self.video_frame, text="🔧 Additional Options", 
                    font=ctk.CTkFont(size=16, weight="bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(20,10))
        row += 1
        
        # Переключатели
        self.video_single_thread_switch = self.create_labeled_switch(
            self.video_frame, "Single Thread Mode", 
            self.config.get("VIDEO_SINGLE_THREAD", False), row
        )
        row += 1
        
        self.video_no_audio_switch = self.create_labeled_switch(
            self.video_frame, "No Audio", 
            self.config.get("VIDEO_NO_AUDIO", False), row
        )
        row += 1
        
        self.video_feather_edges_switch = self.create_labeled_switch(
            self.video_frame, "Feather Edges (for overlay)", 
            self.config.get("VIDEO_FEATHER_EDGES", True), row
        )
        row += 1
        
        # Кнопки управления
        button_frame = ctk.CTkFrame(self.video_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=30)
        
        ctk.CTkButton(button_frame, text="💾 Save Video Config", 
                     command=self.save_video_config).pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(button_frame, text="▶️ Run Video Processor", 
                     command=self.run_video_processor).pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(button_frame, text="⏹️ Stop Video Processor", 
                     command=self.stop_video_processor).pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(button_frame, text="📁 Open Output Folder", 
                     command=self.open_output_folder).pack(side="left", padx=10, pady=10)

    def create_file_selector(self, frame, label, value, row, is_folder=False, select_folder=False, file_types=None):
        """Создает поле ввода с кнопкой выбора файла/папки"""
        ctk.CTkLabel(frame, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        
        entry = ctk.CTkEntry(frame, width=250)
        entry.insert(0, value)
        entry.grid(row=row, column=1, padx=10, pady=5)
        
        def select_path():
            if select_folder:
                path = fd.askdirectory()
            elif is_folder:
                # Можно выбрать и файл, и папку
                path = fd.askdirectory()
                if not path:  # Если папку не выбрали, предложить выбрать файл
                    if file_types:
                        path = fd.askopenfilename(filetypes=file_types)
                    else:
                        path = fd.askopenfilename()
            else:
                if file_types:
                    path = fd.askopenfilename(filetypes=file_types)
                else:
                    path = fd.askopenfilename()
            
            if path:
                entry.delete(0, 'end')
                entry.insert(0, path)
        
        ctk.CTkButton(frame, text="📁", width=40, command=select_path).grid(row=row, column=2, padx=5, pady=5)
        
        return entry

    def save_video_config(self):
        """Сохранение конфигурации видеопроцессора"""
        try:
            self.config.update({
                "VIDEO_INPUT_PATH": self.video_input_entry.get(),
                "VIDEO_OUTPUT_PATH": self.video_output_entry.get(),
                "VIDEO_BACKGROUND_PATH": self.video_background_entry.get(),
                "VIDEO_MODE": self.video_mode_dropdown.get(),
                "VIDEO_EFFECT": self.video_effect_dropdown.get(),
                "VIDEO_BG_COLOR_R": int(self.video_bg_r_entry.get() or 0),
                "VIDEO_BG_COLOR_G": int(self.video_bg_g_entry.get() or 0),
                "VIDEO_BG_COLOR_B": int(self.video_bg_b_entry.get() or 0),
                "VIDEO_PADDING": float(self.video_padding_entry.get() or 0.5),
                "VIDEO_THREADS": int(self.video_threads_entry.get() or 4),
                "VIDEO_SINGLE_THREAD": self.video_single_thread_switch.get(),
                "VIDEO_NO_AUDIO": self.video_no_audio_switch.get(),
                "VIDEO_AVATAR_SIZE_W": int(self.video_avatar_w_entry.get() or 512),
                "VIDEO_AVATAR_SIZE_H": int(self.video_avatar_h_entry.get() or 512),
                "VIDEO_AVATAR_INTERVAL": int(self.video_avatar_interval_entry.get() or 30),
                "VIDEO_OVERLAY_POSITION": self.video_overlay_position_dropdown.get(),
                "VIDEO_OVERLAY_SIZE": int(self.video_overlay_size_entry.get() or 300),
                "VIDEO_FEATHER_EDGES": self.video_feather_edges_switch.get()
            })
            save_config(self.config)
            mb.showinfo("Success", "Video processor configuration saved!")
        except Exception as e:
            mb.showerror("Error", f"Error saving configuration: {e}")

    def run_video_processor(self):
        """Запуск видеопроцессора"""
        if self.video_process and self.video_process.poll() is None:
            mb.showwarning("Warning", "Video processor is already running!")
            return
        
        # Проверяем обязательные поля
        if not self.video_input_entry.get():
            mb.showerror("Error", "Please select input video/folder!")
            return
        
        if not self.video_output_entry.get():
            mb.showerror("Error", "Please select output folder!")
            return
        
        mode = self.video_mode_dropdown.get()
        if mode == "overlay" and not self.video_background_entry.get():
            mb.showerror("Error", "Background video is required for overlay mode!")
            return
        
        try:
            # Сохраняем конфигурацию перед запуском
            self.save_video_config()
            
            # Определяем какой скрипт использовать и формируем команду
            if mode == "overlay":
                # Для overlay режима
                script_name = "face_circle_extractor.py"
                cmd = ["python", script_name]
                cmd.extend([self.video_input_entry.get(), self.video_background_entry.get()])
                cmd.extend(["-o", self.video_output_entry.get()])
                cmd.extend(["--mode", "overlay"])
                cmd.extend(["--position", self.video_overlay_position_dropdown.get()])
                cmd.extend(["--size", str(self.video_overlay_size_entry.get())])
                if not self.video_feather_edges_switch.get():
                    cmd.append("--no-feather")
            else:
                # Для обычных режимов video и avatars
                script_name = "face_circle_extractor.py"
                cmd = ["python", script_name]
                cmd.extend([self.video_input_entry.get()])
                cmd.extend(["-o", self.video_output_entry.get()])
                cmd.extend(["--mode", mode])
                
                if mode == "video":
                    cmd.extend(["--effect", self.video_effect_dropdown.get()])
                    
                    # Цвет фона
                    bg_r = int(self.video_bg_r_entry.get() or 0)
                    bg_g = int(self.video_bg_g_entry.get() or 0)
                    bg_b = int(self.video_bg_b_entry.get() or 0)
                    cmd.extend(["--bg-color", str(bg_b), str(bg_g), str(bg_r)])  # BGR порядок для OpenCV
                
                elif mode == "avatars":
                    # Настройки аватаров
                    avatar_w = int(self.video_avatar_w_entry.get() or 512)
                    avatar_h = int(self.video_avatar_h_entry.get() or 512)
                    cmd.extend(["--avatar-size", str(avatar_w), str(avatar_h)])
                    cmd.extend(["--avatar-interval", str(self.video_avatar_interval_entry.get() or 30)])
            
            # Общие параметры
            cmd.extend(["--padding", str(self.video_padding_entry.get() or 0.5)])
            
            if not self.video_single_thread_switch.get():
                cmd.extend(["--threads", str(self.video_threads_entry.get() or 4)])
            else:
                cmd.append("--single-thread")
            
            if self.video_no_audio_switch.get():
                cmd.append("--no-audio")
            
            print("Running command:", " ".join(cmd))
            
            # Проверяем существует ли файл скрипта
            if not os.path.exists(script_name):
                mb.showerror("Error", f"Script file '{script_name}' not found!\nMake sure the script is in the same directory as ui.py")
                return
            
            # Запускаем процесс без мониторинга в реальном времени (упрощенная версия)
            self.video_process = subprocess.Popen(cmd)
            
            # Запускаем мониторинг процесса в отдельном потоке
            self.start_process_monitoring()
            
            mb.showinfo("Started", f"Video processor started successfully!\nCommand: {' '.join(cmd)}")
            
        except Exception as e:
            mb.showerror("Error", f"Error starting video processor: {e}")
    
    def start_process_monitoring(self):
        """Запуск мониторинга процесса в отдельном потоке (упрощенная версия)"""
        def monitor_process():
            if self.video_process:
                try:
                    # Просто ждем завершения процесса
                    self.video_process.wait()
                    
                    if self.video_process.returncode == 0:
                        print("[VIDEO PROCESSOR]: Process completed successfully!")
                    else:
                        print(f"[VIDEO PROCESSOR]: Process failed with return code {self.video_process.returncode}")
                        
                except Exception as e:
                    print(f"[VIDEO PROCESSOR]: Error monitoring process: {e}")
        
        # Запускаем мониторинг в отдельном потоке
        try:
            monitor_thread = threading.Thread(target=monitor_process, daemon=True)
            monitor_thread.start()
        except Exception as e:
            print(f"Threading error: {e}")
            # Если есть проблемы с потоками, просто не мониторим

    def stop_video_processor(self):
        """Остановка видеопроцессора"""
        if self.video_process and self.video_process.poll() is None:
            self.video_process.terminate()
            mb.showinfo("Stopped", "Video processor stopped!")
        else:
            mb.showinfo("Info", "Video processor is not running")

    def open_output_folder(self):
        """Открытие папки с результатами"""
        output_path = self.video_output_entry.get()
        if output_path and os.path.exists(output_path):
            if os.name == 'nt':  # Windows
                os.startfile(output_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['open', output_path])
        else:
            mb.showerror("Error", "Output folder doesn't exist!")

    def create_settings_frame(self):
        # Dropdown LANGUAGE
        ctk.CTkLabel(self.settings_frame, text="Language:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.language_dropdown = ctk.CTkComboBox(self.settings_frame, values=["en", "uk", "ru"])
        self.language_dropdown.set(self.config.get("LANGUAGE", "en"))
        self.language_dropdown.grid(row=0, column=1, padx=10, pady=10)
        
        self.tester_mode_switch = self.create_labeled_switch(
            self.settings_frame, "Режим тестировщика", self.config.get("TESTER_MODE", False), 1)

        # Save
        ctk.CTkButton(self.settings_frame, text="Save Settings", command=self.save_settings).grid(row=2, column=1, pady=20)

        # Dev info
        ctk.CTkLabel(self.settings_frame, text="Developer: Viacheslav Omeniuk", font=ctk.CTkFont(size=12)).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        ctk.CTkLabel(self.settings_frame, text="Telegram: https://t.me/DinosaurDesign", font=ctk.CTkFont(size=12)).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=5)

    def create_labeled_entry(self, frame, label, value, row):
        ctk.CTkLabel(frame, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        entry = ctk.CTkEntry(frame, width=200)
        entry.insert(0, value)
        entry.grid(row=row, column=1, padx=10, pady=5)
        return entry

    def create_labeled_switch(self, frame, label, value, row):
        ctk.CTkLabel(frame, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        switch = ctk.CTkSwitch(frame, text="", onvalue=True, offvalue=False)
        switch.select() if value else switch.deselect()
        switch.grid(row=row, column=1, padx=10, pady=5)
        return switch

    def create_labeled_dropdown(self, frame, label, values, selected_value, row):
        ctk.CTkLabel(frame, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        combo = ctk.CTkComboBox(frame, values=values, state="readonly", width=200)
        combo.set(selected_value)
        combo.grid(row=row, column=1, padx=10, pady=5)
        return combo

    def save_main(self):
        self.config.update({
            "EMAIL": self.email_entry.get(),
            "PASSWORD": self.password_entry.get(),
            "BASE_URL": self.baseurl_entry.get(),
            "REPEAT_COUNT": int(self.repeat_entry.get()),
            "ENABLE_SUBTITLES": self.subtitles_switch.get(),
            "WITH_WATERMARK": self.watermark_switch.get(),
            "RESOLUTION": self.resolution_dropdown.get(),
            "QUALITY": self.quality_dropdown.get(),
            "FRAMERATE": self.framerate_dropdown.get(),
            "FORMAT": self.format_dropdown.get(),
            "THREADS": int(self.threads_entry.get())
        })
        save_config(self.config)
        mb.showinfo("Success", "Main configuration saved!")

    def save_settings(self):
        self.config["LANGUAGE"] = self.language_dropdown.get()
        self.config["TESTER_MODE"] = self.tester_mode_switch.get()
        save_config(self.config)
        mb.showinfo("Success", "Settings saved!")

    def show_main(self):
        self.video_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    def show_video(self):
        self.main_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.video_frame.pack(fill="both", expand=True)

    def show_settings(self):
        self.main_frame.pack_forget()
        self.video_frame.pack_forget()
        self.settings_frame.pack(fill="both", expand=True)

    def stop_main_script(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            mb.showinfo("Stopped", "Main script stopped!")
        else:
            mb.showinfo("Info", "Main script is not running")

if __name__ == "__main__":
    app = ConfigEditor()
    app.mainloop()