from django.urls import path
from . import views

app_name = 'AutoDoc'

urlpatterns = [
    path('calendar/', views.calendar_view, name='calendar'),
    path('details/<int:year>/<int:month>/<int:day>/', views.assignment_details_view, name='assignment_details'),
    path('create-assignment/<int:year>/<int:month>/<int:day>/', views.create_assignment, name='create_assignment'),
    path('update-work-status/<int:assignment_id>/', views.update_work_status, name='update_work_status'),
]