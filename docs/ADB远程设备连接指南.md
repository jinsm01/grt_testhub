# ADB 远程设备连接指南

本文档介绍如何通过 WiFi 无线连接 Android 设备进行自动化测试。

## 前提条件

- 一台 Android 设备（手机/平板/模拟器）
- USB 数据线（仅初始配置需要）
- macOS / Windows / Linux 系统
- 设备和电脑在同一局域网内

---

## 一、安装 ADB 工具

### macOS

#### 方法 1：使用 Homebrew（推荐）

```bash
brew install android-platform-tools
```

#### 方法 2：手动安装

```bash
# 下载
cd ~/Downloads
curl -O https://dl.google.com/android/repository/platform-tools-latest-darwin.zip
unzip platform-tools-latest-darwin.zip

# 移动到系统目录
sudo mv platform-tools /usr/local/

# 添加到 PATH
echo 'export PATH=$PATH:/usr/local/platform-tools' >> ~/.zshrc
source ~/.zshrc
```

### Windows

1. 下载 [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. 解压到 `C:\platform-tools`
3. 添加到系统环境变量 PATH

### Linux

```bash
sudo apt-get install android-tools-adb
```

### 验证安装

```bash
adb version
```

---

## 二、开启设备开发者选项

### 步骤

1. 打开 Android 设备的 **设置**
2. 找到 **关于手机**（或 关于设备）
3. 连续点击 **版本号** 7 次，直到提示"您已处于开发者模式"
4. 返回设置，找到 **开发者选项**
5. 开启 **USB 调试**
6. （可选）开启 **USB 安装** 和 **USB 调试（安全设置）**

---

## 三、USB 连接与授权

### 1. 连接设备

使用 USB 数据线连接设备和电脑。

### 2. 授权调试

- 设备上会弹出 **"允许 USB 调试吗？"** 对话框
- 勾选 **"始终允许来自此计算机"**
- 点击 **"允许"**

### 3. 验证连接

```bash
adb devices
```

正常输出：
```
List of devices attached
12345678    device
```

如果显示 `unauthorized`：
- 检查设备上是否有授权弹窗
- 执行 `adb kill-server` 后重试
- 断开 USB 重新连接

---

## 四、开启网络 ADB

### 1. 执行命令

保持 USB 连接，执行：

```bash
adb tcpip 5555
```

成功输出：
```
restarting in TCP mode port: 5555
```

### 2. 获取设备 IP 地址

**方法 A：在设备上查看**
- 设置 → WLAN → 点击已连接网络 → 查看 IP 地址

**方法 B：通过 ADB 获取**
```bash
adb shell ip addr show wlan0 | grep 'inet '
```

假设获取到 IP：`192.168.1.100`

### 3. 测试网络连接（可选）

```bash
adb connect 192.168.1.100:5555
```

成功输出：
```
connected to 192.168.1.100:5555
```

---

## 五、在平台上添加远程设备

### 步骤

1. 访问 **设备管理** 页面
   - URL: `http://localhost:3000/app-automation/devices`

2. 点击 **"添加远程设备"** 按钮

3. 填写信息：
   | 字段 | 值 |
   |------|------|
   | IP地址 | `192.168.1.100`（您的设备实际 IP） |
   | 端口 | `5555` |

4. 点击 **"连接"**

5. 连接成功后，设备会显示在设备列表中

---

## 六、断开 USB

连接成功后，**可以拔掉 USB 数据线**，设备将通过 WiFi 无线连接。

---

## 常见问题

### Q1: 设备重启后无法连接？

设备重启后，网络 ADB 会关闭，需要重新开启：

1. 用 USB 数据线连接设备
2. 执行 `adb tcpip 5555`
3. 在平台上重新连接

### Q2: 连接中断怎么办？

检查：
- 设备和电脑是否在同一局域网
- 设备 IP 是否变化
- WiFi 是否稳定

重新连接：
```bash
adb connect 192.168.1.100:5555
```

### Q3: 如何查看已连接的设备？

```bash
adb devices
```

### Q4: 如何断开远程设备？

```bash
adb disconnect 192.168.1.100:5555
```

### Q5: ADB 授权失败？

尝试：
```bash
# 重启 ADB 服务
adb kill-server
adb start-server

# 重新连接设备
adb devices
```

在设备上撤销所有 USB 调试授权后重新连接。

### Q6: 端口被占用？

尝试其他端口：
```bash
adb tcpip 6666
```

然后在平台上使用端口 `6666` 连接。

---

## 快速参考

| 命令 | 说明 |
|------|------|
| `adb version` | 查看 ADB 版本 |
| `adb devices` | 查看已连接设备 |
| `adb tcpip 5555` | 开启网络 ADB（端口 5555） |
| `adb connect IP:PORT` | 连接远程设备 |
| `adb disconnect IP:PORT` | 断开远程设备 |
| `adb kill-server` | 停止 ADB 服务 |
| `adb start-server` | 启动 ADB 服务 |

---

## 注意事项

1. **安全性** - 网络 ADB 没有加密，请在可信网络环境中使用
2. **稳定性** - WiFi 连接不如 USB 稳定，重要测试建议使用 USB 连接
3. **性能** - 无线连接的传输速度低于 USB
4. **电量** - 保持设备有足够电量
5. **IP 变化** - 如果设备 IP 变化，需要重新添加设备

---

## 附录：工作流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    ADB 远程设备连接流程                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  安装 ADB 工具   │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ 开启设备开发者选项 │
                    │   开启 USB 调试   │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  USB 连接设备    │
                    │   授权 USB 调试  │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ adb tcpip 5555  │
                    │  开启网络 ADB    │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  获取设备 IP     │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ 平台添加远程设备  │
                    │ 输入 IP 和端口   │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  连接成功！      │
                    │  可断开 USB 线   │
                    └─────────────────┘
```