from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.student_dashboard, name='student_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/students/', views.admin_students, name='admin_students'),
    path('admin/students/<int:pk>/', views.admin_student_detail, name='admin_student_detail'),
    path('admin/students/<int:pk>/toggle/', views.admin_toggle_student, name='admin_toggle_student'),
]
