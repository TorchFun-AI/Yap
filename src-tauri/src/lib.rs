use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use tauri_plugin_store::StoreExt;
use serde::{Deserialize, Serialize};

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
        .invoke_handler(tauri::generate_handler![greet, save_window_position, load_window_position])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
