from django.urls import path
from . import views

app_name = 'roads'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('map/', views.map_view, name='map'),
    path('charts/', views.charts_view, name='charts'),

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

    path('api/wear-data/', views.api_wear_data, name='api_wear_data'),
    path('api/points-geo/', views.api_points_geo, name='api_points_geo'),
]
