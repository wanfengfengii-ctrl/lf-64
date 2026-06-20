from django.urls import path
from . import views

app_name = 'roads'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('map/', views.map_view, name='map'),
    path('charts/', views.charts_view, name='charts'),
    path('priority/', views.priority_list, name='priority_list'),
    path('export/', views.export_page, name='export'),

    path('roads/', views.road_list, name='road_list'),
    path('roads/create/', views.road_create, name='road_create'),
    path('roads/<int:pk>/', views.road_detail, name='road_detail'),
    path('roads/<int:pk>/edit/', views.road_edit, name='road_edit'),
    path('roads/<int:pk>/delete/', views.road_delete, name='road_delete'),

    path('points/', views.point_list, name='point_list'),
    path('points/create/', views.point_create, name='point_create'),
    path('points/<int:pk>/', views.point_detail, name='point_detail'),
    path('points/<int:pk>/edit/', views.point_edit, name='point_edit'),
    path('points/<int:pk>/delete/', views.point_delete, name='point_delete'),

    path('inspections/', views.inspection_list, name='inspection_list'),
    path('inspections/create/', views.inspection_create, name='inspection_create'),
    path('inspections/<int:pk>/', views.inspection_detail, name='inspection_detail'),
    path('inspections/<int:pk>/edit/', views.inspection_edit, name='inspection_edit'),
    path('inspections/<int:pk>/delete/', views.inspection_delete, name='inspection_delete'),

    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/create/', views.alert_create, name='alert_create'),
    path('alerts/generate/', views.alert_generate_auto, name='alert_generate_auto'),
    path('alerts/<int:pk>/', views.alert_detail, name='alert_detail'),
    path('alerts/<int:pk>/read/', views.alert_mark_read, name='alert_mark_read'),
    path('alerts/<int:pk>/resolve/', views.alert_resolve, name='alert_resolve'),

    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/create/<int:inspection_pk>/', views.task_create, name='task_create_from_insp'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/dispatch/', views.task_dispatch, name='task_dispatch'),
    path('tasks/<int:pk>/rectify/', views.task_rectify, name='task_rectify'),
    path('tasks/<int:pk>/review/', views.task_review, name='task_review'),
    path('tasks/<int:pk>/status/', views.task_status_progress, name='task_status_progress'),

    path('photos/', views.photo_list, name='photo_list'),
    path('photos/upload/', views.photo_upload, name='photo_upload'),
    path('photos/<int:pk>/', views.photo_detail, name='photo_detail'),
    path('photos/<int:pk>/delete/', views.photo_delete, name='photo_delete'),

    path('hazards/', views.hazard_list, name='hazard_list'),
    path('hazards/create/', views.hazard_create, name='hazard_create'),
    path('hazards/<int:pk>/', views.hazard_detail, name='hazard_detail'),
    path('hazards/<int:pk>/edit/', views.hazard_edit, name='hazard_edit'),
    path('hazards/<int:pk>/delete/', views.hazard_delete, name='hazard_delete'),
    path('hazards/<int:pk>/assess/', views.hazard_assess, name='hazard_assess'),
    path('hazards/<int:pk>/dispose/', views.hazard_dispose, name='hazard_dispose'),
    path('hazards/<int:pk>/close/', views.hazard_close, name='hazard_close'),
    path('hazards/<int:pk>/status/', views.hazard_update_status, name='hazard_update_status'),
    path('hazards/hazard-map/', views.hazard_map, name='hazard_map'),

    path('passage-status/', views.passage_status_list, name='passage_status_list'),
    path('passage-status/<int:pk>/edit/', views.passage_status_edit, name='passage_status_edit'),
    path('passage-status/<int:pk>/recalc/', views.passage_status_recalc, name='passage_status_recalc'),

    path('api/wear-data/', views.api_wear_data, name='api_wear_data'),
    path('api/points-geo/', views.api_points_geo, name='api_points_geo'),
    path('api/points-geo-timeline/', views.api_points_geo_timeline, name='api_points_geo_timeline'),
    path('api/point/<int:point_pk>/wear-history/', views.api_point_wear_history, name='api_point_wear_history'),
    path('api/hazards-geo/', views.api_hazards_geo, name='api_hazards_geo'),
    path('api/roads-passage-status/', views.api_roads_passage_status, name='api_roads_passage_status'),
    path('api/hazard-summary/', views.api_hazard_summary, name='api_hazard_summary'),
]
