from django.urls import path, re_path
from user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView
from django.conf.urls import url
from django.contrib.auth.decorators import login_required  # 判断是否登录
urlpatterns = [
    path('register/',RegisterView.as_view(), name='register'),  # 注册
    # path('active/(?P<token>.*)', ActiveView.as_view(), name='active'),  # 直接使用path插入正则无法匹配
    re_path('active/(?P<token>.*)', ActiveView.as_view(), name='active'),  # 使用re_path插入正则才可以匹配，激活
    path('login/', LoginView.as_view(), name='login'),  # 登录
    path('logout/', LogoutView.as_view(), name='logout'),  # 注销登录
    # ?P<token>表示将该部分内容全部以token的名义获取
    # 在setting中设置默认没有登录后的跳转地址LOGIN_URL
    # path('', login_required(UserInfoView.as_view()), name='user'),  # 用户中心-信息页,login_required包起来，只有用户登录后才会执行后续的函数UserInfoView.as_view()
    # path('order/', login_required(UserOrderView.as_view()), name='order'),  # 用户中心-订单页
    # path('address/', login_required(AddressView.as_view()), name='address'),  # 用户中心-地址页
    path('', UserInfoView.as_view(), name='user'),  # 用户中心-信息页
    re_path('order/(?P<page>\d+)', UserOrderView.as_view(), name='order'),  # 用户中心-订单页
    path('address/', AddressView.as_view(), name='address'),  # 用户中心-地址页
]
