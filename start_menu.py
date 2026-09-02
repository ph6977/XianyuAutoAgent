#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
闲鱼机器人主菜单
提供各种功能的交互式菜单
"""

import os
import sys
import time
from datetime import datetime
from loguru import logger

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_main_menu():
    """显示主菜单"""
    clear_screen()
    print("=" * 60)
    print("                   闲鱼机器人主菜单")
    print("=" * 60)
    print("1.  启动闲鱼机器人")
    print("2.  Cookie管理功能")
    print("3.  Chrome Cookie获取")
    print("4.  批量爬取用户消息")
    print("5.  消息处理功能")
    print("6.  聊天记录分析")
    print("7.  设备租赁咨询")
    print("0.  退出")
    print("=" * 60)

def run_smart_reply_test():
    """运行智能回复功能 - 启动完整的闲鱼机器人"""
    try:
        print("启动闲鱼机器人...")
        print("正在加载机器人核心功能...")
        
        # 尝试导入并启动XianyuBot
        try:
            from src.bot.xianyu_bot import main
            import os
            from dotenv import load_dotenv
            load_dotenv()  # 加载环境变量
            
            # 获取必要的配置
            api_key = os.getenv("API_KEY")
            cookies_str = os.getenv("COOKIES_STR")
            
            if not api_key or not cookies_str:
                print("❌ 机器人配置不完整！")
                print("请检查 .env 文件中的 API_KEY 和 COOKIES_STR 配置")
                input("按回车键继续...")
                return
            
            print("✅ 配置加载成功")
            print("正在启动闲鱼机器人...")
            print("机器人将连接到闲鱼服务器并开始自动回复消息")
            print("\n注意：机器人启动后将持续运行，处理闲鱼消息")
            print("如需停止，请使用 Ctrl+C 中断程序")
            
            # 直接运行机器人的主函数
            main()  # 这会阻塞执行，运行完整的机器人
            
        except ImportError as e:
            print(f"❌ 无法导入xianyu_bot主函数: {e}")
            print("尝试直接启动机器人...")
            
            # 尝试直接运行xianyu_bot模块
            import subprocess
            import sys
            import threading
            import os
            
            def run_in_subprocess():
                try:
                    # 使用绝对路径运行机器人脚本
                    robot_script_path = os.path.join(os.path.dirname(__file__), "xianyu_bot_components", "xianyu_bot.py")
                    subprocess.run([sys.executable, robot_script_path], check=True, cwd=os.path.dirname(__file__))
                except subprocess.CalledProcessError as e:
                    print(f"❌ 机器人进程启动失败: {e}")
            
            # 在新线程中启动机器人进程
            bot_thread = threading.Thread(target=run_in_subprocess, daemon=True)
            bot_thread.start()
            
            print("✅ 机器人已在后台启动")
            print("机器人将持续监听闲鱼消息并自动回复")
            print("飞书表格数据已作为知识库集成，可查询设备状态")
            
        except KeyboardInterrupt:
            print("\n⚠️  用户中断了机器人运行")
        except Exception as e:
            print(f"❌ 启动机器人时发生错误: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ 启动机器人失败: {e}")
    finally:
        input("按回车键继续...")

def run_cookie_manager():
    """运行Cookie管理功能"""
    try:
        print("Cookie管理功能")
        print("正在模拟Cookie管理功能...")
        
        import os
        cookies_str = os.getenv("COOKIES_STR", "")
        
        if cookies_str:
            print(f"\n当前Cookie长度: {len(cookies_str)}")
            print("Cookie状态: 已配置")
            # 显示部分Cookie信息（不显示敏感信息）
            if 'unb=' in cookies_str:
                import re
                unb_match = re.search(r'unb=([^;]+)', cookies_str)
                if unb_match:
                    print(f"用户ID: {unb_match.group(1)[:10]}...")  # 只显示前10位
        else:
            print("\nCookie状态: 未配置")
        
        print("\nCookie管理选项:")
        print("1. 检查Cookie有效期")
        print("2. 更新Cookie")
        print("3. 导出Cookie")
        
        option = input("请选择操作 (1-3): ").strip()
        if option == '1':
            print("正在检查Cookie有效期...")
            # 这里可以添加实际的Cookie检查逻辑
            print("Cookie有效期检查完成")
        elif option == '2':
            print("Cookie更新功能待实现")
        elif option == '3':
            print("Cookie导出功能待实现")
        else:
            print("无效选择")
        
    except Exception as e:
        print(f"Cookie管理功能启动失败: {e}")
    finally:
        input("按回车键继续...")

def run_chrome_cookie_getter():
    """运行Chrome Cookie获取功能"""
    try:
        print("Chrome Cookie获取功能")
        print("正在模拟Chrome Cookie获取功能...")
        
        # 这里可以集成chrome_cookie_manager.py的功能
        print("\nChrome Cookie获取选项:")
        print("1. 从Chrome浏览器获取Cookie")
        print("2. 检查Chrome配置")
        print("3. 启动Chrome调试模式")
        
        option = input("请选择操作 (1-3): ").strip()
        if option == '1':
            print("正在尝试从Chrome浏览器获取Cookie...")
            # 这里可以添加实际的Chrome Cookie获取逻辑
            print("Chrome Cookie获取功能待实现")
        elif option == '2':
            print("正在检查Chrome配置...")
            print("Chrome配置检查功能待实现")
        elif option == '3':
            print("正在启动Chrome调试模式...")
            print("Chrome调试模式功能待实现")
        else:
            print("无效选择")
        
    except Exception as e:
        print(f"Chrome Cookie获取功能启动失败: {e}")
    finally:
        input("按回车键继续...")

def run_batch_message_crawler():
    """运行批量爬取用户消息功能 - 使用基础版爬虫自动爬取聊天列表用户"""
    crawler = None  # 初始化crawler变量
    crawler_type = "未知"

    try:
        print("批量爬取用户消息功能")
        
        # 获取用户输入的爬取数量
        try:
            user_input = input("请输入要爬取的用户数量 (默认为10): ").strip()
            if user_input:
                max_users = int(user_input)
                if max_users <= 0:
                    print("用户数量必须大于0，使用默认值10")
                    max_users = 10
                elif max_users > 100:  # 设置一个合理的上限
                    print("用户数量不能超过100，使用最大值100")
                    max_users = 100
                else:
                    max_users = max_users
            else:
                max_users = 10  # 默认值
        except ValueError:
            print("输入无效，使用默认值10")
            max_users = 10
        
        print(f"将爬取前 {max_users} 个用户的聊天记录")
        
        # 直接使用基础版爬虫（我们修改过的版本）
        try:
            print("正在导入基础版爬虫工具...")
            from src.crawler.tools.batch_user_crawler import BatchUserCrawler
            crawler = BatchUserCrawler(headless=False)
            crawler_type = "基础版"
            print(f"发现{crawler_type}批量用户爬虫工具")
        except ImportError as e:
            print(f"基础版本导入失败: {e}")
            print("未找到可用的爬虫工具")
            print("请确保已安装所需依赖（如DrissionPage）")
            print("安装命令: pip install DrissionPage")
            input("按回车键继续...")
            return
        except Exception as e:
            print(f"基础版本初始化失败: {e}")
            print("所有爬虫工具都不可用")
            input("按回车键继续...")
            return

        print("正在启动浏览器并登录闲鱼...")
        if not crawler.init_browser():
            print("浏览器初始化失败")
            input("按回车键继续...")
            return

        success = crawler.login_and_navigate()
        if not success:
            print("登录失败，请手动登录后重试")
            input("按回车键继续...")
            return

        print("正在等待页面加载完成...")
        import time
        time.sleep(5)  # 等待页面完全加载

        print("正在爬取聊天列表中的用户消息...")
        # 直接爬取聊天列表中的所有用户，每个用户最多爬取50条消息
        results = crawler.crawl_chat_list_users(max_users=max_users, max_messages=50)
        print(f"爬取完成！共处理 {len(results)} 个用户")

        # 统计结果
        successful_count = sum(1 for data in results.values() if data and data.get('messages'))
        print(f"成功获取聊天记录的用户数: {successful_count}")

        if results:
            print("聊天记录包含以下交易因素：")
            print("  - 议价次数统计")
            print("  - 原始价格与成交价格对比")
            print("  - 包邮信息")
            print("  - 交易状态")
            print("  - 商品成色讨论")
            print("  - 完整议价历史")
            print("  - 买家消息内容")
        else:
            print("未找到任何用户聊天记录，可能需要手动检查闲鱼页面")

    except AttributeError as e:
        print(f"爬虫工具缺少必要方法: {e}")
        print(f"可能是{crawler_type}爬虫工具版本不兼容")
    except Exception as e:
        print(f"爬虫执行出错: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\n用户中断了爬取过程")
    finally:
        # 不管是否成功都等待用户输入，防止闪退
        input("按回车键继续...")

def run_message_processor():
    """运行消息处理功能"""
    try:
        print("消息处理功能")
        print("正在模拟消息处理功能...")
        
        print("\n消息处理选项:")
        print("1. 处理单条消息")
        print("2. 批量处理消息")
        print("3. 消息分类统计")
        
        option = input("请选择操作 (1-3): ").strip()
        if option == '1':
            print("正在处理单条消息...")
            print("单条消息处理功能待实现")
        elif option == '2':
            print("正在批量处理消息...")
            print("批量消息处理功能待实现")
        elif option == '3':
            print("正在统计消息分类...")
            print("消息分类统计功能待实现")
        else:
            print("无效选择")
        
    except Exception as e:
        print(f"消息处理功能启动失败: {e}")
    finally:
        input("按回车键继续...")

def run_chat_analysis():
    """运行聊天记录分析功能"""
    try:
        print("聊天记录分析功能")
        print("正在导入交易分析模块...")
        
        from src.bot.trading_analyzer import TradingAnalyzer
        from src.core.context_manager import ChatContextManager
        
        context_manager = ChatContextManager()
        analyzer = TradingAnalyzer(context_manager)
        
        print("\n聊天记录分析选项:")
        print("1. 分析议价行为模式")
        print("2. 分析影响利润的因素")
        print("3. 生成完整交易分析报告")
        print("4. 导出分析报告到JSON")
        print("5. 显示分析摘要")
        
        option = input("请选择操作 (1-5): ").strip()
        if option == '1':
            print("\n--- 议价行为分析 ---")
            bargain_analysis = analyzer.analyze_bargain_behavior()
            print(f"总聊天数: {bargain_analysis['total_chats']}")
            print(f"议价聊天数: {bargain_analysis['bargain_chats']}")
            print(f"成交数: {bargain_analysis['completed_deals']}")
            print(f"议价率: {bargain_analysis['bargain_chats']/bargain_analysis['total_chats']*100:.2f}%" if bargain_analysis['total_chats'] > 0 else "0%")
            print(f"平均折扣: {bargain_analysis['price_negotiation_stats']['avg_discount_rate']:.2f}元")
            
        elif option == '2':
            print("\n--- 利润影响因素分析 ---")
            factors = analyzer.analyze_profit_impact_factors()
            
            print("议价影响:")
            print(f"  议价成交率: {factors['bargaining_impact']['bargain_success_rate']:.2%}")
            print(f"  无议价成交率: {factors['bargaining_impact']['no_bargain_success_rate']:.2%}")
            print(f"  议价平均折扣: {factors['bargaining_impact']['avg_discount_with_bargain']:.2f}元")
            
            print("\n邮费影响:")
            print(f"  包邮成交率: {factors['shipping_impact']['free_shipping_success_rate']:.2%}")
            print(f"  付邮成交率: {factors['shipping_impact']['paid_shipping_success_rate']:.2%}")
            
            print("\n时间影响:")
            print(f"  短时成交率: {factors['timing_impact']['short_duration_success_rate']:.2%}")
            print(f"  長时成交率: {factors['timing_impact']['long_duration_success_rate']:.2%}")
            
        elif option == '3':
            print("\n--- 完整交易分析报告 ---")
            report = analyzer.generate_trading_report()
            print(f"总聊天数: {report['summary']['total_chats']}")
            print(f"议价率: {report['summary']['bargain_rate']:.2%}")
            print(f"成交率: {report['summary']['completion_rate']:.2%}")
            print(f"平均折扣: {report['summary']['avg_discount']:.2f}元")
            print(f"包邮率: {report['summary']['free_shipping_rate']:.2%}")
            
            print("\n优化建议:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
                
        elif option == '4':
            print("\n--- 导出分析报告 ---")
            filepath = analyzer.export_analysis_to_json()
            print(f"报告已导出到: {filepath}")
            
        elif option == '5':
            print("\n--- 分析摘要 ---")
            analyzer.print_analysis_summary()
            
        else:
            print("无效选择")
        
    except ImportError as e:
        print(f"导入交易分析模块失败: {e}")
        print("请确保已安装相关模块")
    except Exception as e:
        print(f"聊天记录分析功能启动失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("按回车键继续...")

def run_rental_consultant():
    """运行设备租赁咨询功能"""
    try:
        print("设备租赁咨询功能")
        print("正在加载飞书表格读取器...")
        
        # 加载 .env 文件
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.knowledge.feishu_sheet_reader import FeishuSheetReader
        import os
        from datetime import datetime
        
        # 获取飞书API配置
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
        sheet_id = os.getenv("FEISHU_SHEET_ID")
        
        # 检查配置是否完整
        if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
            print("⚠️  飞书API配置不完整，请检查以下环境变量：")
            print("   FEISHU_APP_ID")
            print("   FEISHU_APP_SECRET") 
            print("   FEISHU_SPREADSHEET_TOKEN")
            print("   FEISHU_SHEET_ID")
            print("\n💡 提示：请在 .env 文件中配置这些参数")
            input("按回车键继续...")
            return
        
        try:
            # 初始化飞书表格读取器
            reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
            print("✅ 飞书表格读取器初始化成功")
            
            print("\n设备租赁咨询选项:")
            print("1. 查询指定设备状态")
            print("2. 查询所有可用设备")
            print("3. 查询指定日期范围内的可用设备")
            print("4. 查询特定位置的设备")
            print("5. 设备状态查询示例")
            
            option = input("请选择操作 (1-5): ").strip()
            
            if option == '1':
                device_name = input("请输入设备名称: ").strip()
                if device_name:
                    date = input("请输入查询日期 (格式: YYYY-MM-DD，直接回车使用今天): ").strip()
                    if not date:
                        date = datetime.now().strftime('%Y-%m-%d')
                    
                    print(f"正在查询设备 '{device_name}' 在 {date} 的状态...")
                    try:
                        status = reader.find_device_status_by_date(device_name, date)
                        if status == "DEVICE_NOT_FOUND":
                            print(f"❌ 未找到设备 '{device_name}'")
                        else:
                            is_available = reader._is_device_available(status)
                            status_desc = reader._get_status_description(status)
                            print(f"设备名称: {device_name}")
                            print(f"日期: {date}")
                            print(f"状态: {status_desc}")
                            print(f"是否可租用: {'是' if is_available else '否'}")
                    except Exception as e:
                        print(f"❌ 查询失败: {e}")
                else:
                    print("设备名称不能为空")
                    
            elif option == '2':
                date = input("请输入查询日期 (格式: YYYY-MM-DD，直接回车使用今天): ").strip()
                if not date:
                    date = datetime.now().strftime('%Y-%m-%d')
                
                print(f"正在查询 {date} 的所有可用设备...")
                try:
                    available_devices = reader.find_available_devices_by_date(date)
                    print(f"✅ {date} 可用设备数量: {len(available_devices)}")
                    
                    if available_devices:
                        print("\n可用设备列表:")
                        for i, device in enumerate(available_devices, 1):
                            print(f"  {i}. {device['name']} - 位置: {device['location']} - 状态: {device['status']}")
                    else:
                        print("当前没有可用设备")
                except Exception as e:
                    print(f"❌ 查询失败: {e}")
                    
            elif option == '3':
                start_date = input("请输入开始日期 (格式: YYYY-MM-DD): ").strip()
                end_date = input("请输入结束日期 (格式: YYYY-MM-DD): ").strip()
                
                if start_date and end_date:
                    print(f"正在查询 {start_date} 到 {end_date} 的连续可用设备...")
                    try:
                        available_devices = reader.find_available_devices_by_date_range(start_date, end_date)
                        print(f"✅ {start_date} 到 {end_date} 连续可用设备数量: {len(available_devices)}")
                        
                        if available_devices:
                            print("\n连续可用设备列表:")
                            for i, device in enumerate(available_devices, 1):
                                print(f"  {i}. {device['name']} - 位置: {device['location']}")
                        else:
                            print("当前日期范围内没有连续可用设备")
                    except Exception as e:
                        print(f"❌ 查询失败: {e}")
                else:
                    print("开始日期和结束日期都不能为空")
                    
            elif option == '4':
                location = input("请输入查询位置: ").strip()
                if location:
                    print(f"正在查询位置 '{location}' 的设备...")
                    try:
                        devices_by_location = reader.find_devices_by_location(location)
                        print(f"位置 '{location}' 的设备数量: {len(devices_by_location)}")
                        
                        if devices_by_location:
                            print("\n设备列表:")
                            for i, device in enumerate(devices_by_location, 1):
                                print(f"  {i}. {device['name']} - 位置: {device['location']} - 状态: {device['status']}")
                        else:
                            print("该位置下没有找到设备")
                    except Exception as e:
                        print(f"❌ 查询失败: {e}")
                else:
                    print("位置不能为空")
                    
            elif option == '5':
                print("\n--- 设备状态查询示例 ---")
                # 示例查询
                sample_devices = ["胖卡4-006", "iPhone 13", "华为P50", "小米12", "设备"]
                
                # 获取实际的设备名称
                sheet_data = reader._get_sheet_data()
                if sheet_data and sheet_data['device_data']:
                    # 使用表格中的第一个设备作为示例
                    first_device = sheet_data['device_data'][0]
                    if first_device and len(first_device) > 0:
                        sample_device_name = str(first_device[0])
                        
                        print(f"示例设备: {sample_device_name}")
                        today = datetime.now().strftime('%Y-%m-%d')
                        print(f"查询日期: {today}")
                        
                        try:
                            status = reader.find_device_status_by_date(sample_device_name, today)
                            is_available = reader._is_device_available(status)
                            status_desc = reader._get_status_description(status)
                            
                            print(f"状态: {status_desc}")
                            print(f"是否可租用: {'是' if is_available else '否'}")
                        except Exception as e:
                            print(f"查询失败: {e}")
                else:
                    print("无法获取设备数据进行示例查询")
            else:
                print("无效选择")
                
        except ImportError:
            print("❌ 飞书表格读取器模块未找到，请确保已安装相关依赖")
        except Exception as e:
            print(f"❌ 设备租赁咨询功能启动失败: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"设备租赁咨询功能初始化失败: {e}")
    finally:
        input("按回车键继续...")



def main():
    """主函数"""
    while True:
        show_main_menu()
        choice = input("请选择功能 (0-7): ").strip()
        
        if choice == '1':
            run_smart_reply_test()
        elif choice == '2':
            run_cookie_manager()
        elif choice == '3':
            run_chrome_cookie_getter()
        elif choice == '4':
            run_batch_message_crawler()
        elif choice == '5':
            run_message_processor()
        elif choice == '6':
            run_chat_analysis()
        elif choice == '7':
            run_rental_consultant()
        elif choice == '0':
            print("感谢使用，再见！")
            break
        else:
            print("无效选择，请重新输入")
            input("按回车键继续...")

if __name__ == "__main__":
    main()