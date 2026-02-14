// 允许使用 cocoa crate 的 deprecated API（迁移到 objc2 需要较大改动）
#![allow(deprecated)]

use std::sync::Mutex;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use tauri_plugin_store::StoreExt;
use serde::{Deserialize, Serialize};

#[cfg(target_os = "macos")]
use objc::msg_send;
#[cfg(target_os = "macos")]
use objc::sel;
#[cfg(target_os = "macos")]
use objc::sel_impl;

const STORE_PATH: &str = "settings.json";
const WINDOW_POSITION_KEY: &str = "window_position";
const SHORTCUTS_KEY: &str = "shortcuts";
const DEFAULT_X: f64 = 100.0;
const DEFAULT_Y: f64 = 100.0;
const SHORTCUT_TOGGLE_RECORDING: &str = "toggle_recording";

/// Global state for managing the backend sidecar process
struct SidecarState {
    child: Mutex<Option<CommandChild>>,
}

/// Global state for backend port
struct PortState {
    port: Mutex<u16>,
}

fn find_available_port() -> Result<u16, std::io::Error> {
    let listener = std::net::TcpListener::bind("127.0.0.1:0")?;
    let port = listener.local_addr()?.port();
    drop(listener);
    Ok(port)
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct WindowPosition {
    x: f64,
    y: f64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct ShortcutConfig {
    modifiers: Vec<String>,  // ["Alt"], ["Ctrl", "Shift"]
    key: String,             // "F5", "A"
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
struct ShortcutsSettings {
    toggle_recording: Option<ShortcutConfig>,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Yap.", name)
}

#[tauri::command]
fn get_backend_port(state: tauri::State<PortState>) -> u16 {
    *state.port.lock().unwrap()
}

#[tauri::command]
fn save_window_position(app: tauri::AppHandle, x: f64, y: f64) -> Result<(), String> {
    let store = app.store(STORE_PATH).map_err(|e| e.to_string())?;
    let pos = WindowPosition { x, y };
    store.set(WINDOW_POSITION_KEY, serde_json::to_value(pos).unwrap());
    store.save().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn load_window_position(app: tauri::AppHandle) -> WindowPosition {
    let store = match app.store(STORE_PATH) {
        Ok(s) => s,
        Err(_) => return WindowPosition { x: DEFAULT_X, y: DEFAULT_Y },
    };

    match store.get(WINDOW_POSITION_KEY) {
        Some(value) => serde_json::from_value(value.clone()).unwrap_or(WindowPosition { x: DEFAULT_X, y: DEFAULT_Y }),
        None => WindowPosition { x: DEFAULT_X, y: DEFAULT_Y },
    }
}

/// 原子操作：同时设置窗口大小和位置，减少闪烁
#[tauri::command]
fn set_window_bounds(window: tauri::Window, x: f64, y: f64, width: f64, height: f64) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        use cocoa::foundation::{NSPoint, NSRect, NSSize};

        let ns_window = window.ns_window().map_err(|e| e.to_string())?;
        let ns_window = ns_window as cocoa::base::id;

        unsafe {
            // 获取屏幕高度用于坐标转换（macOS 坐标系原点在左下角）
            let screen: cocoa::base::id = msg_send![ns_window, screen];
            let screen_frame: NSRect = msg_send![screen, frame];
            let screen_height = screen_frame.size.height;

            // 转换坐标：Tauri 使用左上角原点，macOS 使用左下角原点
            let flipped_y = screen_height - y - height;

            let frame = NSRect::new(
                NSPoint::new(x, flipped_y),
                NSSize::new(width, height)
            );

            // setFrame:display:animate: 一次性设置位置和大小
            // display:false 避免立即重绘，animate:false 禁用动画
            let _: () = msg_send![ns_window, setFrame:frame display:false animate:false];
        }
        Ok(())
    }
    #[cfg(not(target_os = "macos"))]
    {
        use tauri::{LogicalPosition, LogicalSize};
        window.set_size(LogicalSize::new(width, height)).map_err(|e| e.to_string())?;
        window.set_position(LogicalPosition::new(x, y)).map_err(|e| e.to_string())?;
        Ok(())
    }
}

/// 设置窗口是否忽略鼠标事件（点击穿透）
#[tauri::command]
fn set_ignore_cursor_events(window: tauri::Window, ignore: bool) -> Result<(), String> {
    window.set_ignore_cursor_events(ignore).map_err(|e| e.to_string())
}

/// 获取全局鼠标位置
#[tauri::command]
fn get_cursor_position() -> Result<WindowPosition, String> {
    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::CGEvent;
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};

        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
            .map_err(|_| "Failed to create event source")?;
        let event = CGEvent::new(source)
            .map_err(|_| "Failed to create event")?;
        let point = event.location();
        Ok(WindowPosition { x: point.x, y: point.y })
    }
    #[cfg(not(target_os = "macos"))]
    {
        Err("Not supported on this platform".to_string())
    }
}

