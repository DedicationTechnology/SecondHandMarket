import re
from django.core.mail import send_mail  # 发送邮件
from django.contrib.auth import authenticate, login, logout  # 验证用户
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views import View  # 类视图
from django.shortcuts import render, redirect  # redirect是跳转页面所需要的方法
from django.urls import reverse  # reverse可以通过页面的名字来反向解析出页面的地址
from user.models import User, Address
from itsdangerous import  TimedJSONWebSignatureSerializer as Serializer  # 限时激活的模块并进行重命名
from SecondHandMarket import settings
from itsdangerous import SignatureExpired  # 激活时间到期异常
from order.models import OrderGoods, OrderInfo
from celery_tasks.tasks import  send_register_active_email  # 导入异步处理任务中用来发送邮件的方法
from utils.mixin import LoginRequiredMixin  # 需要登录后才能访问的视图界面
from django_redis import  get_redis_connection  # 连接redis
from goods.models import GoodsSKU
# 用类视图来处理界面的显示函数
# 注册界面视图
class RegisterView(View):  # 继承View是为了在urls中可以使用它的默认方法as_view()来在视图上显示类中的内容
    # 如果是get请求就调用get函数，如果是post请求就调用post函数
    # 通过post和get方式的不同来进行不同的处理
    def get(self, request):  # get是View的as_view()函数内部将GET请求方式全部小写为get，也就是说这里是调用get方法来达到获取get请求的目的
        # 显示注册页面
        return render(request, 'register.html')
    # 下面post方法必须写post不能写其他的名字，因为是将POST小写为post而得到的
    def post(self, request):
        # 进行注册处理
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据校验
        if not all([username, password, email]):  # all()函数对于其中的迭代对象只有全部迭代才会返回true
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        # 用于判断邮箱格式的正则表达式
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            # get方法只能返回一条数据，如果查询不到则返回一个DoesNotExist的错误
            user = User.objects.get(username=username)  # 第一个username是表达中的属性，第二个username为接收到的username
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 判断两次的密码是否一致
        if cpassword != password:
            return render(request, 'register.html', {'errmsg': '两次输入的密码不一致'})

        # 进行业务处理: 进行用户注册
        user = User.objects.create_user(username, email, password)  # 通过Django自带的create_user方法来写入，注意顺序不能错
        user.is_active = 0  # 这里的user就是注册的用户，对注册用户默认设置为不激活，后面通过邮箱来进行激活
        user.save()
        # 通过邮件发送激活地址来激活用户的账户
        # 激活地址为http://127.0.0.1:8000/user/active/user_id
        '''user_id是在user表中用户的id，每个用户具有唯一性，为了防止恶意激活(判断这个是id从而激活其他用户)，
        需要将user_id进行加密，这里通过itsdangerous包来进行带有时效性的加密'''
        # 加密
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm':user.id}  # 定义一个字典用来存放id
        # f = open('token.txt', 'a')
        token = serializer.dumps(info).decode()  # dump进行加密，加密的为byte格式，前面会有一个b
        # decode()将byte格式转换为字符串格式
        # 发邮件
        send_register_active_email.delay(email, username, token)  # 使用delay函数将发送邮件的任务放到异步处理器，括号内为要传递的参数
        # 返回应答, 跳转到首页
        return redirect(reverse('goods:index'))  # 通过反向解析获得地址从而来跳转页面
# 激活界面视图
class ActiveView(View):
    def get(self, request, token):
        # 不管加密还是解密都需要写下面的对象
        serializer = Serializer(settings.SECRET_KEY, 3600)  # 前者表示加密的秘钥，可以随意设置，这里设置为django默认的一种秘钥，3600表示激活时间为3600秒
        try:
            info = serializer.loads(token)  # 对token进行解密
            user_id = info['confirm']  # 获取解密后的user_id
            # 根据用户id来获取用户的信息并激活用户
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 激活成功后跳转到登录界面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 表明激活时间已过
            return HttpResponse('激活链接已过期')
