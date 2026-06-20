from django.contrib import admin
from .models import (
    RoadSection, Point, InspectionRecord, Photo, Alert, TaskOrder,
    Hazard, HazardDisposal, RoadPassageStatus,
)


class PointInline(admin.TabularInline):
    model = Point
    extra = 0
    fields = ['code', 'name', 'point_type', 'latitude', 'longitude']


class InspectionInline(admin.TabularInline):
    model = InspectionRecord
    extra = 0
    fields = ['inspection_date', 'inspector', 'wear_level', 'handled']


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0
    fields = ['caption', 'photo_type', 'image', 'taken_at']
    readonly_fields = ['uploaded_at']


class HazardDisposalInline(admin.TabularInline):
    model = HazardDisposal
    extra = 0
    fields = ['disposal_type', 'disposed_by', 'disposed_at', 'description']
    readonly_fields = ['created_at']


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
    inlines = [InspectionInline, PhotoInline]


@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ['point', 'inspection_date', 'inspector', 'get_wear_level_display_full', 'handled', 'get_priority']
    list_filter = ['wear_level', 'handled', 'inspection_date']
    search_fields = ['point__code', 'point__name', 'inspector']
    date_hierarchy = 'inspection_date'


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['point', 'caption', 'photo_type', 'taken_at', 'uploaded_at']
    list_filter = ['photo_type', 'uploaded_at']
    search_fields = ['point__code', 'point__name', 'caption']
    date_hierarchy = 'uploaded_at'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['point', 'alert_type', 'alert_level', 'is_read', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'alert_level', 'is_read', 'is_resolved']
    search_fields = ['point__code', 'point__name', 'message']
    date_hierarchy = 'created_at'


@admin.register(TaskOrder)
class TaskOrderAdmin(admin.ModelAdmin):
    list_display = ['title', 'point', 'status', 'priority', 'assigned_to', 'deadline', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['title', 'point__code', 'assigned_to']
    date_hierarchy = 'created_at'


@admin.register(Hazard)
class HazardAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'hazard_type', 'hazard_level', 'status',
                    'passage_status', 'reported_by', 'reported_date', 'is_overdue']
    list_filter = ['hazard_level', 'hazard_type', 'location_type', 'status', 'passage_status']
    search_fields = ['code', 'title', 'description', 'location_desc', 'reported_by']
    date_hierarchy = 'reported_at'
    readonly_fields = ['created_at', 'updated_at']
    inlines = [HazardDisposalInline]


@admin.register(HazardDisposal)
class HazardDisposalAdmin(admin.ModelAdmin):
    list_display = ['hazard', 'disposal_type', 'disposed_by', 'disposed_at', 'status_after']
    list_filter = ['disposal_type', 'status_after', 'level_after']
    search_fields = ['hazard__code', 'description', 'disposed_by']
    date_hierarchy = 'disposed_at'
    readonly_fields = ['created_at']


@admin.register(RoadPassageStatus)
class RoadPassageStatusAdmin(admin.ModelAdmin):
    list_display = ['road_section', 'passage_status', 'active_hazard_count',
                    'critical_hazard_count', 'updated_by', 'updated_at']
    list_filter = ['passage_status']
    search_fields = ['road_section__code', 'road_section__name', 'status_reason']
    readonly_fields = ['effective_from', 'updated_at']
