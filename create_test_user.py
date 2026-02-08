import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 创建测试用户
try:
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='test123456'
    )
    print(f'✅ 用户创建成功: {user.username}')
    print(f'   邮箱: {user.email}')
    print(f'   密码: test123456')
except Exception as e:
    print(f'❌ 创建用户失败: {e}')
    if 'unique constraint' in str(e).lower() or 'duplicate' in str(e).lower():
        print('ℹ️  用户已存在，可以直接登录')
        print(f'   用户名: testuser')
        print(f'   密码: test123456')