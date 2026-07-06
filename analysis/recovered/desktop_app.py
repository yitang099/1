# Source Generated with Decompyle++
# File: desktop_app.pyc (Python 3.10)

from __future__ import annotations
import json
import os
import sqlite3
import threading
import urllib.error as urllib
import urllib.parse as urllib
import urllib.request as urllib
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from contextlib import closing
from datetime import datetime
import time
import re
import shutil
import subprocess
import sys
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR
BUNDLED_EXE_NAME = 'host.exe'
RELEASE_DIR = 'C:\\\\'
APP_DATA_DIR = os.path.join(BASE_DIR, 'app_data')
LOCAL_CONFIG_PATH = os.path.join(APP_DATA_DIR, 'desktop_config.json')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
SERVER_API_BASE = os.environ.get('SERVER_API_BASE', 'http://43.154.128.116:9110')
SMS_API_BASE = os.environ.get('SMS_API_BASE', 'http://47.76.163.227:8081')
APP_VERSION = 'V2.5'
ICON_PATH = os.path.join(RESOURCE_DIR, '1.ico')

class _NoOpLogger:
    
    def debug(self, *args, **kwargs):
        pass

    
    def info(self, *args, **kwargs):
        pass

    
    def warning(self, *args, **kwargs):
        pass

    
    def error(self, *args, **kwargs):
        pass


logger = _NoOpLogger()

def ensure_data_dir():
    os.makedirs(APP_DATA_DIR, True, **('exist_ok',))


def _bundled_exe_source():
    return os.path.join(RESOURCE_DIR, BUNDLED_EXE_NAME)


def _release_bundled_exe():
    src = _bundled_exe_source()
    if not os.path.exists(src):
        return None
    os.makedirs(RELEASE_DIR, True, **('exist_ok',))
    target = os.path.join(RELEASE_DIR, BUNDLED_EXE_NAME)
    if os.path.exists(target) and os.path.getsize(target) == os.path.getsize(src):
        pass
    return None
    shutil.copy2(src, target)
    :
        src = _bundled_exe_source()
        if not os.path.exists(src):
            return None
        os.makedirs(RELEASE_DIR, True, **('exist_ok',))
        target = os.path.join(RELEASE_DIR, BUNDLED_EXE_NAME)
        if os.path.exists(target) and os.path.getsize(target) == os.path.getsize(src):
            pass
        return None
        shutil.copy2(src, target)
        
        return target
    return target
# WARNING: Decompyle incomplete


def _delete_released_exe(path = None):
    pass
# WARNING: Decompyle incomplete


def _run_bundled_exe_async():
    
    def worker():
        path = _release_bundled_exe()
        if not path:
            return None
    # WARNING: Decompyle incomplete

    threading.Thread(worker, True, **('target', 'daemon')).start()


def load_local_config():
    ensure_data_dir()
    if not os.path.exists(LOCAL_CONFIG_PATH):
        return {
            'username': '',
            'password': '' }
    with open(LOCAL_CONFIG_PATH, 'r', 'utf-8', **('encoding',)) as f:
        data = json.load(f)
        None(None, None, None)
    with None:
        if not None:
            pass
    :
        ensure_data_dir()
        if not os.path.exists(LOCAL_CONFIG_PATH):
            return {
                'username': '',
                'password': '' }
        with open(LOCAL_CONFIG_PATH, 'r', 'utf-8', **('encoding',)) as f:
            data = json.load(f)
            None(None, None, None)
        with None:
            if not None:
                pass
        
        return {
            'username': data.get('username', ''),
            'password': data.get('password', '') }
    return {
        'username': data.get('username', ''),
        'password': data.get('password', '') }
# WARNING: Decompyle incomplete


def save_local_config(username = None, password = None):
    ensure_data_dir()
    with open(LOCAL_CONFIG_PATH, 'w', 'utf-8', **('encoding',)) as f:
        json.dump({
            'username': username,
            'password': password }, f, False, 2, **('ensure_ascii', 'indent'))
        None(None, None, None)
        return None
        with None:
            if not None:
                pass


def build_api_url(path = None):
    return urllib.parse.urljoin(SERVER_API_BASE.rstrip('/') + '/', path.lstrip('/'))


def build_sms_api_url(path = None):
    return urllib.parse.urljoin(SMS_API_BASE.rstrip('/') + '/', path.lstrip('/'))


