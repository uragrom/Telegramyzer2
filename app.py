import os
import threading
from pathlib import Path
from tkinter import Tk, ttk, Listbox, StringVar, END, filedialog, messagebox, HORIZONTAL

CHUNK_SIZE_DEFAULT = 1800 * 1024 * 1024  # 1.8 GiB
READ_BLOCK = 10 * 1024 * 1024  # 10 MiB

class TelegramizerGUI:
    def __init__(self, root):
        self.root = root
        root.title('Telegramizer — split & join files')
        root.geometry('800x450')

        self.items = []
        self.output_dir = StringVar(value=str(Path.cwd()))
        self.chunk_size_var = StringVar(value=str(CHUNK_SIZE_DEFAULT))

        # Настройка тёмной темы
        self.style = ttk.Style()
        self._setup_dark_theme()

        self._build_ui()
        self._stop_flag = False

    def _setup_dark_theme(self):
        # Настройка тёмной темы
        self.style.theme_use('clam')
        # Основные цвета
        bg_color = '#1e1e1e'
        fg_color = '#ffffff'
        button_bg = '#333333'
        button_active = '#444444'
        entry_bg = '#333333'

        # Фон главного окна
        self.root.config(bg=bg_color)

        # Стили ttk виджетов
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TButton', background=button_bg, foreground=fg_color, borderwidth=1, relief='flat', highlightbackground=button_bg, highlightcolor=button_bg, highlightthickness=0)
        self.style.map('TButton', background=[('active', button_active)])
        self.style.configure('TLabel', background=bg_color, foreground=fg_color)
        self.style.configure('TEntry', fieldbackground=entry_bg, foreground=fg_color, insertcolor=fg_color)
        self.style.configure('TProgressbar', background=button_bg, troughcolor=bg_color, borderwidth=1, lightcolor=button_bg, darkcolor=button_bg)

        # Additional styling for Listbox
        self.style.map('Listbox', background=[('selected', button_bg), ('active', button_bg)])
        self.style.map('Listbox', foreground=[('selected', fg_color)])

        # Additional styling for Progressbar
        self.style.map('Progressbar', background=[('active', button_bg)])
    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text='Queue (files and folders):').grid(row=0, column=0, sticky='w')
        self.listbox = Listbox(frm, height=15, width=80, bg='#333333', fg='#ffffff', selectbackground='#444444', selectforeground='#ffffff')
        self.listbox.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=2, pady=2)

        ttk.Button(frm, text='Add Files', command=self.add_files).grid(row=2, column=0, sticky='ew', padx=2, pady=5)
        ttk.Button(frm, text='Add Folder', command=self.add_folder).grid(row=2, column=1, sticky='ew', padx=2, pady=5)
        ttk.Button(frm, text='Remove Selected', command=self.remove_selected).grid(row=2, column=2, sticky='ew', padx=2, pady=5)
        ttk.Button(frm, text='Clear Queue', command=self.clear_queue).grid(row=2, column=3, sticky='ew', padx=2, pady=5)

        ttk.Label(frm, text='Output folder:').grid(row=3, column=0, sticky='w', pady=(10,0))
        ttk.Entry(frm, textvariable=self.output_dir, width=60).grid(row=4, column=0, columnspan=3, sticky='ew', padx=2, pady=5)
        ttk.Button(frm, text='Browse', command=self.choose_output).grid(row=4, column=3, sticky='ew', padx=2, pady=5)

        ttk.Label(frm, text='Chunk size (bytes):').grid(row=5, column=0, sticky='w', pady=(10,0))
        ttk.Entry(frm, textvariable=self.chunk_size_var).grid(row=6, column=0, sticky='ew', padx=2, pady=5)
        ttk.Label(frm, text='(Default 1.8 GiB = 1887436800)').grid(row=6, column=1, sticky='w')

        ttk.Button(frm, text='Start Split', command=self.start_split).grid(row=7, column=0, sticky='ew', pady=(15,0))
        ttk.Button(frm, text='Join Parts', command=self.start_join).grid(row=7, column=1, sticky='ew', pady=(15,0))
        ttk.Button(frm, text='Stop', command=self.stop_split).grid(row=7, column=2, sticky='ew', pady=(15,0))
        ttk.Button(frm, text='Help', command=self.show_help).grid(row=7, column=3, sticky='ew', pady=(15,0))

        self.progress = ttk.Progressbar(frm, orient=HORIZONTAL, length=700, mode='determinate')
        self.progress.grid(row=8, column=0, columnspan=4, sticky='ew', pady=(15,0))

        self.log = Listbox(frm, height=8, bg='#333333', fg='#ffffff', selectbackground='#444444', selectforeground='#ffffff')
        self.log.grid(row=9, column=0, columnspan=4, sticky='nsew', padx=2, pady=4)

        frm.rowconfigure(1, weight=1)
        frm.rowconfigure(9, weight=1)
        for c in range(4):
            frm.columnconfigure(c, weight=1)

    def add_files(self):
        paths = filedialog.askopenfilenames(title='Select files to add')
        for p in paths:
            self.items.append(p)
            self.listbox.insert(END, p)

    def add_folder(self):
        folder = filedialog.askdirectory(title='Select folder to add')
        if folder:
            self.items.append(folder + os.sep)
            self.listbox.insert(END, folder + os.sep)

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        for i in reversed(sel):
            self.listbox.delete(i)
            del self.items[i]

    def clear_queue(self):
        self.listbox.delete(0, END)
        self.items.clear()

    def choose_output(self):
        d = filedialog.askdirectory(title='Choose output directory')
        if d:
            self.output_dir.set(d)

    def log_msg(self, msg):
        self.log.insert(END, msg)
        self.log.yview_moveto(1)

    def start_split(self):
        if not self.items:
            messagebox.showinfo('Info', 'Add files/folders first')
            return
        try:
            chunk_size = int(self.chunk_size_var.get())
        except:
            messagebox.showerror('Error', 'Invalid chunk size')
            return

        self._stop_flag = False
        t = threading.Thread(target=self._split_queue, args=(self.items.copy(), self.output_dir.get(), chunk_size), daemon=True)
        t.start()

    def stop_split(self):
        self._stop_flag = True
        self.log_msg('Stop requested')

    def start_join(self):
        part_file = filedialog.askopenfilename(title='Select first part of file to join')
        if not part_file:
            return
        output_file = filedialog.asksaveasfilename(title='Save joined file as')
        if not output_file:
            return
        t = threading.Thread(target=self._join_file, args=(part_file, output_file), daemon=True)
        t.start()

    def _split_queue(self, items, output_dir, chunk_size):
        total = len(items)
        for idx, path in enumerate(items, 1):
            if self._stop_flag:
                self.log_msg('Stopped by user')
                break
            if os.path.isfile(path):
                self._split_file(path, output_dir, chunk_size)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for f in files:
                        self._split_file(os.path.join(root, f), os.path.join(output_dir, os.path.relpath(root, path)), chunk_size)
            self.progress['value'] = int(idx/total*100)
        self.log_msg('Split done')

    def _split_file(self, filepath, output_dir, chunk_size):
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        parts = (size + chunk_size - 1)//chunk_size
        with open(filepath, 'rb') as f:
            for i in range(1, parts+1):
                chunk = f.read(chunk_size)
                out_file = os.path.join(output_dir, f'{base}.part{i:03d}')
                with open(out_file, 'wb') as out:
                    out.write(chunk)
                self.log_msg(f'Created {out_file} ({len(chunk)} bytes)')

    def _join_file(self, first_part, output_file):
        dir_name = os.path.dirname(first_part)
        base_name = first_part.rsplit('.part',1)[0]
        parts = sorted([f for f in os.listdir(dir_name) if f.startswith(os.path.basename(base_name))], key=lambda x: x)
        with open(output_file, 'wb') as out:
            for p in parts:
                path = os.path.join(dir_name, p)
                if not os.path.isfile(path):
                    self.log_msg(f'File not found, skipped: {p}')
                    continue
                with open(path,'rb') as f:
                    while True:
                        data = f.read(READ_BLOCK)
                        if not data:
                            break
                        out.write(data)
                self.log_msg(f'Joined {p}')
        messagebox.showinfo('Done', f'File joined as {output_file}')

    def show_help(self):
        messagebox.showinfo('Help','Split files/folders <1.8GB. Use Join Parts to merge back.')

if __name__=='__main__':
    root = Tk()
    app = TelegramizerGUI(root)
    root.mainloop()