// 允许使用 cocoa crate 的 deprecated API（迁移到 objc2 需要较大改动）
#![allow(deprecated)]

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
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
    format!("Hello, {}! Welcome to Vocistant.", name)
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
    .inner_size(560.0, 440.0)
    .resizable(false)
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
fn broadcast_settings_changed(app: tauri::AppHandle) -> Result<(), String> {
    app.emit("settings-changed", ()).map_err(|e| e.to_string())
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
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
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
        .invoke_handler(tauri::generate_handler![greet, save_window_position, load_window_position, set_window_bounds, set_ignore_cursor_events, get_cursor_position, open_settings_window, close_settings_window, broadcast_settings_changed, get_shortcut_settings, update_shortcut])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