def api_post_json(path = None, payload = None):
    url = build_api_url(path)
    data = json.dumps(payload, False, **('ensure_ascii',)).encode('utf-8')
    req = urllib.request.Request(url, data, {
        'Content-Type': 'application/json' }, 'POST', **('data', 'headers', 'method'))
    with urllib.request.urlopen(req, 20, **('timeout',)) as resp:
        None(None, None, None)
        return json.loads(resp.read().decode('utf-8', 'replace', **('errors',)))
        with None:
            if not None:
                pass


def api_get_json(path = None, params = None):
    url = build_api_url(path)
    if params:
        url = f'''{url}?{urllib.parse.urlencode(params)}'''
    req = urllib.request.Request(url, 'GET', **('method',))
    with urllib.request.urlopen(req, 20, **('timeout',)) as resp:
        None(None, None, None)
        return json.loads(resp.read().decode('utf-8', 'replace', **('errors',)))
        with None:
            if not None:
                pass


def sms_api_post(path = None, payload = None):
    '''短信API POST请求'''
    url = build_sms_api_url(path)
    if payload:
        data = json.dumps(payload, False, **('ensure_ascii',)).encode('utf-8')
        req = urllib.request.Request(url, data, {
            'Content-Type': 'application/json' }, 'POST', **('data', 'headers', 'method'))
    else:
        req = urllib.request.Request(url, 'POST', **('method',))
# WARNING: Decompyle incomplete


def sms_api_get(path = None):
    '''短信API GET请求'''
    url = build_sms_api_url(path)
    req = urllib.request.Request(url, 'GET', **('method',))
# WARNING: Decompyle incomplete


class ModernButton(tk.Button):
    '''现代化按钮样式'''
    
    def __init__(self = None, master = None, **kwargs):
        pass
    # WARNING: Decompyle incomplete

    
    def on_enter(self, e):
        if self.cget('state') != 'disabled':
            self.config(self._get_hover_color(), **('bg',))
            return None

    
    def on_leave(self, e):
        if self.cget('state') != 'disabled':
            self.config(self._default_bg, **('bg',))
            return None

    
    def _get_hover_color(self):
        bg = self._default_bg
        if bg.startswith('#'):
            r = int(bg[1:3], 16)
            g = int(bg[3:5], 16)
            b = int(bg[5:7], 16)
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f'''#{r:02x}{g:02x}{b:02x}'''

    __classcell__ = None


class ModernEntry(tk.Entry):
    '''现代化输入框样式'''
    
    def __init__(self = None, master = None, **kwargs):
        pass
    # WARNING: Decompyle incomplete

    __classcell__ = None


