# DynamicVoiceChannel Bot 🎙️

一個基於 [py-cord](https://github.com/Pycord-Development/pycord) 開發的 Discord 機器人，專為提升語音社群互動性與管理效率而設計。具備動態語音頻道管理、高度自訂的猜歌遊戲以及自動化社群輔助功能。

---

## 🚀 主要功能

### 1. 動態語音頻道 (Dynamic Voice Channels)
*   **自動創建**：使用者進入指定的「點我創建」頻道後，機器人會自動建立專屬語音頻道並將成員移入。
*   **自動清理**：當動態頻道內最後一名成員離開時，機器人會自動刪除頻道以保持伺服器整潔。
*   **權限管理系統**：
    *   `/rename`：更改頻道名稱（僅限擁有者與管理員）。
    *   `/add_manager` / `/remove_manager`：管理頻道的協作管理員。
    *   `/transfer`：將頻道所有權轉移給他人。
    *   `/info`：查看目前動態頻道的擁有者與詳細資訊。

### 2. 猜歌挑戰遊戲 (Music Guess Game)
*   **靈活題庫**：支援單一藝人挑戰或「綜合挑戰」（隨機從所有 `songs/` JSON 中選題）。
*   **YouTube 整合**：透過 `yt-dlp` 進行背景串流播放，支援自訂起始時間與別名匹配。
*   **智慧回答**：搭配 `/answer` 指令與 Discord Autocomplete 功能，讓回答更流暢。

### 3. 社群輔助與管理
*   **連結修復**：自動偵測指定頻道中的 Twitter/X 連結，並轉換為 `fixvx.com` 以提供更好的 Discord 預覽。
*   **自動踢除**：自動偵測並踢除帶有特定惡意身分組 ID 的使用者，保護伺服器安全。

---

## 🛠️ 安裝與設定

本專案支援 **[uv](https://github.com/astral-sh/uv)**，這是一個極速的 Python 套件管理工具。

### 1. 安裝環境
確保你的系統已安裝 **FFmpeg**（語音播放核心需求）。

#### 使用 uv (推薦)
```bash
# 安裝依賴
uv sync

# 啟動機器人
uv run main.py
```

#### 使用傳統 pip
```bash
pip install -r requirements.txt
python main.py
```

### 2. 配置檔案

#### `.env`
在根目錄建立 `.env` 檔案：
```env
TOKEN=你的_DISCORD_BOT_TOKEN
```

#### `voice_channel.json`
設定動態頻道的「母頻道」：
```json
{
    "creator_channel_id": 1234567890,  // 「點我創建」頻道的 ID
    "dynamic_channels": {}             // 保持預設，機器人會自動維護此處資料
}
```

#### `songs/` 題庫格式
在 `songs/` 資料夾下新增 JSON 檔案（例如 `example.json`）：
```json
{
  "singer": "歌手名稱",
  "songs": [
    {
      "title": "歌曲名稱",
      "url": "YouTube 網址",
      "aliases": ["別名1", "別名2"],
      "start_time": 30
    }
  ]
}
```

---

## 📜 指令清單

| 指令 | 描述 |
| :--- | :--- |
| `/info` | 顯示目前所在動態頻道的資訊 |
| `/rename` | [擁有者/管理員] 重新命名頻道 |
| `/add_manager` | [擁有者] 新增一位頻道管理員 |
| `/remove_manager` | [擁有者] 移除一位頻道管理員 |
| `/transfer` | [擁有者] 將頻道擁有權完全轉移 |
| `/guess` | 開始猜歌挑戰 |
| `/answer` | 回答猜歌答案 |

---

## 📄 授權條款
本專案採 [CC BY-NC 4.0 (姓名標示-非商業性 4.0 國際)](LICENSE) 授權。
*   **姓名標示**：必須指明原作者姓名。
*   **非商業性**：不得將本軟體用於商業目的。
*   **無擔保與免責**：本軟體按「現狀」提供，作者不負擔任何風險賠償。
