#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import os
import sys
import time
import subprocess
import platform

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
FONT   = "Helvetica" if IS_MAC else "Microsoft YaHei"


class Tooltip:
    def __init__(self, widget, text):
        self.tip = None
        widget.bind("<Enter>", lambda e: self._show(widget, text))
        widget.bind("<Leave>", lambda e: self._hide())

    def _show(self, widget, text):
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        self.tip = tk.Toplevel(widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=text, font=(FONT, 10),
                 bg="#FFFBCC", relief="solid", bd=1,
                 padx=6, pady=4, justify="left").pack()

    def _hide(self):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App:
    WAIT  = "⏳"
    DOING = "🔄"
    DONE  = "✅"
    ERROR = "❌"

    def __init__(self, root):
        self.root = root
        self.root.title("逐字稿提取")
        self.root.geometry("560x640")
        self.root.resizable(False, False)
        self.file_list   = []
        self._paused     = False
        self._device     = "cpu"
        self._out_paths  = []
        self._build()

    def _build(self):
        tk.Label(self.root, text="第一步：选择文件",
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=20, pady=(16, 4))

        file_ctrl = tk.Frame(self.root)
        file_ctrl.pack(fill="x", padx=20)
        tk.Button(file_ctrl, text="添加文件", font=(FONT, 11),
                  padx=8, command=self.add_files).pack(side="left")
        tk.Button(file_ctrl, text="删除选中", font=(FONT, 11),
                  padx=8, command=self.remove_selected).pack(side="left", padx=(8, 0))
        tk.Button(file_ctrl, text="清空列表", font=(FONT, 11),
                  padx=8, command=self.clear_files).pack(side="left", padx=(8, 0))

        self.file_count_label = tk.Label(file_ctrl, text="尚未选择文件",
                                         font=(FONT, 10), fg="gray")
        self.file_count_label.pack(side="right")

        list_frame = tk.Frame(self.root, relief="groove", bd=1)
        list_frame.pack(fill="x", padx=20, pady=(6, 0))
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(list_frame, height=6, font=(FONT, 11),
                                  yscrollcommand=scrollbar.set,
                                  selectmode="extended", activestyle="none")
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(fill="x")

        tk.Label(self.root, text="第二步：选择语言",
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=20, pady=(14, 4))

        self.lang_var = tk.StringVar(value="zh")
        lang_row = tk.Frame(self.root)
        lang_row.pack(anchor="w", padx=20)
        for text, val, tip in [
            ("中文", "zh",   "普通话、粤语、闽南语等中文内容\n国内短视频、采访、会议录音首选"),
            ("英文", "en",   "全程英文的视频或播客\n指定语言比自动检测更快更准"),
            ("自动检测", "None", "中英混合、不确定语言时使用\n速度略慢，Whisper 会先判断语言"),
        ]:
            b = tk.Radiobutton(lang_row, text=text, variable=self.lang_var,
                               value=val, font=(FONT, 12))
            b.pack(side="left", padx=8)
            Tooltip(b, tip)

        tk.Label(self.root, text="第三步：选择精度",
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=20, pady=(14, 4))

        self.model_var = tk.StringVar(value="base")
        self._model_speeds = {
            "tiny": 15.0, "base": 8.0, "small": 4.0, "medium": 2.0, "large": 1.0
        }

        model_row = tk.Frame(self.root)
        model_row.pack(anchor="w", padx=20)
        self._model_time_labels = {}

        for text, val, tip in [
            ("tiny\n最快",   "tiny",   "适合快速预览内容大意\n说话清晰、普通话标准时可用\n速度最快，偶尔会漏字"),
            ("base\n推荐",   "base",   "日常使用首选\n普通话口播、采访、会议均适用\n速度与准确度平衡最佳"),
            ("small\n较准",  "small",  "说话较快或有轻微口音时使用\n比 base 更少漏词\n速度稍慢，约多花 1 倍时间"),
            ("medium\n更准", "medium", "内容含专业术语、方言口音较重时使用\n识别率明显提升\n速度约为 base 的 1/3"),
            ("large\n最准",  "large",  "最高精度，适合字幕级别要求\n混合语言、强口音、嘈杂环境效果最好\n速度最慢，约多花 4-5 倍时间"),
        ]:
            col = tk.Frame(model_row)
            col.pack(side="left", padx=10)
            b = tk.Radiobutton(col, text=text, variable=self.model_var,
                               value=val, font=(FONT, 10), justify="center")
            b.pack()
            Tooltip(b, tip)
            lbl = tk.Label(col, text="--", font=(FONT, 9), fg="#999")
            lbl.pack()
            self._model_time_labels[val] = lbl

        btn_row = tk.Frame(self.root)
        btn_row.pack(pady=(14, 6))

        self.start_btn = tk.Button(btn_row, text="开始转录",
                                   font=(FONT, 13, "bold"),
                                   width=14, command=self.start)
        self.start_btn.pack(side="left", padx=(0, 8))

        self.pause_btn = tk.Button(btn_row, text="⏸ 暂停",
                                   font=(FONT, 11), width=8,
                                   state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=(0, 8))

        bench_btn = tk.Button(btn_row, text="⚡ 测试算力",
                              font=(FONT, 11), width=10,
                              command=self.run_benchmark)
        bench_btn.pack(side="left")
        Tooltip(bench_btn, "检测 CPU / GPU 算力\n并推荐最适合的运行模式")

        self.overall_label = tk.Label(self.root, text="",
                                      font=(FONT, 10), fg="gray")
        self.overall_label.pack(anchor="w", padx=20)

        prog_row = tk.Frame(self.root)
        prog_row.pack(fill="x", padx=20, pady=(2, 0))
        self.progress = ttk.Progressbar(prog_row, length=380,
                                        mode="determinate", maximum=100)
        self.progress.pack(side="left")
        self.pct_label = tk.Label(prog_row, text="  0%",
                                  font=(FONT, 11), width=5)
        self.pct_label.pack(side="left")

        eta_row = tk.Frame(self.root)
        eta_row.pack(fill="x", padx=20, pady=(4, 0))

        tk.Label(eta_row, text="已用：", font=(FONT, 10), fg="#555").pack(side="left")
        self.elapsed_label = tk.Label(eta_row, text="--:--",
                                      font=(FONT, 10, "bold"), fg="#333", width=6)
        self.elapsed_label.pack(side="left")

        tk.Label(eta_row, text="  剩余：", font=(FONT, 10), fg="#555").pack(side="left")
        self.eta_label = tk.Label(eta_row, text="--:--",
                                  font=(FONT, 10, "bold"), fg="#007AFF", width=8)
        self.eta_label.pack(side="left")

        self.status_label = tk.Label(self.root, text="请添加文件后点击「开始转录」",
                                     font=(FONT, 10), fg="gray")
        self.status_label.pack(pady=(4, 0))

        self.result_frame = tk.Frame(self.root)
        self.result_label = tk.Label(self.result_frame,
                                     text="转录完成，点击文件名在 Finder 中显示：",
                                     font=(FONT, 10), fg="gray", anchor="w")
        self.result_label.pack(anchor="w", padx=20)

        result_list_frame = tk.Frame(self.result_frame, relief="groove", bd=1)
        result_list_frame.pack(fill="x", padx=20, pady=(4, 0))
        self.result_listbox = tk.Listbox(result_list_frame, height=4,
                                         font=(FONT, 11),
                                         fg="blue", cursor="hand2",
                                         activestyle="none")
        self.result_listbox.pack(fill="x")
        self.result_listbox.bind("<Button-1>", self._on_result_click)

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="选择视频或音频文件（可多选）",
            filetypes=[("媒体文件", "*.mp4 *.mov *.avi *.mkv *.m4v *.mp3 *.m4a *.wav *.aac *.flac"),
                       ("所有文件", "*.*")]
        )
        for p in paths:
            if p not in [f[0] for f in self.file_list]:
                dur = self._get_duration(p)
                self.file_list.append((p, dur))
                self.listbox.insert(tk.END, f"{self.WAIT}  {os.path.basename(p)}")
        self._update_count()
        self._update_time_estimates()

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        for i in reversed(selected):
            self.listbox.delete(i)
            self.file_list.pop(i)
        self._update_count()
        self._update_time_estimates()

    def clear_files(self):
        self.file_list.clear()
        self.listbox.delete(0, tk.END)
        self._update_count()
        self._update_time_estimates()

    def _update_time_estimates(self):
        total_dur = sum(d for _, d in self.file_list if d)
        for model, lbl in self._model_time_labels.items():
            if total_dur == 0:
                lbl.config(text="--", fg="#999")
            else:
                secs = total_dur / self._model_speeds[model]
                lbl.config(text=f"约 {self._fmt(secs)}", fg="#007AFF")

    def _update_count(self):
        n = len(self.file_list)
        self.file_count_label.config(
            text=f"已选 {n} 个文件" if n > 0 else "尚未选择文件",
            fg="black" if n > 0 else "gray"
        )

    def _get_duration(self, path):
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                capture_output=True, text=True
            )
            return float(r.stdout.strip())
        except Exception:
            return None

    def start(self):
        if not self.file_list:
            self.set_status("请先添加文件！", "red")
            return
        self._paused = False
        self._out_paths = []
        self._batch_start = time.time()
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.result_frame.pack_forget()
        self.set_progress(0)
        self.set_eta("--:--", "--:--", "--")
        for i in range(len(self.file_list)):
            name = os.path.basename(self.file_list[i][0])
            self.listbox.delete(i)
            self.listbox.insert(i, f"{self.WAIT}  {name}")
        self.set_status("加载模型中，请稍候…", "blue")
        threading.Thread(target=self._run_batch, daemon=True).start()

    def toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self.pause_btn.config(text="▶ 继续")
            self.set_status("已暂停，点击继续恢复转录…", "#FF9500")
        else:
            self.pause_btn.config(text="⏸ 暂停")
            self.set_status(f"转录中（{'GPU 加速' if self._device != 'cpu' else 'CPU'}）…", "blue")

    def _run_batch(self):
        try:
            import whisper
            import torch
        except ImportError as e:
            err = str(e)
            self.set_status(f"缺少依赖：{err}", "red")
            self._finish()
            return

        try:
            lang = self.lang_var.get()
            if lang == "None":
                lang = None

            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
            model_name = self.model_var.get()

            print(f"\n{'='*52}")
            print(f"  逐字稿提取工具  启动")
            print(f"{'='*52}")
            print(f"  模型：{model_name}  |  设备：{self._device.upper()}  |  语言：{lang or 'auto'}")
            print(f"  队列：{len(self.file_list)} 个文件")
            print(f"{'='*52}\n")
            print(f"  加载模型 [{model_name}]...")

            model = whisper.load_model(model_name, device=self._device)
            print(f"  模型加载完成 ✓\n")

            total_files  = len(self.file_list)
            done_count   = 0
            error_count  = 0

            for file_idx, (path, duration) in enumerate(self.file_list):
                name = os.path.basename(path)

                print(f"  ┌─ 文件 [{file_idx+1}/{total_files}] {name}")
                if duration:
                    m, s = divmod(int(duration), 60)
                    print(f"  │  时长：{m:02d}:{s:02d}  |  路径：{path}")

                self._set_list_item(file_idx, self.DOING, name)
                self.set_overall(file_idx + 1, total_files, name)
                self.set_progress(0)
                self.set_status(
                    f"转录中（{'GPU 加速' if self._device != 'cpu' else 'CPU'}）…", "blue"
                )

                try:
                    out_path = self._transcribe_one(model, path, duration, lang)
                    self._set_list_item(file_idx, self.DONE, name)
                    self._out_paths.append(out_path)
                    done_count += 1
                    print(f"  └─ 完成 ✓  →  {out_path}\n")
                except Exception as e:
                    err = str(e)
                    self._set_list_item(file_idx, self.ERROR, f"{name}  [{err}]")
                    error_count += 1
                    print(f"  └─ 失败 ✗  {err}\n")

            total_time = self._fmt(time.time() - self._batch_start)
            print(f"{'='*52}")
            print(f"  全部完成  ✓  成功 {done_count} 个  失败 {error_count} 个")
            print(f"  总耗时：{total_time}")
            print(f"{'='*52}\n")
            self.set_progress(100)
            if error_count == 0:
                self.set_status(f"全部完成 ✓  共 {done_count} 个文件", "green")
            else:
                self.set_status(
                    f"完成 {done_count} 个，失败 {error_count} 个", "#FF9500"
                )
            self._show_results()

        except Exception as e:
            err = str(e)
            self.set_status(f"出错：{err}", "red")

        self._finish()

    def _transcribe_one(self, model, path, duration, lang):
        import whisper

        audio        = whisper.load_audio(path)
        chunk_size   = 30 * whisper.audio.SAMPLE_RATE
        chunks       = [audio[i:i + chunk_size]
                        for i in range(0, len(audio), chunk_size)]
        total_chunks = len(chunks)

        decode_opts = whisper.DecodingOptions(
            language=lang,
            fp16=(self._device != "cpu"),
        )

        all_text   = []
        chunk_times = []

        for i, chunk in enumerate(chunks):
            while self._paused:
                time.sleep(0.2)

            t0     = time.time()
            padded = whisper.pad_or_trim(chunk)
            mel    = whisper.log_mel_spectrogram(padded).to(self._device)
            result = whisper.decode(model, mel, decode_opts)
            all_text.append(result.text)
            chunk_times.append(time.time() - t0)

            pct         = min(int((i + 1) / total_chunks * 100), 99)
            avg_chunk   = sum(chunk_times) / len(chunk_times)
            remaining   = avg_chunk * (total_chunks - i - 1)
            elapsed_all = time.time() - self._batch_start
            speed       = 30 / avg_chunk

            chunk_start_sec = i * 30
            cm, cs = divmod(chunk_start_sec, 60)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"  │  [{bar}] {pct:3d}%  "
                  f"片段 {i+1:3d}/{total_chunks}  "
                  f"@{cm:02d}:{cs:02d}  "
                  f"{speed:.1f}x  "
                  f"剩余 {self._fmt(remaining)}")
            if result.text.strip():
                print(f"  │  ▶ {result.text.strip()[:60]}")

            self.set_progress(pct)
            self.set_eta(self._fmt(elapsed_all), self._fmt(remaining))

        full_text = "".join(all_text).strip()
        out_path  = os.path.splitext(path)[0] + "_逐字稿.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        return out_path

    def _show_results(self):
        def _do():
            self.result_listbox.delete(0, tk.END)
            for p in self._out_paths:
                self.result_listbox.insert(tk.END, f"📄  {os.path.basename(p)}")
            self.result_frame.pack(fill="x", pady=(6, 0))
        self.root.after(0, _do)

    def _on_result_click(self, event):
        idx = self.result_listbox.nearest(event.y)
        if 0 <= idx < len(self._out_paths):
            p = self._out_paths[idx]
            if IS_MAC:
                subprocess.run(["open", "-R", p])
            elif IS_WIN:
                subprocess.run(["explorer", "/select,", p])

    def run_benchmark(self):
        win = tk.Toplevel(self.root)
        win.title("算力测试")
        win.geometry("340x200")
        win.resizable(False, False)
        lbl = tk.Label(win, text="测试中，约 15 秒…",
                       font=(FONT, 12), fg="gray")
        lbl.pack(expand=True)

        def _do():
            try:
                import torch

                def measure(dev):
                    size = 2048
                    d = torch.device(dev)
                    a = torch.randn(size, size, device=d)
                    b = torch.randn(size, size, device=d)
                    torch.mm(a, b)
                    if dev == "mps":
                        torch.mps.synchronize()
                    elif dev == "cuda":
                        torch.cuda.synchronize()
                    t0 = time.time()
                    for _ in range(10):
                        torch.mm(a, b)
                    if dev == "mps":
                        torch.mps.synchronize()
                    elif dev == "cuda":
                        torch.cuda.synchronize()
                    return (2 * size**3 * 10) / (time.time() - t0) / 1e9

                cpu = measure("cpu")
                if torch.backends.mps.is_available():
                    gpu = measure("mps")
                    gpu_name = "GPU (MPS)"
                elif torch.cuda.is_available():
                    gpu = measure("cuda")
                    gpu_name = f"GPU ({torch.cuda.get_device_name(0)})"
                else:
                    gpu = 0
                    gpu_name = None

                if gpu_name:
                    speedup = gpu / cpu
                    rec = gpu_name if speedup > 1.5 else "CPU"
                    msg = (f"CPU 算力：{cpu:.0f} GFLOPS\n"
                           f"GPU 算力：{gpu:.0f} GFLOPS\n"
                           f"GPU 比 CPU 快：{speedup:.1f} 倍\n\n"
                           f"建议使用：{rec}\n"
                           f"{'✅ 已自动使用 GPU 加速' if speedup > 1.5 else '✅ CPU 模式已足够'}")
                else:
                    msg = f"CPU 算力：{cpu:.0f} GFLOPS\nGPU：不可用\n\n建议使用：CPU 模式"

                final_msg = msg
                win.after(0, lambda m=final_msg: lbl.config(text=m, fg="black",
                                                             justify="left", padx=20))
            except Exception as e:
                err_msg = f"出错：{e}"
                win.after(0, lambda m=err_msg: lbl.config(text=m, fg="red"))

        threading.Thread(target=_do, daemon=True).start()

    def _set_list_item(self, idx, icon, name):
        def _do():
            self.listbox.delete(idx)
            self.listbox.insert(idx, f"{icon}  {name}")
        self.root.after(0, _do)

    def set_overall(self, current, total, name):
        self.root.after(0, lambda: self.overall_label.config(
            text=f"第 {current} / {total} 个文件：{name}", fg="#555"
        ))

    def set_progress(self, value):
        self.root.after(0, lambda: (
            self.progress.config(value=value),
            self.pct_label.config(text=f"{value:3d}%"),
        ))

    def set_status(self, msg, color="gray"):
        self.root.after(0, lambda: self.status_label.config(text=msg, fg=color))

    def set_eta(self, elapsed, remaining, speed=None):
        self.root.after(0, lambda: (
            self.elapsed_label.config(text=elapsed),
            self.eta_label.config(text=remaining),
        ))

    def _fmt(self, seconds):
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        if m >= 60:
            h, m = divmod(m, 60)
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _finish(self):
        total_elapsed = self._fmt(time.time() - self._batch_start)
        self.root.after(0, lambda: (
            self.start_btn.config(state="normal"),
            self.pause_btn.config(state="disabled", text="⏸ 暂停"),
            self.elapsed_label.config(text=total_elapsed),
            self.eta_label.config(text="已完成", fg="green"),
        ))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
