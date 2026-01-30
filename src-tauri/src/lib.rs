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
const DEFAULT_X: f64 = 100.0;
const DEFAULT_Y: f64 = 100.0;
const SHORTCUT_TOGGLE_RECORDING: &str = "toggle_recording";

#[derive(Debug, Serialize, Deserialize, Clone)]
struct WindowPosition {
    x: f64,
    y: f64,
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
        use tauri::Manager;

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
        use core_graphics::event::{CGEvent, CGEventType};
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

            // 注册全局快捷键 Option+F5
            let shortcut = Shortcut::new(Some(Modifiers::ALT), Code::F5);
            let app_handle = app.handle().clone();
            app.global_shortcut().on_shortcut(shortcut, move |_app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    let _ = app_handle.emit(SHORTCUT_TOGGLE_RECORDING, ());
                }
            })?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet, save_window_position, load_window_position, set_window_bounds, set_ignore_cursor_events, get_cursor_position])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
