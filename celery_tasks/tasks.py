# 使用celery
from celery import Celery
from django.template import loader, RequestContext
import time
from django.conf import settings
from django.core.mail import send_mail
from django_redis import get_redis_connection

# 在任务处理端加入这几句
import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SecondHandMarket.settings")
# django.setup()
# 以下类要写在下方，否则会报错
from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
# 创建一个celery类的实例对象
# ps aux | grep redis查看redis的地址
app = Celery('celery_tasks.tasks', broker='redis://172.16.136.128:6379/8')  # 8表示要用的数据库
# celery_tasks.tasks名字随便起，但最好用这个规律，worker中的app中会显示该部分内容，broker表示中间人，这里为redis
# 定义任务函数
@app.task  # 使用task方法进行装饰，app为上面实例化的对象
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '二手交易市场欢迎你'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    # 当邮件显示的信息中含有html标签时用html_message属性来编写，如果没有可以用message来编写
    html_message = '<h1>%s，欢迎你成为二手交易市场的会员</h1>请点击下面的链接来进行账户激活<br/>' \
                   '<a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)  # 发送邮件的函数，前四个的顺序是固定

@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners


    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners,}

    # 使用模板
    # 1. 加载模版文件，返回
    temp = loader.get_template('static_index.html')
    # 2. 模版渲染
    static_index_html = temp.render(context)

    # 生成首页对应的静态文件
    sava_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(sava_path, 'w') as f:
        f.write(static_index_html)
