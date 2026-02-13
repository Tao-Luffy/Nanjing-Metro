from selenium import webdriver
from selenium.webdriver.edge.options import Options
import json
import time
import os

class WeiboLogin:
    def __init__(self):
        self.driver = None

    def init_driver(self):
        """初始化 Edge 浏览器"""
        try:
            edge_options = Options()
            edge_options.add_argument('--start-maximized')

            # 固定用户数据目录：首次登录后会被复用
            profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "edge_profile_weibo"))
            edge_options.add_argument(rf'--user-data-dir={profile_dir}')

            # 可选稳定性参数
            edge_options.add_argument('--no-first-run')
            edge_options.add_argument('--no-default-browser-check')

            print("正在启动 Edge 浏览器...")
            self.driver = webdriver.Edge(options=edge_options)

            # 隐藏 webdriver 特征
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })

            print("✓ 浏览器启动成功！\n")
            return True
        except Exception as e:
            print(f"❌ 启动浏览器失败: {e}")
            return False

    def manual_login(self):
        """手动登录微博"""
        print("=" * 60)
        print("   请在浏览器中手动完成登录")
        print("=" * 60)
        print("\n操作步骤：")
        print("1. 在打开的浏览器中输入账号密码")
        print("2. 完成验证码或滑块验证（如有）")
        print("3. 点击登录按钮")
        print("4. 确认登录成功后，回到此窗口")
        print("=" * 60 + "\n")

        # 打开微博登录页面
        self.driver.get('https://weibo.com')
        time.sleep(2)
        self.driver.get('https://weibo.com')
        time.sleep(2)

        # 已登录就直接跳过
        if 'login' not in self.driver.current_url.lower():
            print("\n✓ 已检测到登录态，跳过手动登录\n")
            return True

        # 等待用户手动登录
        input("完成登录后按 Enter 键继续...")

        # 验证是否登录成功
        current_url = self.driver.current_url
        page_title = self.driver.title

        if 'login' not in current_url.lower() and 'weibo' in current_url:
            print(f"\n✓ 登录成功！当前页面: {page_title}\n")
            return True
        else:
            print("\n⚠️  似乎还未登录成功")
            retry = input("是否重试？(y/n): ")
            if retry.lower() == 'y':
                return self.manual_login()
            return False

    def get_cookies(self):
        """获取并保存 Cookies"""
        try:
            print("=" * 60)
            print("正在获取 Cookies...")
            print("=" * 60 + "\n")

            # 获取所有 Cookie
            cookies = self.driver.get_cookies()

            if not cookies:
                print("❌ 未获取到 Cookie")
                return None

            print(f"✓ 成功获取 {len(cookies)} 个 Cookie\n")

            # 显示 Cookie 列表
            print("Cookie 列表：")
            for i, cookie in enumerate(cookies, 1):
                name = cookie.get('name', '')
                value = cookie.get('value', '')[:50]  # 只显示前50个字符
                print(f"  {i}. {name}: {value}...")
            print()

            # 保存为 JSON 格式
            with open('weibo_cookies.json', 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print("✓ Cookies 已保存到: weibo_cookies.json")

            # 保存为字符串格式
            cookie_list = [f"{c['name']}={c['value']}" for c in cookies]
            cookie_string = '; '.join(cookie_list)

            with open('weibo_cookies.txt', 'w', encoding='utf-8') as f:
                f.write(cookie_string)
            print("✓ Cookie 字符串已保存到: weibo_cookies.txt")

            # 在浏览器中显示提示
            js_code = f'alert("成功获取 {len(cookies)} 个 Cookie！\\n\\n已保存到本地文件")'
            self.driver.execute_script(js_code)
            time.sleep(2)

            try:
                self.driver.switch_to.alert.accept()
            except:
                pass

            # 打印 Cookie 字符串预览
            print("\n" + "=" * 60)
            print("Cookie 字符串预览（前200字符）：")
            print("=" * 60)
            print(cookie_string[:200] + "...")
            print("=" * 60 + "\n")

            return cookie_string

        except Exception as e:
            print(f"❌ 获取 Cookies 失败: {e}")
            return None

    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("正在关闭浏览器...")
            self.driver.quit()
            print("✓ 浏览器已关闭\n")


def main():
    print("\n" + "=" * 60)
    print("   微博手动登录获取 Cookie 工具")
    print("=" * 60 + "\n")

    weibo = WeiboLogin()

    try:
        # 初始化浏览器
        if not weibo.init_driver():
            print("初始化失败，程序退出")
            return

        # 手动登录
        if not weibo.manual_login():
            print("\n登录失败，程序退出")
            return

        # 获取 Cookies
        cookies = weibo.get_cookies()

        if cookies:
            print("=" * 60)
            print("   ✓ 所有操作完成！")
            print("=" * 60)
            print("\nCookie 文件保存位置：")
            print("  • weibo_cookies.json (JSON格式)")
            print("  • weibo_cookies.txt  (字符串格式)")
            print("\n可以在其他程序中使用这些 Cookie 文件\n")

        # input("按 Enter 键关闭浏览器...")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
    finally:
        weibo.close()


if __name__ == '__main__':
    main()
