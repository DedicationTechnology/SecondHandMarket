from django.contrib.auth.decorators import login_required

# 有些视图需要用户登录之后才能访问
class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):  # 在url.py中按住ctrl并点击鼠标可以快速跳转到对应点界面获取相关的函数说明
        # 调用父类的as_view
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)  # login_required只有用户登录后才会执行后面的视图