/// 打开设置窗口
#[tauri::command]
fn open_settings_window(app: tauri::AppHandle) -> Result<(), String> {
    // 如果窗口已存在，显示并聚焦
    if let Some(window) = app.get_webview_window("settings") {
        #[cfg(target_os = "macos")]
        {
            let _ = window.set_shadow(false);
        }
        window.show().map_err(|e| e.to_string())?;
        window.center().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }

    // 动态创建设置窗口
    let settings_window = tauri::WebviewWindowBuilder::new(
        &app,
        "settings",
        tauri::WebviewUrl::App("settings.html".into()),
    )
    .title("Settings")
    .inner_size(568.0, 448.0)
    .min_inner_size(568.0, 448.0)
    .resizable(true)
    .center()
    .decorations(false)
    .transparent(true)
    .build()
    .map_err(|e| e.to_string())?;

    #[cfg(target_os = "macos")]
    {
        let _ = settings_window.set_shadow(false);
    }

    settings_window.set_focus().map_err(|e| e.to_string())?;
    Ok(())
}

/// 关闭设置窗口（隐藏而非销毁）
#[tauri::command]
fn close_settings_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("settings") {
        window.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// 广播设置变更事件到所有窗口
#[tauri::command]
fn broadcast_settings_changed(app: tauri::AppHandle, settings: serde_json::Value) -> Result<(), String> {
    app.emit("settings-changed", settings).map_err(|e| e.to_string())
}

/// 打开开发者工具
#[tauri::command]
fn open_devtools(webview_window: tauri::WebviewWindow) {
    webview_window.open_devtools();
}

/// 复制文本到剪贴板
#[tauri::command]
fn copy_to_clipboard(app: tauri::AppHandle, text: String) -> Result<(), String> {
    use tauri_plugin_clipboard_manager::ClipboardExt;
    app.clipboard()
        .write_text(text)
        .map_err(|e| format!("Failed to copy to clipboard: {}", e))
}

/// 模拟键盘输入文本（macOS）
#[tauri::command]
fn input_text(text: String, typewriter: Option<bool>) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::{CGEvent, CGEventTapLocation};
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};

        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
            .map_err(|_| "Failed to create event source")?;

        let use_typewriter = typewriter.unwrap_or(true);

        for ch in text.chars() {
            let event = CGEvent::new_keyboard_event(source.clone(), 0, true)
                .map_err(|_| "Failed to create keyboard event")?;

            // Encode char to UTF-16 (max 2 code units for surrogate pairs)
            let mut buf = [0u16; 2];
            let encoded = ch.encode_utf16(&mut buf);
            event.set_string_from_utf16_unchecked(encoded);
            event.post(CGEventTapLocation::HID);

            let event_up = CGEvent::new_keyboard_event(source.clone(), 0, false)
                .map_err(|_| "Failed to create key up event")?;
            event_up.post(CGEventTapLocation::HID);

            if use_typewriter {
                std::thread::sleep(std::time::Duration::from_millis(16));
            }
        }
        Ok(())
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = text;
        let _ = typewriter;
        Err("Text input not supported on this platform".to_string())
    }
}

/// 解析修饰键字符串为 Modifiers
fn parse_modifiers(modifiers: &[String]) -> Modifiers {
    let mut result = Modifiers::empty();
    for m in modifiers {
        match m.to_uppercase().as_str() {
            "ALT" | "OPTION" => result |= Modifiers::ALT,
            "CTRL" | "CONTROL" => result |= Modifiers::CONTROL,
            "SHIFT" => result |= Modifiers::SHIFT,
            "META" | "SUPER" | "CMD" | "COMMAND" => result |= Modifiers::META,
            _ => {}
        }
    }
    result
}

/// 解析按键字符串为 Code
fn parse_key(key: &str) -> Option<Code> {
    match key.to_uppercase().as_str() {
        "F1" => Some(Code::F1),
        "F2" => Some(Code::F2),
        "F3" => Some(Code::F3),
        "F4" => Some(Code::F4),
        "F5" => Some(Code::F5),
        "F6" => Some(Code::F6),
        "F7" => Some(Code::F7),
        "F8" => Some(Code::F8),
        "F9" => Some(Code::F9),
        "F10" => Some(Code::F10),
        "F11" => Some(Code::F11),
        "F12" => Some(Code::F12),
        "A" => Some(Code::KeyA),
        "B" => Some(Code::KeyB),
        "C" => Some(Code::KeyC),
        "D" => Some(Code::KeyD),
        "E" => Some(Code::KeyE),
        "F" => Some(Code::KeyF),
        "G" => Some(Code::KeyG),
        "H" => Some(Code::KeyH),
        "I" => Some(Code::KeyI),
        "J" => Some(Code::KeyJ),
        "K" => Some(Code::KeyK),
        "L" => Some(Code::KeyL),
        "M" => Some(Code::KeyM),
        "N" => Some(Code::KeyN),
        "O" => Some(Code::KeyO),
        "P" => Some(Code::KeyP),
        "Q" => Some(Code::KeyQ),
        "R" => Some(Code::KeyR),
        "S" => Some(Code::KeyS),
        "T" => Some(Code::KeyT),
        "U" => Some(Code::KeyU),
        "V" => Some(Code::KeyV),
        "W" => Some(Code::KeyW),
        "X" => Some(Code::KeyX),
        "Y" => Some(Code::KeyY),
        "Z" => Some(Code::KeyZ),
        _ => None,
    }
}

