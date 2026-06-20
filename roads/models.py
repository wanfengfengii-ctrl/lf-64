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

HAZARD_LOCATION_TYPE_CHOICES = [
    ('stone_step', '石阶'),
    ('slope', '边坡'),
    ('drainage', '排水沟'),
    ('bridge_culvert', '桥涵'),
    ('retaining_wall', '挡墙'),
    ('tunnel', '隧道/涵洞'),
    ('road_surface', '路面'),
    ('other', '其他'),
]

HAZARD_TYPE_CHOICES = [
    ('landslide', '塌方/滑坡'),
    ('waterlogging', '积水'),
    ('rockfall', '落石'),
    ('fracture', '断裂/开裂'),
    ('slippery', '湿滑'),
    ('subsidence', '沉降/塌陷'),
    ('blockage', '堵塞'),
    ('erosion', '冲刷/侵蚀'),
    ('deformation', '变形'),
    ('other', '其他'),
]

HAZARD_LEVEL_CHOICES = [
    ('safe', '安全'),
    ('info', '提示'),
    ('warning', '警告'),
    ('severe', '严重'),
    ('critical', '紧急'),
]

HAZARD_STATUS_CHOICES = [
    ('reported', '已上报'),
    ('assessing', '评估中'),
    ('pending_disposal', '待处置'),
    ('disposing', '处置中'),
    ('monitoring', '监控观察'),
    ('resolved', '已消除'),
    ('closed', '已闭环'),
]

CONTROL_SUGGESTION_CHOICES = [
    ('none', '无需封控'),
    ('caution', '设置警示标识'),
    ('speed_limit', '限速通行'),
    ('single_lane', '单向/间歇通行'),
    ('detour', '建议绕行'),
    ('full_closure', '全路段封闭'),
]

PASSAGE_STATUS_CHOICES = [
    ('normal', '正常通行'),
    ('caution', '谨慎通行'),
    ('restricted', '限制通行'),
    ('detour', '建议绕行'),
    ('closed', '禁止通行'),
]