# 登录界面视图
class LoginView(View):
    def get(self, request):
        # 判断是否记录了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username':username, 'checked':checked})

    def post(self, request):
        # 接受数据
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        # 判断数据是否全部接受
        if all([username, pwd]):
            # 校验数据，使用django内置的校验系统进行校验
            user = authenticate(username=username, password=pwd)
            if user is not None:
            # 验证成功,使用Django内部的用户登录来记录用户的登录状态
                # 判断用户是否激活
                if user.is_active:
                    # 记录用户的登录状态
                    login(request, user)
                    # 获取登录后索要跳转到的地址
                    '''例如用户信息界面如何用户没有登录在页面中输入相关的网址不能直接跳转到用户信息界面，
                    要跳转到指定的界面，这里指定的界面后面有next，且next后面的地址就是用户信息界面'''
                    next_url = request.GET.get('next', reverse('goods:index'))  # 如果没有得到next值，next_url默认赋值为goods:index反向解析的网址
                    # 带着登录状态跳转到next_url页面，默认跳转到首页
                    response = redirect(next_url)
                    # 判断是否需要记住用户名
                    remember = request.POST.get('remember')
                    if remember == 'on':
                        # 需要记住用户名
                        response.set_cookie('username', username, max_age=7*24*3600)  # 设置过期时间为一周
                    else:
                        response.delete_cookie('username')
                    return response



                else:
                    # 用户未激活
                    return render(request, 'login.html', {'errmsg':'用户未激活'})

            else:
                # 判断用户是否注册
                try:
                    user = User.objects.get(username=username)
                    return render(request, 'login.html', {'errmsg':'密码不正确'})
                except User.DoesNotExist:
                    return render(request, 'login.html', {'errmsg':'用户尚未注册'})


        # No backend authenticated the credentials

        else:
            return render(request, 'login.html', {'errmsg':'用户名或密码没有填写'})
# /user/logout
class LogoutView(View):
    # 退出登录
    def get(self, request):
        # 清除用户的session信息
        logout(request)
        # 跳转到首页
        return redirect(reverse('goods:index'))
# /user
class UserInfoView(LoginRequiredMixin, View):  # 这两个参数的顺序不能颠倒，颠倒可能会报错
    '''用户中心-信息页'''
    def get(self, request):
        '''显示'''


        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)  # 返回的是user相关的全部信息不只包括地址

        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host='192.168.40.128', port='6379', db=9)
        con = get_redis_connection('default')  # 拿到默认的链接

        history_key = 'history_%d'%user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4) # 返回一个列表，下标从0到4，并且是倒序

        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)  # 查找id在sku_ids之中的值，但不会直接根据sku_ids的顺序进行输出而是直接按照id的大小进行输出

        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)

        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page':'user',
                   'address':address,
                   'goods_li':goods_li}

        # Django会给request对象添加一个属性request.user
        # 如果用户未登录->user是AnonymousUser类的一个实例对象
        # 如果用户登录->user是User类的一个实例对象
        # request.user.is_authenticated()
        # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传给模板文件,在模板文件中可以直接调用user.is_authenticated来判断是否登录
        return render(request, 'user_center_info.html', context)

# /user/order
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心-订单页'''
    def get(self, request, page):
        '''显示'''
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品的信息
        for order in orders:
            # 根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历order_skus计算商品的小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性amount,保存订单商品的小计
                order_sku.amount = amount

            # 动态给order增加属性，保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给order增加属性，保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,
                   'page': 'order'}

        # 使用模板
        return render(request, 'user_center_order.html', context)


# /user/address
class AddressView(LoginRequiredMixin, View):
    '''用户中心-地址页'''
    def get(self, request):
        '''显示'''
        # 获取登录用户对应User对象
        user = request.user

        # 获取用户的默认收货地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True) # models.Manager
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address = None
        address = Address.objects.get_default_address(user)

        # 使用模板
        return render(request, 'user_center_site.html', {'page':'address', 'address':address})

    def post(self, request):
        '''地址的添加'''
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg':'数据不完整'})

        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg':'手机格式不正确'})

        # 业务处理：地址添加
        # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        # 获取登录用户对应User对象
        user = request.user

        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address = None

        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答,刷新地址页面
        return redirect(reverse('user:address')) # get请求方式

