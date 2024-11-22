# CloudreveDownloader

CloudreveDownloader 是一个旨在改进 Cloudreve 官方打包下载功能较差问题的工具。通过利用 `aria2c` 实现高效并行下载，提供更强大的批量下载体验。

## 项目背景

Cloudreve 是一个开源的云存储系统，但其官方的打包下载功能在实际使用中可能会出现效率低下、不稳定等问题。CloudreveDownloader 致力于解决这些痛点，提供以下改进功能：

- **自动化解析**：无需手动操作即可获取文件列表及下载链接。
- **批量并行下载**：通过 `aria2c` 实现高效的多线程并行下载。
- **智能缓存**：避免重复请求，提高下载效率。
- **实时监控**：可视化监控下载进度，了解当前任务完成情况。

---

## 功能特性

1. **支持从分享链接批量下载：**
   - 自动解析 Cloudreve 分享链接中的文件列表和下载链接。
   - 按需设置下载目录和并发任务数。

2. **缓存机制：**
   - 利用本地缓存保存文件元数据和下载链接，减少 API 请求。
   - 再次运行时可直接使用缓存，加快下载启动速度。

3. **高效的并发下载：**
   - 基于 `aria2c` 的高效下载工具，支持多线程并发下载。
   - 可设置最大并发数，优化带宽使用。

4. **下载进度实时监控：**
   - 每隔 15 秒更新一次总进度，显示完成的文件数量、已下载的大小和总进度百分比。

5. **自动启动 aria2c：**
   - 自动检测本地是否运行 `aria2c`，如果未运行会自动启动。

6. **日志记录：**
   - 自动记录下载和运行状态，便于排查问题。

---

## 环境要求

- **Python**：3.8 或更高版本。
- **aria2c**：需要安装 `aria2c` 并将其路径添加到系统环境变量中。

---

## 安装步骤

### 1. 克隆项目代码

```bash
git clone https://github.com/Daofengql/CloudreveDownloader.git
cd CloudreveDownloader
```

### 2. 安装依赖

使用 `pip` 安装依赖：
```bash
pip install -r requirements.txt
```

### 3. 安装并配置 `aria2c`

- 从 [aria2c 官方页面](https://github.com/aria2/aria2/releases) 下载并安装。
- 确保 `aria2c` 的路径已添加到系统的环境变量中。

验证安装是否成功：
```bash
aria2c --version
```

---

## 使用方法

### 基本命令
```bash
python main.py <share_url> [-d 下载目录] [-n 最大并发下载数]
```

### 参数说明
1. **`<share_url>`**：分享链接，必填参数，例如 `https://demo.cloudreve.org/s/Asdf`。
2. **`-d, --download-root`**：指定下载保存的目录，默认为当前目录下的 `./download`。
3. **`-n, --max-concurrent-downloads`**：设置最大并发下载任务数，默认为 `10`。

### 示例

1. 下载分享链接中的文件，使用默认下载目录：
   ```bash
   python main.py "https://demo.cloudreve.org/s/Asdf"
   ```

2. 自定义下载目录为 `./my_downloads`：
   ```bash
   python main.py "https://demo.cloudreve.org/s/Asdf" -d "./my_downloads"
   ```

3. 将最大并发下载数设置为 5：
   ```bash
   python main.py "https://demo.cloudreve.org/s/Asdf" -n 5
   ```

---

## 工作原理

1. **解析分享链接：**
   - 从分享链接中提取基础 URL 和分享码。

2. **获取文件元数据：**
   - 通过 Cloudreve API 递归获取分享链接中的文件路径和大小。

3. **缓存机制：**
   - 利用缓存保存文件列表和下载链接，避免重复请求，提高效率。

4. **下载文件：**
   - 使用 `aria2c` 下载文件，并通过 `aria2p` 与其交互，实时更新任务状态。

5. **监控总进度：**
   - 每隔 15 秒更新下载进度，包括：
     - 已完成文件数量。
     - 已下载总大小。
     - 总进度百分比。

6. **自动清理：**
   - 下载完成后清理临时缓存文件。

---

## 日志记录

- **日志位置：** 默认保存到 `./download.log`。
- **日志特性：**
  - 支持文件大小轮转（单个日志文件最大 10 MB）。
  - 自动记录运行状态、错误信息及进度更新。


---

## 常见问题

1. **`aria2c` 启动失败**
   - 检查是否已安装 `aria2c`，并将其路径添加到系统的环境变量中。
   - 验证安装：
     ```bash
     aria2c --version
     ```

2. **分享链接无法解析**
   - 确保提供的分享链接正确且未过期。
   - 检查是否能通过浏览器正常访问链接。

3. **下载速度慢**
   - 调整并发下载任务数（`-n` 参数）。
   - 检查网络环境是否稳定。

4. **缓存数据问题**
   - 如果出现缓存问题，可手动清理 `cache` 目录。

---

## 贡献指南

欢迎对本项目提出改进建议或提交代码贡献！

### 如何贡献

1. Fork 本项目。
2. 创建一个新的分支：
   ```bash
   git checkout -b feature/your-feature
   ```
3. 提交代码改动：
   ```bash
   git commit -m "Add your feature description"
   ```
4. Push 到你的仓库：
   ```bash
   git push origin feature/your-feature
   ```
5. 提交 Pull Request。

---

## 开源许可

本项目使用 [Apache 2.0 许可证](./LICENSE)。

---

## 联系方式

如有任何疑问或建议，请通过以下方式联系：
- 提交 [GitHub Issues](https://github.com/Daofengql/CloudreveDownloader/issues)
- 通过电子邮件联系项目维护者。

感谢您对 CloudreveDownloader 的关注和支持！
