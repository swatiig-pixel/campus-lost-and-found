from django.urls import path
from . import views

app_name = 'lostfound'

urlpatterns = [
    # Public / Student
    path('', views.landing_page, name='landing'),
    path('lost/', views.lost_items, name='lost_items'),
    path('found/', views.found_items, name='found_items'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('report/lost/', views.report_lost, name='report_lost'),
    path('report/found/', views.report_found, name='report_found'),
    path('my-reports/', views.my_reports, name='my_reports'),
    path('my-reports/edit/<int:pk>/', views.edit_report, name='edit_report'),
    path('my-reports/delete/<int:pk>/', views.delete_report, name='delete_report'),
    path('claim/<int:item_pk>/', views.submit_claim, name='submit_claim'),
    path('my-claims/', views.my_claims, name='my_claims'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('messages/<int:item_pk>/<int:other_user_pk>/', views.message_conversation, name='message_conversation'),

    # Admin
    path('admin/items/', views.admin_items, name='admin_items'),
    path('admin/items/<int:pk>/', views.admin_item_action, name='admin_item_action'),
    path('admin/claims/', views.admin_claims, name='admin_claims'),
    path('admin/claims/<int:pk>/', views.admin_claim_detail, name='admin_claim_detail'),
]
