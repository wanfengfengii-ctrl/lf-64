import os
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

ALERT_LEVEL_CHOICES = [
    ('info', '提示'),
    ('warning', '警告'),
    ('critical', '紧急'),
]

ALERT_TYPE_CHOICES = [
    ('wear_critical', '严重磨损预警'),
    ('wear_worsening', '磨损恶化趋势'),
    ('task_overdue', '工单超期预警'),
    ('unhandled_long', '长期未处理预警'),
]

TASK_STATUS_CHOICES = [
    ('pending', '待派发'),
    ('dispatched', '已派发'),
    ('rectifying', '整改中'),
    ('pending_review', '待复核'),
    ('closed', '已闭环'),
    ('rejected', '复核不通过'),
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

    def get_worst_unhandled_inspection(self):
        return self.inspections.filter(handled=False).order_by('-wear_level', '-inspection_date').first()

    def get_worst_unhandled_wear_level(self):
        worst = self.get_worst_unhandled_inspection()
        if worst:
            return worst.wear_level
        return None

    def is_high_risk(self):
        worst = self.get_worst_unhandled_inspection()
        if worst and worst.wear_level >= 3:
            return True
        return False

    def has_unhandled_critical(self):
        return self.inspections.filter(wear_level=4, handled=False).exists()

    def get_open_task(self):
        return self.task_orders.exclude(status='closed').first()


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


def photo_upload_path(instance, filename):
    point_code = instance.point.code if instance.point else 'unknown'
    date_str = timezone.now().strftime('%Y%m%d')
    return os.path.join('photos', point_code, date_str, filename)


class Photo(models.Model):
    point = models.ForeignKey(
        Point,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='点位'
    )
    inspection = models.ForeignKey(
        InspectionRecord,
        on_delete=models.SET_NULL,
        related_name='photos',
        verbose_name='巡查记录',
        null=True,
        blank=True
    )
    image = models.ImageField('照片', upload_to=photo_upload_path)
    caption = models.CharField('照片说明', max_length=200, blank=True)
    photo_type = models.CharField(
        '照片类型',
        max_length=20,
        choices=[
            ('inspection', '巡查照片'),
            ('damage', '破损照片'),
            ('rectification', '整改照片'),
            ('verification', '复核照片'),
        ],
        default='inspection'
    )
    taken_at = models.DateField('拍摄日期', null=True, blank=True)
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        verbose_name = '照片档案'
        verbose_name_plural = '照片档案'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.point.code} - {self.caption or self.image.name}'


class Alert(models.Model):
    point = models.ForeignKey(
        Point,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='点位'
    )
    alert_type = models.CharField(
        '预警类型',
        max_length=20,
        choices=ALERT_TYPE_CHOICES
    )
    alert_level = models.CharField(
        '预警等级',
        max_length=20,
        choices=ALERT_LEVEL_CHOICES
    )
    message = models.TextField('预警信息')
    is_read = models.BooleanField('是否已读', default=False)
    is_resolved = models.BooleanField('是否已处理', default=False)
    related_inspection = models.ForeignKey(
        InspectionRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联巡查记录'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    resolved_at = models.DateTimeField('处理时间', null=True, blank=True)

    class Meta:
        verbose_name = '风险预警'
        verbose_name_plural = '风险预警'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_alert_level_display()}] {self.point.code} - {self.get_alert_type_display()}'

    def resolve(self):
        self.is_resolved = True
        self.is_read = True
        self.resolved_at = timezone.now()
        self.save()


class TaskOrder(models.Model):
    inspection = models.ForeignKey(
        InspectionRecord,
        on_delete=models.CASCADE,
        related_name='task_orders',
        verbose_name='关联巡查记录'
    )
    point = models.ForeignKey(
        Point,
        on_delete=models.CASCADE,
        related_name='task_orders',
        verbose_name='点位'
    )
    title = models.CharField('工单标题', max_length=200)
    description = models.TextField('工单描述', blank=True)
    status = models.CharField(
        '工单状态',
        max_length=20,
        choices=TASK_STATUS_CHOICES,
        default='pending'
    )
    priority = models.CharField(
        '优先级',
        max_length=10,
        choices=[
            ('urgent', '紧急'),
            ('high', '高'),
            ('medium', '中'),
            ('low', '低'),
        ],
        default='high'
    )
    assigned_to = models.CharField('指派人员', max_length=100, blank=True)
    dispatch_note = models.TextField('派发说明', blank=True)
    rectification_result = models.TextField('整改结果', blank=True)
    review_note = models.TextField('复核意见', blank=True)
    reviewer = models.CharField('复核人', max_length=100, blank=True)
    deadline = models.DateField('整改期限', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    dispatched_at = models.DateTimeField('派发时间', null=True, blank=True)
    rectified_at = models.DateTimeField('整改完成时间', null=True, blank=True)
    reviewed_at = models.DateTimeField('复核时间', null=True, blank=True)
    closed_at = models.DateTimeField('闭环时间', null=True, blank=True)

    class Meta:
        verbose_name = '任务工单'
        verbose_name_plural = '任务工单'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} [{self.get_status_display()}]'

    def is_overdue(self):
        if self.deadline and self.status not in ['closed']:
            return timezone.now().date() > self.deadline
        return False

    def get_progress_steps(self):
        steps = [
            {'key': 'discovery', 'label': '发现', 'done': True, 'time': self.inspection.inspection_date},
            {'key': 'dispatch', 'label': '派单', 'done': self.status != 'pending', 'time': self.dispatched_at},
            {'key': 'rectify', 'label': '整改', 'done': self.status in ['pending_review', 'closed', 'rejected'], 'time': self.rectified_at},
            {'key': 'review', 'label': '复核', 'done': self.status in ['closed', 'rejected'], 'time': self.reviewed_at},
        ]
        return steps
