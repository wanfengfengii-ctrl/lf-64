from django.contrib import admin
from .models import RoadSection, Point, InspectionRecord


class PointInline(admin.TabularInline):
    model = Point
    extra = 0
    fields = ['code', 'name', 'point_type', 'latitude', 'longitude']


class InspectionInline(admin.TabularInline):
    model = InspectionRecord
    extra = 0
    fields = ['inspection_date', 'inspector', 'wear_level', 'handled']


@admin.register(RoadSection)
class RoadSectionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'status', 'length_km', 'get_unhandled_critical_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'code']
    inlines = [PointInline]


@admin.register(Point)
class PointAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'road_section', 'point_type', 'latitude', 'longitude', 'is_high_risk']
    list_filter = ['point_type', 'road_section']
    search_fields = ['code', 'name']
    inlines = [InspectionInline]


@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ['point', 'inspection_date', 'inspector', 'get_wear_level_display_full', 'handled', 'get_priority']
    list_filter = ['wear_level', 'handled', 'inspection_date']
    search_fields = ['point__code', 'point__name', 'inspector']
    date_hierarchy = 'inspection_date'
