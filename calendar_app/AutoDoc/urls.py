from django.urls import path
from . import views

app_name = 'AutoDoc'

urlpatterns = [
    path('calendar/', views.calendar_view, name='calendar'),
    path('details/<int:year>/<int:month>/<int:day>/', views.assignment_details_view, name='assignment_details'),
    path('create-assignment/<int:year>/<int:month>/<int:day>/', views.create_assignment, name='create_assignment'),
    path('update-work-status/<int:assignment_id>/', views.update_work_status, name='update_work_status'),
    path('delete-assignment/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
    #update card
    path('get-assignment/<int:assignment_id>/', views.get_assignment, name='get_assignment'),
    path('update-assignment/', views.update_assignment, name='update_assignment'),
]