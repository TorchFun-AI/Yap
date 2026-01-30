## 悬浮球产品 UI 设计规范

### 1. 核心视觉理念 (Visual Concept)

* **风格定义：** 玻璃拟态 (Glassmorphism) 结合深色模式。
* **物理隐喻：** 半透明磨砂材质，通过多重投影与内发光营造多维层级感。
* **品牌色：** 科技蓝 `Hex #4A90E2`，用于激活态与视觉引导。

---

### 2. 结构层级 (Layer Hierarchy)

1. **Level 4 - 提示层 (Tooltip)：** 顶层信息，深色半透明，引导用户操作。
2. **Level 3 - 主按钮 (Primary Trigger)：** 视觉锚点，高对比度，叠加于面板之上。
3. **Level 2 - 功能图标 (Action Icons)：** 交互元素，等距排列，具备 Hover/Active 反馈态。
4. **Level 1 - 磨砂底座 (Base Panel)：** 容器层，胶囊形结构，集成背景模糊 (Backdrop Blur)。

---

### 3. 尺寸与间距 (Sizing & Spacing)

* **主按钮直径：** `56dp`
* **面板高度：** `56dp`
* **面板圆角：** `28dp` (高度的 )
* **功能图标尺寸：** `24dp x 24dp`
* **图标点击热区：** `40dp x 40dp`
* **元素间距：** 图标间距 `12dp`，面板右侧内边距 `16dp`。
* **提示层偏移：** 距离面板顶部 `8dp`。

---

### 4. 材质与属性 (Materials & Effects)

#### 容器面板 (Base Panel)

* **背景：** `RGBA(45, 45, 48, 0.85)`
* **背景模糊：** `Backdrop Blur: 25px`
* **描边 (Border)：** `1px solid RGBA(255, 255, 255, 0.08)`
* **外阴影：** `Drop Shadow: 0 10px 30px RGBA(0, 0, 0, 0.4)`

#### 主按钮 (Primary Trigger)

* **背景：** `Linear-Gradient(180deg, #2C2C2E 0%, #1C1C1E 100%)`
* **强调轮廓：** `2px solid #4A90E2`
* **外发光：** `Box-shadow: 0 0 12px RGBA(74, 144, 226, 0.5)`

#### 提示标签 (Tooltip)

* **背景：** `RGBA(30, 30, 30, 0.95)`
* **圆角：** `6dp`
* **字体：** `Size: 12px`, `Weight: Medium`, `Color: #FFFFFF`

---

### 5. 交互状态 (State Definitions)

* **Default (常规)：** 仅显示主按钮，轻微呼吸灯特效。
* **Expanded (展开)：** 容器横向滑出，背景呈现高斯模糊覆盖下方内容。
* **Hover/Pressed (悬停/按下)：** 图标背景出现 `RGBA(255, 255, 255, 0.1)` 的圆形遮罩，缩放比例 `0.95`。

---

### 6. 动效规范 (Motion)

* **面板展开：** 长度变化配合 `Cubic-bezier(0.34, 1.56, 0.64, 1)` (弹性过渡)。
* **入场时长：** `300ms`
* **图标出现：** 顺序淡入 (Stagger animation)，每个图标间隔 `50ms`。