/// 获取快捷键设置
#[tauri::command]
fn get_shortcut_settings(app: tauri::AppHandle) -> ShortcutsSettings {
    let store = match app.store(STORE_PATH) {
        Ok(s) => s,
        Err(_) => return ShortcutsSettings::default(),
    };

    match store.get(SHORTCUTS_KEY) {
        Some(value) => serde_json::from_value(value.clone()).unwrap_or_default(),
        None => ShortcutsSettings::default(),
    }
}

/// 更新快捷键
#[tauri::command]
fn update_shortcut(app: tauri::AppHandle, modifiers: Vec<String>, key: String) -> Result<(), String> {
    // 解析新快捷键
    let mods = parse_modifiers(&modifiers);
    let code = parse_key(&key).ok_or("Invalid key")?;
    let new_shortcut = Shortcut::new(Some(mods), code);

    // 注销所有现有快捷键
    let global_shortcut = app.global_shortcut();
    global_shortcut.unregister_all().map_err(|e| e.to_string())?;

    // 注册新快捷键
    let app_handle = app.clone();
    global_shortcut.on_shortcut(new_shortcut, move |_app, _shortcut, event| {
        if event.state == ShortcutState::Pressed {
            let _ = app_handle.emit(SHORTCUT_TOGGLE_RECORDING, ());
        }
    }).map_err(|e| e.to_string())?;

    // 保存到 store
    let store = app.store(STORE_PATH).map_err(|e| e.to_string())?;
    let config = ShortcutConfig { modifiers, key };
    let settings = ShortcutsSettings { toggle_recording: Some(config) };
    store.set(SHORTCUTS_KEY, serde_json::to_value(settings).unwrap());
    store.save().map_err(|e| e.to_string())?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_clipboard_manager::init())
        .manage(SidecarState {
            child: Mutex::new(None),
        })
        .manage(PortState {
            port: Mutex::new(8765),
        })
        .setup(|app| {
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let show = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "quit" => {
                        app.exit(0);
                    }
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            #[cfg(target_os = "macos")]
            {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.set_shadow(false);
                }
            }

            // Determine backend port: use 8765 in dev, find available port in production
            let port: u16 = if cfg!(debug_assertions) {
                8765
            } else {
                find_available_port().unwrap_or(8765)
            };
            log::info!("Backend port: {}", port);

            // Update PortState with the determined port
            *app.state::<PortState>().port.lock().unwrap() = port;

            // Start backend sidecar from resources directory
            let resource_path = app.path().resource_dir()
                .map_err(|e| format!("Failed to get resource dir: {}", e))?;
            let sidecar_path = resource_path.join("vocistant-backend");

            log::info!("Starting backend sidecar from: {:?}", sidecar_path);

            let (mut rx, child) = app.shell().command(&sidecar_path)
                .env("VOCISTANT_PORT", port.to_string())
                .spawn()
                .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

            log::info!("Backend sidecar started with PID: {}", child.pid());

            // Store the child process handle
            let state = app.state::<SidecarState>();
            *state.child.lock().unwrap() = Some(child);

            // Spawn a task to handle sidecar output
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            log::info!("[backend] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Stderr(line) => {
                            log::warn!("[backend] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Terminated(payload) => {
                            log::info!("[backend] Process terminated: {:?}", payload);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            // 从 store 读取快捷键配置，如果没有则使用默认值 Alt+F5
            let store = app.store(STORE_PATH)?;
            let shortcuts_settings: ShortcutsSettings = store
                .get(SHORTCUTS_KEY)
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();

            let (mods, code) = if let Some(config) = shortcuts_settings.toggle_recording {
                (parse_modifiers(&config.modifiers), parse_key(&config.key).unwrap_or(Code::F5))
            } else {
                (Modifiers::ALT, Code::F5)
            };

            let shortcut = Shortcut::new(Some(mods), code);
            let app_handle = app.handle().clone();
            app.global_shortcut().on_shortcut(shortcut, move |_app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    let _ = app_handle.emit(SHORTCUT_TOGGLE_RECORDING, ());
                }
            })?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet, get_backend_port, save_window_position, load_window_position, set_window_bounds, set_ignore_cursor_events, get_cursor_position, open_settings_window, close_settings_window, broadcast_settings_changed, get_shortcut_settings, update_shortcut, open_devtools, input_text, copy_to_clipboard])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                // Kill the backend sidecar process on exit
                let state = app.state::<SidecarState>();
                let child = state.child.lock().unwrap().take();
                if let Some(child) = child {
                    log::info!("Killing backend sidecar process...");
                    let _ = child.kill();
                }
            }
        });
}
