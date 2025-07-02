from django.urls import path
from .views import EmailThreadView, SendEmailView,InboxView

urlpatterns = [
    path('threads/', EmailThreadView.as_view()),
    path('send/', SendEmailView.as_view()),
    path('inbox/', InboxView.as_view(), name='inbox_emails'),
]