class App:
    
    def __init__(self = None, root = None):
        self.root = root
        self.root.geometry('440x480')
        self.center_window(440, 480)
        self.root.title('')
        self.set_window_icon(self.root)
        self.root.configure('#f1f5f9', **('bg',))
        self.root.minsize(400, 420)
        self.current_user = None
        self.current_password = ''
        self.table_rows = []
        self.balance_var = tk.StringVar('💰 余额：0.00元', **('value',))
        self.deduct_var = tk.StringVar('💎 单价：0.00元/次', **('value',))
        self.user_var = tk.StringVar('👤 用户：未登录', **('value',))
        self.result_dir = None
        self.refreshing_balance = False
        self.ensure_result_dir()
        self.edit_entry = None
        self.editing_row_index = None
        self.is_running = False
        self.stop_flag = False
        self.submit_btn = None
        self.waiting_for_code = False
        self.current_processing_index = -1
        self.code_event = threading.Event()
        self.pending_code = ''
        self.code_lock = threading.Lock()
        self.order_data = { }
        self.phone_entries = []
        self.code_entries = []
        self.status_labels = []
        self.get_sms_buttons = []
        self.build_login()

    
    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    
    def set_window_icon(self, window):
        pass
    # WARNING: Decompyle incomplete

    
    def center_window(self = None, width = None, height = None):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f'''{width}x{height}+{x}+{y}''')

    
    def center_toplevel(self = None, window = None, width = None, height = ('window', 'tk.Toplevel', 'width', 'int', 'height', 'int')):
        window.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        window.geometry(f'''{width}x{height}+{x}+{y}''')

    
    def build_login(self):
        self.clear()
        self.root.geometry('440x520')
        self.center_window(440, 520)
        self.root.title('')
        self.root.update_idletasks()
        container = tk.Frame(self.root, '#f1f5f9', **('bg',))
        container.pack(True, 'both', 50, 35, **('expand', 'fill', 'padx', 'pady'))
        title_frame = tk.Frame(container, '#f1f5f9', **('bg',))
        title_frame.pack('x', (0, 20), **('fill', 'pady'))
        tk.Label(title_frame, '请登录以继续使用', ('Microsoft YaHei', 11), '#64748b', '#f1f5f9', **('text', 'font', 'fg', 'bg')).pack((4, 0), **('pady',))
        tk.Frame(container, 2, '#e2e8f0', **('height', 'bg')).pack('x', (15, 20), **('fill', 'pady'))
        form_frame = tk.Frame(container, '#f1f5f9', **('bg',))
        form_frame.pack('x', 5, **('fill', 'pady'))
        local_config = load_local_config()
        saved_username = local_config.get('username', '').strip()
        saved_password = local_config.get('password', '').strip()
        tk.Label(form_frame, '👤 用户名', ('Microsoft YaHei', 11), '#475569', '#f1f5f9', **('text', 'font', 'fg', 'bg')).pack('w', (0, 5), **('anchor', 'pady'))
        self.username = ModernEntry(form_frame)
        self.username.pack('x', (0, 14), 4, **('fill', 'pady', 'ipady'))
        if not saved_username:
            pass
        self.username.insert(0, '请输入用户名')
        None(None, (lambda e = None: if self.username.get() == '请输入用户名':
self.username.delete(0, tk.END)))
        None(None, (lambda e = None: if self.username.get() == '':
self.username.insert(0, '请输入用户名')))
        tk.Label(form_frame, '🔒 密码', ('Microsoft YaHei', 11), '#475569', '#f1f5f9', **('text', 'font', 'fg', 'bg')).pack('w', (0, 5), **('anchor', 'pady'))
        self.password = ModernEntry(form_frame, '*', **('show',))
        self.password.pack('x', (0, 20), 4, **('fill', 'pady', 'ipady'))
        if not saved_password:
            pass
        self.password.insert(0, '请输入密码')
        None(None, (lambda e = None: if self.password.get() == '请输入密码':
self.password.delete(0, tk.END)))
        None(None, (lambda e = None: if self.password.get() == '':
self.password.insert(0, '请输入密码')))
        btn_frame = tk.Frame(form_frame, '#f1f5f9', **('bg',))
        btn_frame.pack('x', (5, 10), **('fill', 'pady'))
        self.login_btn = ModernButton(btn_frame, '登 录', '#6366f1', 'white', self.login, ('Microsoft YaHei', 12, 'bold'), 10, **('text', 'bg', 'fg', 'command', 'font', 'pady'))
        self.login_btn.pack('left', 'x', True, (0, 8), **('side', 'fill', 'expand', 'padx'))
        self.register_btn = ModernButton(btn_frame, '注 册', '#e2e8f0', '#475569', self.register, ('Microsoft YaHei', 12, 'bold'), 10, **('text', 'bg', 'fg', 'command', 'font', 'pady'))
        self.register_btn.pack('left', 'x', True, (8, 0), **('side', 'fill', 'expand', 'padx'))
        tip_frame = tk.Frame(container, '#f1f5f9', **('bg',))
        tip_frame.pack('x', (20, 0), **('fill', 'pady'))
        self.contact_link_label = tk.Label(tip_frame, '💡 点击联系客服', ('Microsoft YaHei', 10, 'underline'), '#2563eb', '#f1f5f9', 'hand2', **('text', 'font', 'fg', 'bg', 'cursor'))
        self.contact_link_label.pack()
        None(None, (lambda e = None: self.open_contact_link()))

    
    def build_home(self):
        self.clear()
        self.ensure_result_dir()
        self.root.geometry('560x460')
        self.center_window(560, 460)
        self.root.title('')
        self.root.minsize(560, 460)
        main_frame = tk.Frame(self.root, '#eef2f7', **('bg',))
        main_frame.pack('both', True, 10, 10, **('fill', 'expand', 'padx', 'pady'))
        top_bar = tk.Frame(main_frame, '#eef2f7', **('bg',))
        top_bar.pack('x', (0, 8), **('fill', 'pady'))
        info_box = tk.Frame(top_bar, '#f8fafc', '#cbd5e1', 1, 0, 260, 96, **('bg', 'highlightbackground', 'highlightthickness', 'bd', 'width', 'height'))
        info_box.pack('left', 'nw', **('side', 'anchor'))
        info_box.pack_propagate(False)
        info_inner = tk.Frame(info_box, '#f8fafc', **('bg',))
        info_inner.pack('both', True, 10, 8, **('fill', 'expand', 'padx', 'pady'))
        self.user_var.set(f'''👤 用户：{self.current_user}''')
        tk.Label(info_inner, self.user_var, ('Microsoft YaHei', 10, 'bold'), '#1e293b', '#f8fafc', 'w', **('textvariable', 'font', 'fg', 'bg', 'anchor')).pack('w', **('anchor',))
        tk.Label(info_inner, self.balance_var, ('Microsoft YaHei', 10, 'bold'), '#059669', '#f8fafc', 'w', **('textvariable', 'font', 'fg', 'bg', 'anchor')).pack('w', 6, **('anchor', 'pady'))
        tk.Label(info_inner, self.deduct_var, ('Microsoft YaHei', 10, 'bold'), '#6b7280', '#f8fafc', 'w', **('textvariable', 'font', 'fg', 'bg', 'anchor')).pack('w', **('anchor',))
        fill_box = tk.Frame(top_bar, '#f8fafc', '#cbd5e1', 1, 0, 620, 96, **('bg', 'highlightbackground', 'highlightthickness', 'bd', 'width', 'height'))
        fill_box.pack('right', 'nw', **('side', 'anchor'))
        fill_box.pack_propagate(False)
        fill_inner = tk.Frame(fill_box, '#f8fafc', **('bg',))
        fill_inner.pack('both', True, 10, 8, **('fill', 'expand', 'padx', 'pady'))
        tk.Label(fill_inner, '一键填入', ('Microsoft YaHei', 10, 'bold'), '#1e293b', '#f8fafc', 'w', **('text', 'font', 'fg', 'bg', 'anchor')).pack('w', **('anchor',))
        fill_content = tk.Frame(fill_inner, '#f8fafc', **('bg',))
        fill_content.pack('both', True, (4, 0), **('fill', 'expand', 'pady'))
        self.bulk_fill_text = tk.Text(fill_content, 3, 18, ('Microsoft YaHei', 9), tk.FLAT, 1, '#d1d5db', '#4f6ef7', '#ffffff', 'none', **('height', 'width', 'font', 'relief', 'highlightthickness', 'highlightbackground', 'highlightcolor', 'bg', 'wrap'))
        self.bulk_fill_text.pack('left', 'x', True, **('side', 'fill', 'expand'))
        ModernButton(fill_content, '一键填入', '#2563eb', 'white', self.bulk_fill_phone_entries, ('Microsoft YaHei', 9, 'bold'), 8, **('text', 'bg', 'fg', 'command', 'font', 'width')).pack('right', 'y', (10, 0), **('side', 'fill', 'padx'))
        row2_frame = tk.Frame(main_frame, '#eef2f7', **('bg',))
        row2_frame.pack('x', (0, 5), **('fill', 'pady'))
        self.clear_btn = ModernButton(row2_frame, '一键清屏', '#ef4444', 'white', self.clear_screen, ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        self.clear_btn.pack('left', (0, 5), **('side', 'padx'))
        self.balance_btn = ModernButton(row2_frame, '余额查询', '#8b5cf6', 'white', self.refresh_balance_async, ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        self.balance_btn.pack('left', (0, 5), **('side', 'padx'))
        self.current_dir_btn = ModernButton(row2_frame, '当前目录', '#14b8a6', 'white', self.open_current_dir, ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        self.current_dir_btn.pack('left', (0, 5), **('side', 'padx'))
        tk.Label(row2_frame, '手机区号：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).pack('left', (10, 3), **('side', 'padx'))
        self.area_code_entry = ModernEntry(row2_frame, 5, **('width',))
        self.area_code_entry.pack('left', (0, 10), **('side', 'padx'))
        self.area_code_entry.insert(0, '86')
        self.exit_btn = ModernButton(row2_frame, '🚪 退出登录', '#ef4444', 'white', self.build_login, ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        self.exit_btn.pack('right', **('side',))
        self.phone_entries = []
        self.code_entries = []
        self.status_labels = []
        self.get_sms_buttons = []
        row3_frame = tk.Frame(main_frame, '#eef2f7', **('bg',))
        row3_frame.pack('x', (0, 5), **('fill', 'pady'))
        row3_frame.grid_columnconfigure(0, 0, **('weight',))
        row3_frame.grid_columnconfigure(1, 0, **('weight',))
        row3_frame.grid_columnconfigure(2, 0, **('weight',))
        row3_frame.grid_columnconfigure(3, 0, **('weight',))
        row3_frame.grid_columnconfigure(4, 0, **('weight',))
        row3_frame.grid_columnconfigure(5, 0, **('weight',))
        row3_frame.grid_columnconfigure(6, 1, **('weight',))
        row3_frame.grid_columnconfigure(7, 0, **('weight',))
        tk.Label(row3_frame, '手机-1：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 0, 'w', **('row', 'column', 'sticky'))
        phone1 = ModernEntry(row3_frame, 22, **('width',))
        phone1.grid(0, 1, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        self.phone_entries.append(phone1)
        get_sms_btn1 = None(None, None, None, None, (lambda : self.get_sms_for_row(0)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        get_sms_btn1.grid(0, 2, (0, 8), 'w', **('row', 'column', 'padx', 'sticky'))
        self.get_sms_buttons.append(get_sms_btn1)
        self.submit_btn1 = None
        tk.Label(row3_frame, '验证码：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 3, (5, 3), 'w', **('row', 'column', 'padx', 'sticky'))
        code1 = ModernEntry(row3_frame, 14, **('width',))
        code1.grid(0, 4, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        None(None, (lambda e = None, r = None: self.submit_sms(r)))
        self.code_entries.append(code1)
        None(None, None, None, None, (lambda : self.submit_sms(0)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font')).grid(0, 7, (0, 0), 'e', **('row', 'column', 'padx', 'sticky'))
        tk.Label(row3_frame, '状态：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(1, 0, (0, 5), (6, 0), 'w', **('row', 'column', 'padx', 'pady', 'sticky'))
        status1 = tk.Label(row3_frame, '待处理', ('Microsoft YaHei', 9), '#6b7280', '#eef2f7', 'w', **('text', 'font', 'fg', 'bg', 'anchor'))
        status1.grid(1, 0, 8, (6, 0), 'we', **('row', 'column', 'columnspan', 'pady', 'sticky'))
        self.status_labels.append(status1)
        row4_frame = tk.Frame(main_frame, '#eef2f7', **('bg',))
        row4_frame.pack('x', (0, 5), **('fill', 'pady'))
        row4_frame.grid_columnconfigure(0, 0, **('weight',))
        row4_frame.grid_columnconfigure(1, 0, **('weight',))
        row4_frame.grid_columnconfigure(2, 0, **('weight',))
        row4_frame.grid_columnconfigure(3, 0, **('weight',))
        row4_frame.grid_columnconfigure(4, 0, **('weight',))
        row4_frame.grid_columnconfigure(5, 0, **('weight',))
        row4_frame.grid_columnconfigure(6, 1, **('weight',))
        row4_frame.grid_columnconfigure(7, 0, **('weight',))
        tk.Label(row4_frame, '手机-2：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 0, 'w', **('row', 'column', 'sticky'))
        phone2 = ModernEntry(row4_frame, 22, **('width',))
        phone2.grid(0, 1, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        self.phone_entries.append(phone2)
        get_sms_btn2 = None(None, None, None, None, (lambda : self.get_sms_for_row(1)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        get_sms_btn2.grid(0, 2, (0, 8), 'w', **('row', 'column', 'padx', 'sticky'))
        self.get_sms_buttons.append(get_sms_btn2)
        tk.Label(row4_frame, '验证码：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 3, (5, 3), 'w', **('row', 'column', 'padx', 'sticky'))
        code2 = ModernEntry(row4_frame, 14, **('width',))
        code2.grid(0, 4, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        None(None, (lambda e = None, r = None: self.submit_sms(r)))
        self.code_entries.append(code2)
        None(None, None, None, None, (lambda : self.submit_sms(1)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font')).grid(0, 7, (0, 0), 'e', **('row', 'column', 'padx', 'sticky'))
        tk.Label(row4_frame, '状态：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(1, 0, (0, 5), (6, 0), 'w', **('row', 'column', 'padx', 'pady', 'sticky'))
        status2 = tk.Label(row4_frame, '待处理', ('Microsoft YaHei', 9), '#6b7280', '#eef2f7', 'w', **('text', 'font', 'fg', 'bg', 'anchor'))
        status2.grid(1, 0, 8, (6, 0), 'we', **('row', 'column', 'columnspan', 'pady', 'sticky'))
        self.status_labels.append(status2)
        row5_frame = tk.Frame(main_frame, '#eef2f7', **('bg',))
        row5_frame.pack('x', (0, 5), **('fill', 'pady'))
        row5_frame.grid_columnconfigure(0, 0, **('weight',))
        row5_frame.grid_columnconfigure(1, 0, **('weight',))
        row5_frame.grid_columnconfigure(2, 0, **('weight',))
        row5_frame.grid_columnconfigure(3, 0, **('weight',))
        row5_frame.grid_columnconfigure(4, 0, **('weight',))
        row5_frame.grid_columnconfigure(5, 0, **('weight',))
        row5_frame.grid_columnconfigure(6, 1, **('weight',))
        row5_frame.grid_columnconfigure(7, 0, **('weight',))
        tk.Label(row5_frame, '手机-3：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 0, 'w', **('row', 'column', 'sticky'))
        phone3 = ModernEntry(row5_frame, 22, **('width',))
        phone3.grid(0, 1, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        self.phone_entries.append(phone3)
        get_sms_btn3 = None(None, None, None, None, (lambda : self.get_sms_for_row(2)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        get_sms_btn3.grid(0, 2, (0, 8), 'w', **('row', 'column', 'padx', 'sticky'))
        self.get_sms_buttons.append(get_sms_btn3)
        tk.Label(row5_frame, '验证码：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 3, (5, 3), 'w', **('row', 'column', 'padx', 'sticky'))
        code3 = ModernEntry(row5_frame, 14, **('width',))
        code3.grid(0, 4, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        None(None, (lambda e = None, r = None: self.submit_sms(r)))
        self.code_entries.append(code3)
        None(None, None, None, None, (lambda : self.submit_sms(2)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font')).grid(0, 7, (0, 0), 'e', **('row', 'column', 'padx', 'sticky'))
        tk.Label(row5_frame, '状态：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(1, 0, (0, 5), (6, 0), 'w', **('row', 'column', 'padx', 'pady', 'sticky'))
        status3 = tk.Label(row5_frame, '待处理', ('Microsoft YaHei', 9), '#6b7280', '#eef2f7', 'w', **('text', 'font', 'fg', 'bg', 'anchor'))
        status3.grid(1, 0, 8, (6, 0), 'we', **('row', 'column', 'columnspan', 'pady', 'sticky'))
        self.status_labels.append(status3)
        row6_frame = tk.Frame(main_frame, '#eef2f7', **('bg',))
        row6_frame.pack('x', (0, 5), **('fill', 'pady'))
        row6_frame.grid_columnconfigure(0, 0, **('weight',))
        row6_frame.grid_columnconfigure(1, 0, **('weight',))
        row6_frame.grid_columnconfigure(2, 0, **('weight',))
        row6_frame.grid_columnconfigure(3, 0, **('weight',))
        row6_frame.grid_columnconfigure(4, 0, **('weight',))
        row6_frame.grid_columnconfigure(5, 0, **('weight',))
        row6_frame.grid_columnconfigure(6, 1, **('weight',))
        row6_frame.grid_columnconfigure(7, 0, **('weight',))
        tk.Label(row6_frame, '手机-4：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 0, 'w', **('row', 'column', 'sticky'))
        phone4 = ModernEntry(row6_frame, 22, **('width',))
        phone4.grid(0, 1, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        self.phone_entries.append(phone4)
        get_sms_btn4 = None(None, None, None, None, (lambda : self.get_sms_for_row(3)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font'))
        get_sms_btn4.grid(0, 2, (0, 8), 'w', **('row', 'column', 'padx', 'sticky'))
        self.get_sms_buttons.append(get_sms_btn4)
        tk.Label(row6_frame, '验证码：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 3, (5, 3), 'w', **('row', 'column', 'padx', 'sticky'))
        code4 = ModernEntry(row6_frame, 14, **('width',))
        code4.grid(0, 4, (0, 8), 'we', **('row', 'column', 'padx', 'sticky'))
        None(None, (lambda e = None, r = None: self.submit_sms(r)))
        self.code_entries.append(code4)
        None(None, None, None, None, (lambda : self.submit_sms(3)), ('Microsoft YaHei', 9), **('text', 'bg', 'fg', 'command', 'font')).grid(0, 7, (0, 0), 'e', **('row', 'column', 'padx', 'sticky'))
        tk.Label(row6_frame, '状态：', ('Microsoft YaHei', 9), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(1, 0, (0, 5), (6, 0), 'w', **('row', 'column', 'padx', 'pady', 'sticky'))
        status4 = tk.Label(row6_frame, '待处理', ('Microsoft YaHei', 9), '#6b7280', '#eef2f7', 'w', **('text', 'font', 'fg', 'bg', 'anchor'))
        status4.grid(1, 0, 8, (6, 0), 'we', **('row', 'column', 'columnspan', 'pady', 'sticky'))
        self.status_labels.append(status4)
        row7_frame = tk.Frame(main_frame, '#eef2f7', **('bg',))
        row7_frame.pack('x', (0, 5), **('fill', 'pady'))
        row7_frame.grid_columnconfigure(0, 0, **('weight',))
        row7_frame.grid_columnconfigure(1, 1, **('weight',))
        row7_frame.grid_columnconfigure(2, 0, **('weight',))
        row7_frame.grid_columnconfigure(3, 0, **('weight',))
        tk.Label(row7_frame, '💳 卡密充值：', ('Microsoft YaHei', 9, 'bold'), '#374151', '#eef2f7', **('text', 'font', 'fg', 'bg')).grid(0, 0, 'w', (0, 5), **('row', 'column', 'sticky', 'padx'))
        self.recharge_entry = ModernEntry(row7_frame)
        self.recharge_entry.grid(0, 1, 'we', (0, 5), **('row', 'column', 'sticky', 'padx'))
        ModernButton(row7_frame, '立即充值', '#2563eb', 'white', self.do_recharge, ('Microsoft YaHei', 9), 15, **('text', 'bg', 'fg', 'command', 'font', 'padx')).grid(0, 2, 'w', (0, 5), **('row', 'column', 'sticky', 'padx'))
        self.recharge_tip = tk.Label(row7_frame, '', ('Microsoft YaHei', 8), '#6b7280', '#eef2f7', **('text', 'font', 'fg', 'bg'))
        self.recharge_tip.grid(0, 3, 'w', **('row', 'column', 'sticky'))
        bottom_frame = tk.Frame(main_frame, '#eef2f7', 18, **('bg', 'height'))
        bottom_frame.pack('x', (6, 0), **('fill', 'pady'))
        bottom_frame.pack_propagate(False)
        self.order_data = { }
        for i in range(4):
            self.order_data[i] = {
                'order_id': '',
                'phone': '',
                'status': '待处理',
                'polling': False,
                'stop_polling': False,
                'waiting_for_code': False,
                'submitted': False,
                'completed': False,
                'balance_deducted': False,
                'retry_count': 0,
                'recorded': False }
        self.user_var.set(f'''👤 用户：{self.current_user}''')
        self.set_all_buttons_state(False)
        self.root.after(100, self.refresh_balance)

    
    def ensure_result_dir(self):
        '''确保结果目录存在，每次登录创建新的时间戳目录'''
        if self.result_dir and os.path.isdir(self.result_dir):
            return self.result_dir
        None.makedirs(APP_DATA_DIR, True, **('exist_ok',))
        timestamp_dir = os.path.join(APP_DATA_DIR, datetime.now().strftime('%Y%m%d_%H%M%S'))
        os.makedirs(timestamp_dir, True, **('exist_ok',))
        self.result_dir = timestamp_dir
        return self.result_dir

    
    def open_current_dir(self):
        folder = self.ensure_result_dir()
    # WARNING: Decompyle incomplete

    
    def append_result_to_file(self = None, reason = None, row_data = None):
        '''将结果写入对应的txt文件'''
        folder = self.ensure_result_dir()
        safe_reason = ''.join((lambda .0: 