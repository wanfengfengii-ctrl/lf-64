from django import forms
from .models import (
    RoadSection, Point, InspectionRecord, Photo, Alert, TaskOrder,
    Hazard, HazardDisposal, RoadPassageStatus,
    WEAR_LEVEL_CHOICES, POINT_TYPE_CHOICES, ROAD_STATUS_CHOICES,
    ALERT_LEVEL_CHOICES, ALERT_TYPE_CHOICES, TASK_STATUS_CHOICES,
    HAZARD_LOCATION_TYPE_CHOICES, HAZARD_TYPE_CHOICES,
    HAZARD_LEVEL_CHOICES, HAZARD_STATUS_CHOICES,
    CONTROL_SUGGESTION_CHOICES, PASSAGE_STATUS_CHOICES,
    DISPOSAL_TYPE_CHOICES,
)


class RoadSectionForm(forms.ModelForm):
    class Meta:
        model = RoadSection
        fields = ['name', 'code', 'start_location', 'end_location', 'length_km', 'historical_info', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'start_location': forms.TextInput(attrs={'class': 'form-control'}),
            'end_location': forms.TextInput(attrs={'class': 'form-control'}),
            'length_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'historical_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('status') == 'good' and self.instance.pk:
            has_critical = self.instance.points.filter(
                inspections__wear_level=4,
                inspections__handled=False
            ).exists()
            if has_critical:
                self.add_error('status', '该路段存在未处理的严重磨损点，不能标记为状态良好。')
        return cleaned_data


class PointForm(forms.ModelForm):
    class Meta:
        model = Point
        fields = ['road_section', 'code', 'name', 'point_type', 'latitude', 'longitude', 'description']
        widgets = {
            'road_section': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'point_type': forms.Select(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is not None and not (-90 <= lat <= 90):
            raise forms.ValidationError('纬度必须在 -90 到 90 之间。')
        return lat

    def clean_longitude(self):
        lon = self.cleaned_data.get('longitude')
        if lon is not None and not (-180 <= lon <= 180):
            raise forms.ValidationError('经度必须在 -180 到 180 之间。')
        return lon


class InspectionRecordForm(forms.ModelForm):
    class Meta:
        model = InspectionRecord
        fields = ['point', 'inspection_date', 'inspector', 'wear_level', 'wear_description', 'maintenance_suggestion', 'handled', 'handled_date']
        widgets = {
            'point': forms.Select(attrs={'class': 'form-control'}),
            'inspection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'inspector': forms.TextInput(attrs={'class': 'form-control'}),
            'wear_level': forms.Select(attrs={'class': 'form-control'}, choices=WEAR_LEVEL_CHOICES),
            'wear_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'maintenance_suggestion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'handled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'handled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['wear_level'].choices = WEAR_LEVEL_CHOICES


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['point', 'inspection', 'image', 'caption', 'photo_type', 'taken_at']
        widgets = {
            'point': forms.Select(attrs={'class': 'form-control'}),
            'inspection': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'photo_type': forms.Select(attrs={'class': 'form-control'}),
            'taken_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class TaskOrderForm(forms.ModelForm):
    class Meta:
        model = TaskOrder
        fields = ['inspection', 'point', 'title', 'description', 'priority', 'assigned_to', 'deadline']
        widgets = {
            'inspection': forms.Select(attrs={'class': 'form-control'}),
            'point': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.TextInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class TaskDispatchForm(forms.ModelForm):
    class Meta:
        model = TaskOrder
        fields = ['assigned_to', 'dispatch_note', 'deadline', 'priority']
        widgets = {
            'assigned_to': forms.TextInput(attrs={'class': 'form-control'}),
            'dispatch_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }


class TaskRectifyForm(forms.ModelForm):
    class Meta:
        model = TaskOrder
        fields = ['rectification_result']
        widgets = {
            'rectification_result': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class TaskReviewForm(forms.ModelForm):
    class Meta:
        model = TaskOrder
        fields = ['review_note', 'reviewer']
        widgets = {
            'review_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'reviewer': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AlertForm(forms.ModelForm):
    class Meta:
        model = Alert
        fields = ['point', 'alert_type', 'alert_level', 'message']
        widgets = {
            'point': forms.Select(attrs={'class': 'form-control'}),
            'alert_type': forms.Select(attrs={'class': 'form-control'}),
            'alert_level': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DataExportForm(forms.Form):
    EXPORT_TYPE_CHOICES = [
        ('inspections', '巡查记录'),
        ('points', '点位数据'),
        ('tasks', '工单数据'),
        ('alerts', '预警数据'),
    ]
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel (xlsx)'),
    ]
    export_type = forms.ChoiceField(
        label='导出类型',
        choices=EXPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    export_format = forms.ChoiceField(
        label='文件格式',
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    road_section = forms.ModelChoiceField(
        label='路段筛选',
        queryset=RoadSection.objects.all(),
        required=False,
        empty_label='全部路段',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        label='开始日期',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        label='结束日期',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class HazardForm(forms.ModelForm):
    class Meta:
        model = Hazard
        fields = [
            'road_section', 'point', 'title', 'location_type', 'hazard_type',
            'hazard_level', 'description', 'latitude', 'longitude',
            'location_desc', 'reported_by', 'reported_date',
            'inspection_source', 'control_suggestion', 'passage_status',
            'affected_length_m', 'casualty_info'
        ]
        widgets = {
            'road_section': forms.Select(attrs={'class': 'form-control'}),
            'point': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'location_type': forms.Select(attrs={'class': 'form-control'}),
            'hazard_type': forms.Select(attrs={'class': 'form-control'}),
            'hazard_level': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'location_desc': forms.TextInput(attrs={'class': 'form-control'}),
            'reported_by': forms.TextInput(attrs={'class': 'form-control'}),
            'reported_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'inspection_source': forms.Select(attrs={'class': 'form-control'}),
            'control_suggestion': forms.Select(attrs={'class': 'form-control'}),
            'passage_status': forms.Select(attrs={'class': 'form-control'}),
            'affected_length_m': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'casualty_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['road_section'].required = False
        self.fields['point'].required = False
        self.fields['inspection_source'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['hazard_level'].required = False
        self.fields['control_suggestion'].required = False
        self.fields['passage_status'].required = False
        self.fields['affected_length_m'].required = False
        self.fields['description'].required = False
        self.fields['location_desc'].required = False
        self.fields['casualty_info'].required = False


class HazardAssessForm(forms.ModelForm):
    class Meta:
        model = Hazard
        fields = [
            'hazard_level', 'status', 'control_suggestion', 'passage_status',
            'assess_note', 'assessed_by', 'disposal_deadline'
        ]
        widgets = {
            'hazard_level': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'control_suggestion': forms.Select(attrs={'class': 'form-control'}),
            'passage_status': forms.Select(attrs={'class': 'form-control'}),
            'assess_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'assessed_by': forms.TextInput(attrs={'class': 'form-control'}),
            'disposal_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class HazardStatusForm(forms.ModelForm):
    class Meta:
        model = Hazard
        fields = ['status', 'hazard_level', 'passage_status', 'closed_by']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'hazard_level': forms.Select(attrs={'class': 'form-control'}),
            'passage_status': forms.Select(attrs={'class': 'form-control'}),
            'closed_by': forms.TextInput(attrs={'class': 'form-control'}),
        }


class HazardDisposalForm(forms.ModelForm):
    class Meta:
        model = HazardDisposal
        fields = [
            'disposal_type', 'description', 'disposed_by', 'disposed_at',
            'disposal_result', 'next_step', 'related_task',
            'status_after', 'level_after', 'passage_after'
        ]
        widgets = {
            'disposal_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'disposed_by': forms.TextInput(attrs={'class': 'form-control'}),
            'disposed_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'disposal_result': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'next_step': forms.TextInput(attrs={'class': 'form-control'}),
            'related_task': forms.Select(attrs={'class': 'form-control'}),
            'status_after': forms.Select(attrs={'class': 'form-control'}),
            'level_after': forms.Select(attrs={'class': 'form-control'}),
            'passage_after': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['related_task'].required = False
        self.fields['status_after'].required = False
        self.fields['level_after'].required = False
        self.fields['passage_after'].required = False
        self.fields['disposal_result'].required = False
        self.fields['next_step'].required = False


class RoadPassageStatusForm(forms.ModelForm):
    class Meta:
        model = RoadPassageStatus
        fields = [
            'passage_status', 'affected_start_km', 'affected_end_km',
            'status_reason', 'updated_by', 'estimated_resume', 'notice_public'
        ]
        widgets = {
            'passage_status': forms.Select(attrs={'class': 'form-control'}),
            'affected_start_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'affected_end_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'status_reason': forms.TextInput(attrs={'class': 'form-control'}),
            'updated_by': forms.TextInput(attrs={'class': 'form-control'}),
            'estimated_resume': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notice_public': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
