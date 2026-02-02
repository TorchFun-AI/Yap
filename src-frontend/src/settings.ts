import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './style.css'
import SettingsWindow from './SettingsWindow.vue'
import i18n from './i18n'

const app = createApp(SettingsWindow)
const pinia = createPinia()

app.use(pinia)
app.use(Antd)
app.use(i18n)
app.mount('#app')
