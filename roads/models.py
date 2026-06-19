from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q


WEAR_LEVEL_CHOICES = [
    (1, '轻微'),
    (2, '一般'),
    (3, '较重'),
    (4, '严重'),
]

POINT_TYPE_CHOICES = [
    ('stone_step', '石阶'),
    ('road_stele', '路碑'),
    ('drainage', '排水沟'),
]

ROAD_STATUS_CHOICES = [
    ('good', '状态良好'),
    ('warning', '需要关注'),
    ('critical', '亟待维护'),
]


class RoadSection(models.Model):
    name = models.CharField('路段名称', max_length=200, unique=True)
    code = models.CharField('路段编号', max_length=50, unique=True)
    start_location = models.CharField('起点位置', max_length=200)
    end_location = models.CharField('终点位置', max_length=200)
    length_km = models.FloatField('长度(公里)', default=0)
    historical_info = models.TextField('历史背景', blank=True)
    status = models.CharField(
        '路段状态',
        max_length=20,
        choices=ROAD_STATUS_CHOICES,
        default='good'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '路段档案'
        verbose_name_plural = '路段档案'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'

    def clean(self):
        if self.status == 'good':
            has_critical = self.points.filter(
                inspections__wear_level=4,
                inspections__handled=False
            ).exists()
            if has_critical:
                raise ValidationError({
                    'status': '该路段存在未处理的严重磨损点，不能标记为状态良好。'
                })

    def get_unhandled_critical_count(self):
        return self.points.filter(
            inspections__wear_level=4,
            inspections__handled=False
        ).distinct().count()


class Point(models.Model):
    road_section = models.ForeignKey(
        RoadSection,
        on_delete=models.CASCADE,
        related_name='points',
        verbose_name='所属路段'
    )
    code = models.CharField('点位编号', max_length=50, unique=True)
    name = models.CharField('点位名称', max_length=200)
    point_type = models.CharField(
        '点位类型',
        max_length=20,
        choices=POINT_TYPE_CHOICES
    )
    latitude = models.FloatField('纬度')
    longitude = models.FloatField('经度')
    description = models.TextField('点位描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '点位'
        verbose_name_plural = '点位'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'

    def clean(self):
        if not (-90 <= self.latitude <= 90):
            raise ValidationError({
                'latitude': '纬度必须在 -90 到 90 之间。'
            })
        if not (-180 <= self.longitude <= 180):
            raise ValidationError({
                'longitude': '经度必须在 -180 到 180 之间。'
            })

    def get_latest_inspection(self):
        return self.inspections.order_by('-inspection_date').first()

    def get_current_wear_level(self):
        latest = self.get_latest_inspection()
        if latest:
            return latest.wear_level
        return None

    def is_high_risk(self):
        latest = self.get_latest_inspection()
        if latest and latest.wear_level >= 3 and not latest.handled:
            return True
        return False


class InspectionRecord(models.Model):
    point = models.ForeignKey(
        Point,
        on_delete=models.CASCADE,
        related_name='inspections',
        verbose_name='点位'
    )
    inspection_date = models.DateField('巡查日期')
    inspector = models.CharField('巡查人员', max_length=100)
    wear_level = models.IntegerField(
        '磨损等级',
        choices=WEAR_LEVEL_CHOICES
    )
    wear_description = models.TextField('磨损描述', blank=True)
    maintenance_suggestion = models.TextField('维护建议', blank=True)
    handled = models.BooleanField('是否已处理', default=False)
    handled_date = models.DateField('处理日期', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '巡查记录'
        verbose_name_plural = '巡查记录'
        ordering = ['-inspection_date']
        unique_together = [['point', 'inspection_date']]

    def __str__(self):
        return f'{self.point.code} - {self.inspection_date}'

    def clean(self):
        today = timezone.now().date()
        if self.inspection_date > today:
            raise ValidationError({
                'inspection_date': '巡查日期不能晚于当前日期。'
            })

        if self.wear_level == 4 and not self.maintenance_suggestion.strip():
            raise ValidationError({
                'maintenance_suggestion': '磨损等级为严重时必须填写维护建议。'
            })

        if self.handled and not self.handled_date:
            self.handled_date = today

    def get_wear_level_display_full(self):
        return dict(WEAR_LEVEL_CHOICES).get(self.wear_level, '未知')

    def get_priority(self):
        if self.wear_level == 4 and not self.handled:
            return '紧急'
        elif self.wear_level == 3 and not self.handled:
            return '高'
        elif self.wear_level == 2 and not self.handled:
            return '中'
        elif self.wear_level == 1 and not self.handled:
            return '低'
        return '已处理'
