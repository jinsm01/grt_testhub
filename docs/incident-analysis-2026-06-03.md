# 代码合并导致的数据库与功能异常事件分析

## 事件概述

**时间**: 2026-06-03  
**涉及人员**: 主开发（你）、A同学  
**影响范围**: 本地开发环境数据库丢失、部分功能无法使用

---

## 事件经过

### 1. 初始状态
- 主开发本地代码运行正常
- 数据库完整，所有功能可用
- 系统登录正常

### 2. 触发事件
- 主开发拉取 A 同学提交的代码并合并
- 合并无冲突，代码合并成功

### 3. 问题表现
1. **登录失败** - 无法登录系统
2. **数据库清空** - 提示账号不存在，本地数据库被清空
3. **功能异常** - 重新配置数据库后，Bug 分析等页面报错"资源不存在"

---

## 根本原因分析

### 问题一：登录失败 → 数据库被清空

**直接原因**:
- 在排查问题时执行了 `rm -f db.sqlite3` 删除数据库文件

**深层原因**:
- A 同学的代码中包含 `data_factory` 应用的新增模型和迁移文件
- 合并后 Django 检测到新的迁移文件，但本地数据库缺少对应表结构
- 尝试修复过程中误删了数据库文件

### 问题二：页面报错"资源不存在"

**根本原因**:
- A 同学为了让自己本地环境能正常运行，将 `data_factory` 应用的启用配置注释掉了
- 具体表现为：
  - `backend/settings.py` 中 `'apps.data_factory'` 被注释
  - `backend/urls.py` 中 `path('api/data-factory/', ...)` 被注释
- 虽然模型代码和迁移文件存在，但应用实际上未被启用
- 前端请求 `/api/data-factory/bug-analysis/summaries/` 时，后端返回 404

### 核心问题总结

```
A 同学的提交不完整：
├── ✅ 模型代码（models.py）
├── ✅ 迁移文件（migrations/）
├── ❌ 应用启用配置（settings.py 中被注释）
├── ❌ URL 路由配置（urls.py 中被注释）
└── ❌ 无文档说明
```

---

## 问题复现路径

1. A 同学在本地开发 `data_factory` 新功能
2. A 同学发现缺少依赖（pandas）或数据库表未创建，导致无法运行
3. A 同学选择注释掉应用启用和 URL 配置，使项目能正常运行其他部分
4. A 同学提交了代码（只提交了能运行的部分）
5. 主开发拉取代码合并
6. 主开发环境数据库与代码不匹配，出现各种异常
7. 修复过程中误删数据库

---

## 解决方案

### 已执行的修复操作

1. **恢复数据库迁移**:
   ```bash
   # 重新创建迁移文件
   python manage.py makemigrations data_factory
   
   # 执行迁移
   python manage.py migrate
   ```

2. **启用应用**:
   - 取消 `backend/settings.py` 中 `'apps.data_factory'` 的注释
   - 取消 `backend/urls.py` 中 `path('api/data-factory/', ...)` 的注释

3. **重新创建超级用户**:
   ```bash
   python manage.py createsuperuser
   ```

---

## 后续规避方案

### 方案一：强制完整提交规范（推荐）

任何涉及数据库模型的提交必须包含：

- [ ] 模型代码（models.py）
- [ ] 迁移文件（执行 `makemigrations` 生成）
- [ ] 应用配置（settings.py 中启用应用）
- [ ] 路由配置（urls.py 中添加路由）
- [ ] 依赖声明（requirements.txt 如有新增依赖）
- [ ] 文档说明（README 更新或提交说明）

**提交前自检清单**:
```bash
# 1. 检查是否有未生成的迁移文件
python manage.py makemigrations --check --dry-run

# 2. 检查迁移是否能正常执行
python manage.py migrate --check

# 3. 检查项目能否正常启动
python manage.py runserver &
```

### 方案二：Git Hooks 自动化检查

在 `.git/hooks/pre-commit` 中添加：

```bash
#!/bin/bash
# 检查是否有模型改动但未生成迁移
if ! python manage.py makemigrations --check --dry-run 2>/dev/null; then
    echo "错误: 检测到模型改动但未生成迁移文件"
    echo "请执行: python manage.py makemigrations"
    exit 1
fi

# 检查 settings.py 中是否有注释掉的本地应用
if grep -q "^\s*#\s*'apps\." backend/settings.py; then
    echo "警告: settings.py 中存在被注释的应用"
    echo "请确认是否需要启用"
fi
```

### 方案三：数据库备份习惯

**合并他人代码前必做**:

```bash
#!/bin/bash
# backup-before-merge.sh

# 备份数据库
BACKUP_NAME="db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)"
cp db.sqlite3 "$BACKUP_NAME"
echo "数据库已备份到: $BACKUP_NAME"

# 备份迁移记录
cp -r apps/*/migrations migrations-backup-$(date +%Y%m%d)

# 执行合并
git pull origin main

# 检查是否有新的迁移文件
python manage.py migrate --check
if [ $? -ne 0 ]; then
    echo "检测到新的迁移文件，准备执行迁移..."
    python manage.py migrate
fi
```

### 方案四：使用 Docker 统一环境

**docker-compose.yml**:
```yaml
version: '3.8'
services:
  web:
    build: .
    volumes:
      - .:/app
      - db_data:/app/data
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
  
  frontend:
    build: ./frontend
    volumes:
      - ./frontend:/app
    ports:
      - "3000:3000"

volumes:
  db_data:
```

避免"在我电脑上能运行"的问题。

### 方案五：分支策略优化

```
main (保护分支)
  ↑
develop (开发分支)
  ↑
feature/data-factory (A同学的功能分支)
```

**流程**:
1. A 同学在 `feature/data-factory` 分支开发
2. 开发完成后，先在本地完整测试
3. 提交 PR 到 `develop` 分支
4. 主开发审查 PR，检查是否包含完整配置
5. 合并到 `develop` 进行集成测试
6. 测试通过后合并到 `main`

---

## 经验教训

### 对主开发的建议

1. **合并前备份**: 养成合并前自动备份数据库的习惯
2. **审查提交**: 不只是看代码，还要看配置是否完整
3. **逐步验证**: 合并后先检查迁移状态，再启动服务
4. **不要急于修复**: 出现问题先分析原因，避免误操作

### 对团队成员的建议

1. **完整提交**: 不要为了方便自己而注释掉配置
2. **自测完整**: 提交前确保功能完整可用，不只是"能跑起来"
3. **文档说明**: 复杂的改动附上说明文档
4. **沟通协作**: 涉及全局配置的改动提前沟通

---

## 相关命令速查

```bash
# 检查迁移状态
python manage.py showmigrations

# 检查是否有未生成的迁移
python manage.py makemigrations --check --dry-run

# 备份数据库
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)

# 恢复数据库
cp db.sqlite3.backup.20260603 db.sqlite3

# 重新创建超级用户
python manage.py createsuperuser

# 查看数据库表结构
python manage.py dbshell
> .tables
```

---

## 附录：本次事件相关提交

- **问题引入**: A 同学提交（未完整启用 data_factory 应用）
- **问题修复**: `1e15c0a` - feat: 启用 data_factory 应用
  - 启用 apps.data_factory 应用
  - 添加 data-factory URL 路由配置