DISPOSAL_TYPE_CHOICES = [
    ('reported', '隐患上报'),
    ('assessed', '等级评估'),
    ('dispatched', '派发任务'),
    ('onsite', '现场处置'),
    ('reinforced', '加固维修'),
    ('cleaned', '清理疏通'),
    ('monitored', '设置监控'),
    ('controlled', '封控警戒'),
    ('inspected', '复核验收'),
    ('closed', '闭环归档'),
    ('other', '其他操作'),
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
        on_delete=models.SET_NULL,
        related_name='task_orders',
        verbose_name='关联巡查记录',
        null=True,
        blank=True
    )
    hazard = models.ForeignKey(
        'Hazard',
        on_delete=models.SET_NULL,
        related_name='task_orders',
        verbose_name='关联灾害隐患',
        null=True,
        blank=True
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
        discovery_time = self.created_at
        if self.inspection:
            discovery_time = self.inspection.inspection_date
        elif self.hazard:
            discovery_time = self.hazard.reported_at
        steps = [
            {'key': 'discovery', 'label': '发现', 'done': True, 'time': discovery_time},
            {'key': 'dispatch', 'label': '派单', 'done': self.status != 'pending', 'time': self.dispatched_at},
            {'key': 'rectify', 'label': '整改', 'done': self.status in ['pending_review', 'closed', 'rejected'], 'time': self.rectified_at},
            {'key': 'review', 'label': '复核', 'done': self.status in ['closed', 'rejected'], 'time': self.reviewed_at},
        ]
        return steps


class Hazard(models.Model):
    road_section = models.ForeignKey(
        RoadSection,
        on_delete=models.CASCADE,
        related_name='hazards',
        verbose_name='所属路段',
        null=True,
        blank=True
    )
    point = models.ForeignKey(
        Point,
        on_delete=models.SET_NULL,
        related_name='hazards',
        verbose_name='关联点位',
        null=True,
        blank=True
    )
    code = models.CharField('隐患编号', max_length=50, unique=True)
    title = models.CharField('隐患标题', max_length=200)
    location_type = models.CharField(
        '位置类型',
        max_length=30,
        choices=HAZARD_LOCATION_TYPE_CHOICES
    )
    hazard_type = models.CharField(
        '隐患类型',
        max_length=30,
        choices=HAZARD_TYPE_CHOICES
    )
    hazard_level = models.CharField(
        '预警等级',
        max_length=20,
        choices=HAZARD_LEVEL_CHOICES,
        default='info'
    )
    status = models.CharField(
        '处置状态',
        max_length=30,
        choices=HAZARD_STATUS_CHOICES,
        default='reported'
    )
    description = models.TextField('隐患描述', blank=True)
    latitude = models.FloatField('纬度', null=True, blank=True)
    longitude = models.FloatField('经度', null=True, blank=True)
    location_desc = models.CharField('具体位置描述', max_length=300, blank=True)
    reported_by = models.CharField('上报人', max_length=100)
    reported_at = models.DateTimeField('上报时间', auto_now_add=True)
    reported_date = models.DateField('上报日期', null=True, blank=True)
    inspection_source = models.ForeignKey(
        InspectionRecord,
        on_delete=models.SET_NULL,
        related_name='hazards',
        verbose_name='来源巡查记录',
        null=True,
        blank=True
    )
    control_suggestion = models.CharField(
        '封控建议',
        max_length=30,
        choices=CONTROL_SUGGESTION_CHOICES,
        default='none'
    )
    passage_status = models.CharField(
        '通行状态',
        max_length=30,
        choices=PASSAGE_STATUS_CHOICES,
        default='normal'
    )
    assess_note = models.TextField('评估意见', blank=True)
    assessed_by = models.CharField('评估人', max_length=100, blank=True)
    assessed_at = models.DateTimeField('评估时间', null=True, blank=True)
    disposal_deadline = models.DateField('处置期限', null=True, blank=True)
    resolved_at = models.DateTimeField('消除时间', null=True, blank=True)
    closed_at = models.DateTimeField('闭环时间', null=True, blank=True)
    closed_by = models.CharField('闭环人', max_length=100, blank=True)
    affected_length_m = models.FloatField('影响长度(米)', default=0, blank=True)
    casualty_info = models.TextField('人员伤亡情况', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '灾害隐患'
        verbose_name_plural = '灾害隐患'
        ordering = ['-reported_at']

    def __str__(self):
        return f'[{self.get_hazard_level_display()}] {self.code} - {self.title}'

    def clean(self):
        if not self.code:
            date_str = timezone.now().strftime('%Y%m%d')
            count = Hazard.objects.filter(code__startswith=f'HZD{date_str}').count() + 1
            self.code = f'HZD{date_str}{count:04d}'
        if not self.reported_date:
            self.reported_date = timezone.now().date()
        if self.latitude is not None:
            if not (-90 <= self.latitude <= 90):
                raise ValidationError({'latitude': '纬度必须在 -90 到 90 之间。'})
        if self.longitude is not None:
            if not (-180 <= self.longitude <= 180):
                raise ValidationError({'longitude': '经度必须在 -180 到 180 之间。'})
        if self.point and not self.road_section:
            self.road_section = self.point.road_section
        if self.point:
            if self.latitude is None:
                self.latitude = self.point.latitude
            if self.longitude is None:
                self.longitude = self.point.longitude

    def save(self, *args, **kwargs):
        if not self.code:
            date_str = timezone.now().strftime('%Y%m%d')
            count = Hazard.objects.filter(code__startswith=f'HZD{date_str}').count() + 1
            self.code = f'HZD{date_str}{count:04d}'
        if not self.reported_date:
            self.reported_date = timezone.now().date()
        if self.point and not self.road_section:
            self.road_section = self.point.road_section
        if self.point:
            if self.latitude is None:
                self.latitude = self.point.latitude
            if self.longitude is None:
                self.longitude = self.point.longitude

        self.full_clean()

        if self.status in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        if self.status == 'closed':
            if not self.closed_at:
                self.closed_at = timezone.now()
            if not self.hazard_level == 'safe':
                self.hazard_level = 'safe'
            if not self.passage_status == 'normal':
                self.passage_status = 'normal'
        super().save(*args, **kwargs)

    def is_overdue(self):
        if self.disposal_deadline and self.status not in ['resolved', 'closed']:
            return timezone.now().date() > self.disposal_deadline
        return False

    def get_active_disposals(self):
        return self.disposals.filter(is_active=True).order_by('-disposed_at')

    def get_latest_disposal(self):
        return self.disposals.order_by('-disposed_at').first()

    def get_progress_percentage(self):
        status_order = {
            'reported': 0,
            'assessing': 15,
            'pending_disposal': 30,
            'disposing': 55,
            'monitoring': 75,
            'resolved': 90,
            'closed': 100,
        }
        return status_order.get(self.status, 0)

    def get_hazard_level_color(self):
        colors = {
            'safe': '#28a745',
            'info': '#17a2b8',
            'warning': '#ffc107',
            'severe': '#fd7e14',
            'critical': '#dc3545',
        }
        return colors.get(self.hazard_level, '#6c757d')

    def get_passage_status_color(self):
        colors = {
            'normal': '#28a745',
            'caution': '#ffc107',
            'restricted': '#fd7e14',
            'detour': '#6f42c1',
            'closed': '#dc3545',
        }
        return colors.get(self.passage_status, '#6c757d')


class HazardDisposal(models.Model):
    hazard = models.ForeignKey(
        Hazard,
        on_delete=models.CASCADE,
        related_name='disposals',
        verbose_name='关联隐患'
    )
    disposal_type = models.CharField(
        '处置类型',
        max_length=30,
        choices=DISPOSAL_TYPE_CHOICES
    )
    status_before = models.CharField(
        '操作前状态',
        max_length=30,
        choices=HAZARD_STATUS_CHOICES,
        blank=True
    )
    status_after = models.CharField(
        '操作后状态',
        max_length=30,
        choices=HAZARD_STATUS_CHOICES,
        blank=True
    )
    level_before = models.CharField(
        '操作前等级',
        max_length=20,
        choices=HAZARD_LEVEL_CHOICES,
        blank=True
    )
    level_after = models.CharField(
        '操作后等级',
        max_length=20,
        choices=HAZARD_LEVEL_CHOICES,
        blank=True
    )
    passage_before = models.CharField(
        '操作前通行',
        max_length=30,
        choices=PASSAGE_STATUS_CHOICES,
        blank=True
    )
    passage_after = models.CharField(
        '操作后通行',
        max_length=30,
        choices=PASSAGE_STATUS_CHOICES,
        blank=True
    )
    description = models.TextField('处置说明')
    disposed_by = models.CharField('处置人员', max_length=100)
    disposed_at = models.DateTimeField('处置时间', default=timezone.now)
    disposal_result = models.TextField('处置结果', blank=True)
    next_step = models.CharField('下一步措施', max_length=300, blank=True)
    related_task = models.ForeignKey(
        TaskOrder,
        on_delete=models.SET_NULL,
        related_name='hazard_disposals',
        verbose_name='关联工单',
        null=True,
        blank=True
    )
    is_active = models.BooleanField('有效记录', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '隐患处置记录'
        verbose_name_plural = '隐患处置记录'
        ordering = ['-disposed_at']

    def __str__(self):
        return f'{self.hazard.code} - {self.get_disposal_type_display()} [{self.disposed_at}]'


class RoadPassageStatus(models.Model):
    road_section = models.ForeignKey(
        RoadSection,
        on_delete=models.CASCADE,
        related_name='passage_statuses',
        verbose_name='所属路段',
        unique=True
    )
    passage_status = models.CharField(
        '当前通行状态',
        max_length=30,
        choices=PASSAGE_STATUS_CHOICES,
        default='normal'
    )
    active_hazard_count = models.IntegerField('活跃隐患数', default=0)
    critical_hazard_count = models.IntegerField('紧急隐患数', default=0)
    affected_start_km = models.FloatField('影响起点公里', null=True, blank=True)
    affected_end_km = models.FloatField('影响终点公里', null=True, blank=True)
    status_reason = models.CharField('状态原因', max_length=500, blank=True)
    updated_by = models.CharField('更新人', max_length=100, blank=True)
    effective_from = models.DateTimeField('生效时间', auto_now_add=True)
    estimated_resume = models.DateTimeField('预计恢复时间', null=True, blank=True)
    notice_public = models.TextField('对外公告内容', blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '路段通行状态'
        verbose_name_plural = '路段通行状态'
        ordering = ['road_section__code']

    def __str__(self):
        return f'{self.road_section.code} - {self.get_passage_status_display()}'

    def get_status_color(self):
        colors = {
            'normal': '#28a745',
            'caution': '#ffc107',
            'restricted': '#fd7e14',
            'detour': '#6f42c1',
            'closed': '#dc3545',
        }
        return colors.get(self.passage_status, '#6c757d')

    def recalculate_from_hazards(self):
        hazards = self.road_section.hazards.exclude(
            status__in=['resolved', 'closed']
        )
        self.active_hazard_count = hazards.count()
        self.critical_hazard_count = hazards.filter(
            hazard_level__in=['severe', 'critical']
        ).count()
        if self.critical_hazard_count > 0:
            new_status = 'closed'
            self.status_reason = f'存在{self.critical_hazard_count}处紧急隐患'
        elif hazards.filter(hazard_level='warning').exists():
            new_status = 'restricted'
            self.status_reason = '存在警告级隐患'
        elif hazards.filter(hazard_level='info').exists():
            new_status = 'caution'
            self.status_reason = '存在提示级隐患'
        else:
            new_status = 'normal'
            self.status_reason = '通行正常'
        self.passage_status = new_status
        self.save()
        return new_status
