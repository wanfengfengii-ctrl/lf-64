from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Q, Max, Min, F
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, date, timedelta
from collections import defaultdict
import csv
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import (
    RoadSection, Point, InspectionRecord, Photo, Alert, TaskOrder,
    WEAR_LEVEL_CHOICES, POINT_TYPE_CHOICES, ROAD_STATUS_CHOICES,
    ALERT_LEVEL_CHOICES, ALERT_TYPE_CHOICES, TASK_STATUS_CHOICES,
)
from .forms import (
    RoadSectionForm, PointForm, InspectionRecordForm,
    PhotoForm, TaskOrderForm, TaskDispatchForm, TaskRectifyForm,
    TaskReviewForm, AlertForm, DataExportForm,
)


def dashboard(request):
    total_roads = RoadSection.objects.count()
    total_points = Point.objects.count()
    total_inspections = InspectionRecord.objects.count()
    high_risk_points = Point.objects.filter(
        inspections__wear_level__gte=3,
        inspections__handled=False
    ).distinct().count()
    critical_points = Point.objects.filter(
        inspections__wear_level=4,
        inspections__handled=False
    ).distinct()

    unread_alerts = Alert.objects.filter(is_read=False, is_resolved=False).count()
    critical_alerts = Alert.objects.filter(alert_level='critical', is_resolved=False).count()
    pending_tasks = TaskOrder.objects.filter(status='pending').count()
    rectifying_tasks = TaskOrder.objects.filter(status='rectifying').count()
    overdue_tasks = TaskOrder.objects.exclude(status='closed').filter(deadline__lt=timezone.now().date()).count()

    recent_inspections = InspectionRecord.objects.select_related('point', 'point__road_section').order_by('-inspection_date')[:10]
    recent_alerts = Alert.objects.select_related('point', 'point__road_section').order_by('-created_at')[:8]
    recent_tasks = TaskOrder.objects.select_related('point', 'point__road_section').order_by('-created_at')[:8]

    roads_with_issues = RoadSection.objects.annotate(
        unhandled_critical=Count('points', filter=Q(
            points__inspections__wear_level=4,
            points__inspections__handled=False
        ), distinct=True)
    ).filter(unhandled_critical__gt=0).order_by('-unhandled_critical')

    wear_distribution = InspectionRecord.objects.values('wear_level').annotate(
        count=Count('id')
    ).order_by('wear_level')

    wear_stats_dict = {level: 0 for level, _ in WEAR_LEVEL_CHOICES}
    for item in wear_distribution:
        wear_stats_dict[item['wear_level']] = item['count']

    wear_stats_list = []
    for level, label in WEAR_LEVEL_CHOICES:
        count = wear_stats_dict.get(level, 0)
        percentage = round(count * 100 / total_inspections, 1) if total_inspections > 0 else 0
        wear_stats_list.append({
            'level': level,
            'label': label,
            'count': count,
            'percentage': percentage,
        })

    task_status_stats = TaskOrder.objects.values('status').annotate(count=Count('id'))
    task_stats_dict = {s: 0 for s, _ in TASK_STATUS_CHOICES}
    for item in task_status_stats:
        task_stats_dict[item['status']] = item['count']

    return render(request, 'roads/dashboard.html', {
        'total_roads': total_roads,
        'total_points': total_points,
        'total_inspections': total_inspections,
        'high_risk_points': high_risk_points,
        'critical_points': critical_points,
        'unread_alerts': unread_alerts,
        'critical_alerts': critical_alerts,
        'pending_tasks': pending_tasks,
        'rectifying_tasks': rectifying_tasks,
        'overdue_tasks': overdue_tasks,
        'recent_inspections': recent_inspections,
        'recent_alerts': recent_alerts,
        'recent_tasks': recent_tasks,
        'roads_with_issues': roads_with_issues,
        'wear_stats_list': wear_stats_list,
        'task_stats_dict': task_stats_dict,
        'task_status_choices': dict(TASK_STATUS_CHOICES),
    })


def map_view(request):
    high_risk = request.GET.get('high_risk', '0') == '1'
    date_param = request.GET.get('date', '')
    points = Point.objects.select_related('road_section').all()
    if high_risk:
        points = points.filter(
            inspections__wear_level__gte=3,
            inspections__handled=False
        ).distinct()

    return render(request, 'roads/map.html', {
        'points': points,
        'high_risk_filter': high_risk,
        'date': date_param,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
        'point_type_choices': dict(POINT_TYPE_CHOICES),
    })


def charts_view(request):
    roads = RoadSection.objects.all()
    selected_road_id = request.GET.get('road_id')
    months_count = int(request.GET.get('months', '6'))
    selected_point_id = request.GET.get('point')
    points = Point.objects.select_related('road_section').all().order_by('code')

    today = timezone.now().date()
    labels = []
    for i in range(months_count - 1, -1, -1):
        month_date = date(today.year, today.month, 1)
        if today.month - i <= 0:
            year = today.year - 1
            month = today.month - i + 12
        else:
            year = today.year
            month = today.month - i
        labels.append(f'{year}年{month}月')

    road_data = []
    if selected_road_id:
        road = get_object_or_404(RoadSection, pk=selected_road_id)
        monthly_avg = []
        for i in range(months_count - 1, -1, -1):
            if today.month - i <= 0:
                year = today.year - 1
                month = today.month - i + 12
            else:
                year = today.year
                month = today.month - i
            inspections = InspectionRecord.objects.filter(
                point__road_section=road,
                inspection_date__year=year,
                inspection_date__month=month
            )
            if inspections.exists():
                avg = inspections.aggregate(avg=Avg('wear_level'))['avg']
                monthly_avg.append(round(avg, 2))
            else:
                monthly_avg.append(0)
        road_data.append({
            'name': road.name,
            'data': monthly_avg,
        })
    else:
        for road in roads:
            monthly_avg = []
            for i in range(months_count - 1, -1, -1):
                if today.month - i <= 0:
                    year = today.year - 1
                    month = today.month - i + 12
                else:
                    year = today.year
                    month = today.month - i
                inspections = InspectionRecord.objects.filter(
                    point__road_section=road,
                    inspection_date__year=year,
                    inspection_date__month=month
                )
                if inspections.exists():
                    avg = inspections.aggregate(avg=Avg('wear_level'))['avg']
                    monthly_avg.append(round(avg, 2))
                else:
                    monthly_avg.append(0)
            road_data.append({
                'name': road.name,
                'data': monthly_avg,
            })

    wear_count_data = defaultdict(lambda: [0] * len(labels))
    for i in range(months_count - 1, -1, -1):
        idx = months_count - 1 - i
        if today.month - i <= 0:
            year = today.year - 1
            month = today.month - i + 12
        else:
            year = today.year
            month = today.month - i
        for level, _ in WEAR_LEVEL_CHOICES:
            count = InspectionRecord.objects.filter(
                inspection_date__year=year,
                inspection_date__month=month,
                wear_level=level
            ).count()
            wear_count_data[level][idx] = count

    return render(request, 'roads/charts.html', {
        'roads': roads,
        'points': points,
        'selected_road_id': int(selected_road_id) if selected_road_id else None,
        'selected_point_id': int(selected_point_id) if selected_point_id else None,
        'months_count': months_count,
        'labels': labels,
        'road_data': road_data,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
        'wear_count_data': dict(wear_count_data),
    })


def api_wear_data(request):
    road_id = request.GET.get('road_id')
    months_count = int(request.GET.get('months', '6'))
    today = timezone.now().date()

    labels = []
    road_data = {}

    roads = RoadSection.objects.all()
    if road_id:
        roads = roads.filter(pk=road_id)

    for road in roads:
        road_data[road.name] = []

    for i in range(months_count - 1, -1, -1):
        if today.month - i <= 0:
            year = today.year - 1
            month = today.month - i + 12
        else:
            year = today.year
            month = today.month - i
        labels.append(f'{year}年{month}月')

        for road in roads:
            inspections = InspectionRecord.objects.filter(
                point__road_section=road,
                inspection_date__year=year,
                inspection_date__month=month
            )
            if inspections.exists():
                avg = inspections.aggregate(avg=Avg('wear_level'))['avg']
                road_data[road.name].append(round(avg, 2))
            else:
                road_data[road.name].append(0)

    return JsonResponse({
        'labels': labels,
        'datasets': road_data,
    })


def api_points_geo(request):
    high_risk = request.GET.get('high_risk', '0') == '1'
    points = Point.objects.select_related('road_section').all()
    if high_risk:
        points = points.filter(
            inspections__wear_level__gte=3,
            inspections__handled=False
        ).distinct()

    features = []
    for point in points:
        worst = point.get_worst_unhandled_inspection()
        latest = point.get_latest_inspection()
        wear_level = worst.wear_level if worst else None
        is_high = point.is_high_risk()

        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [point.longitude, point.latitude],
            },
            'properties': {
                'id': point.id,
                'code': point.code,
                'name': point.name,
                'point_type': point.point_type,
                'point_type_display': point.get_point_type_display(),
                'road_section': point.road_section.name,
                'road_section_id': point.road_section.id,
                'wear_level': wear_level,
                'wear_level_display': dict(WEAR_LEVEL_CHOICES).get(wear_level, '无未处理记录'),
                'is_high_risk': is_high,
                'handled': worst is None,
                'has_latest': latest is not None,
                'latest_wear_level': latest.wear_level if latest else None,
                'latest_wear_display': dict(WEAR_LEVEL_CHOICES).get(latest.wear_level, '无记录') if latest else '无记录',
            }
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
    })


def road_list(request):
    roads = RoadSection.objects.annotate(
        point_count=Count('points', distinct=True),
        unhandled_critical=Count('points', filter=Q(
            points__inspections__wear_level=4,
            points__inspections__handled=False
        ), distinct=True)
    ).all().order_by('code')
    return render(request, 'roads/road_list.html', {'roads': roads})


def road_create(request):
    if request.method == 'POST':
        form = RoadSectionForm(request.POST)
        if form.is_valid():
            road = form.save()
            return redirect('roads:road_detail', pk=road.pk)
    else:
        form = RoadSectionForm()
    return render(request, 'roads/road_form.html', {'form': form, 'mode': 'create'})


def road_detail(request, pk):
    road = get_object_or_404(RoadSection.objects.prefetch_related('points', 'points__inspections'), pk=pk)
    points = road.points.all()
    return render(request, 'roads/road_detail.html', {'road': road, 'points': points})


def road_edit(request, pk):
    road = get_object_or_404(RoadSection, pk=pk)
    if request.method == 'POST':
        form = RoadSectionForm(request.POST, instance=road)
        if form.is_valid():
            form.save()
            return redirect('roads:road_detail', pk=road.pk)
    else:
        form = RoadSectionForm(instance=road)
    return render(request, 'roads/road_form.html', {'form': form, 'road': road, 'mode': 'edit'})


def road_delete(request, pk):
    road = get_object_or_404(RoadSection, pk=pk)
    if request.method == 'POST':
        road.delete()
        return redirect('roads:road_list')
    return render(request, 'roads/road_confirm_delete.html', {'road': road})


def point_list(request):
    road_filter = request.GET.get('road')
    type_filter = request.GET.get('type')
    risk_filter = request.GET.get('risk')

    points = Point.objects.select_related('road_section').all()

    if road_filter:
        points = points.filter(road_section_id=road_filter)
    if type_filter:
        points = points.filter(point_type=type_filter)
    if risk_filter == 'high':
        points = points.filter(
            inspections__wear_level__gte=3,
            inspections__handled=False
        ).distinct()

    points = points.annotate(
        latest_wear=Avg('inspections__wear_level')
    ).order_by('code')

    roads = RoadSection.objects.all()
    return render(request, 'roads/point_list.html', {
        'points': points,
        'roads': roads,
        'road_filter': road_filter,
        'type_filter': type_filter,
        'risk_filter': risk_filter,
        'point_type_choices': dict(POINT_TYPE_CHOICES),
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
    })


def point_create(request):
    if request.method == 'POST':
        form = PointForm(request.POST)
        if form.is_valid():
            try:
                point = form.save(commit=False)
                point.full_clean()
                point = form.save()
                return redirect('roads:point_detail', pk=point.pk)
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
    else:
        form = PointForm()
    return render(request, 'roads/point_form.html', {'form': form, 'mode': 'create'})


def point_detail(request, pk):
    point = get_object_or_404(Point.objects.select_related('road_section').prefetch_related(
        'inspections', 'photos', 'task_orders', 'alerts'
    ), pk=pk)
    inspections = point.inspections.all().order_by('-inspection_date')
    photos = point.photos.all().order_by('-uploaded_at')[:12]
    task_orders = point.task_orders.all().order_by('-created_at')
    alerts = point.alerts.all().order_by('-created_at')[:10]
    return render(request, 'roads/point_detail.html', {
        'point': point,
        'inspections': inspections,
        'photos': photos,
        'task_orders': task_orders,
        'alerts': alerts,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
        'task_status_choices': dict(TASK_STATUS_CHOICES),
    })


def point_edit(request, pk):
    point = get_object_or_404(Point, pk=pk)
    if request.method == 'POST':
        form = PointForm(request.POST, instance=point)
        if form.is_valid():
            try:
                p = form.save(commit=False)
                p.full_clean()
                form.save()
                return redirect('roads:point_detail', pk=point.pk)
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
    else:
        form = PointForm(instance=point)
    return render(request, 'roads/point_form.html', {'form': form, 'point': point, 'mode': 'edit'})


def point_delete(request, pk):
    point = get_object_or_404(Point, pk=pk)
    road_pk = point.road_section.pk
    if request.method == 'POST':
        point.delete()
        return redirect('roads:road_detail', pk=road_pk)
    return render(request, 'roads/point_confirm_delete.html', {'point': point})


def inspection_list(request):
    point_filter = request.GET.get('point')
    level_filter = request.GET.get('level')
    handled_filter = request.GET.get('handled')

    inspections = InspectionRecord.objects.select_related('point', 'point__road_section').all()

    if point_filter:
        inspections = inspections.filter(point_id=point_filter)
    if level_filter:
        inspections = inspections.filter(wear_level=int(level_filter))
    if handled_filter == 'yes':
        inspections = inspections.filter(handled=True)
    elif handled_filter == 'no':
        inspections = inspections.filter(handled=False)

    inspections = inspections.order_by('-inspection_date')
    points = Point.objects.all().order_by('code')

    return render(request, 'roads/inspection_list.html', {
        'inspections': inspections,
        'points': points,
        'point_filter': point_filter,
        'level_filter': level_filter,
        'handled_filter': handled_filter,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
    })


def inspection_create(request):
    if request.method == 'POST':
        form = InspectionRecordForm(request.POST)
        if form.is_valid():
            try:
                insp = form.save(commit=False)
                insp.full_clean()
                insp = form.save()
                return redirect('roads:inspection_detail', pk=insp.pk)
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
    else:
        form = InspectionRecordForm(initial={'inspection_date': timezone.now().date()})
    return render(request, 'roads/inspection_form.html', {'form': form, 'mode': 'create'})


def inspection_detail(request, pk):
    inspection = get_object_or_404(
        InspectionRecord.objects.select_related('point', 'point__road_section'),
        pk=pk
    )
    return render(request, 'roads/inspection_detail.html', {
        'inspection': inspection,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
    })


def inspection_edit(request, pk):
    inspection = get_object_or_404(InspectionRecord, pk=pk)
    if request.method == 'POST':
        form = InspectionRecordForm(request.POST, instance=inspection)
        if form.is_valid():
            try:
                insp = form.save(commit=False)
                insp.full_clean()
                form.save()
                return redirect('roads:inspection_detail', pk=inspection.pk)
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
    else:
        form = InspectionRecordForm(instance=inspection)
    return render(request, 'roads/inspection_form.html', {'form': form, 'inspection': inspection, 'mode': 'edit'})


def inspection_delete(request, pk):
    inspection = get_object_or_404(InspectionRecord, pk=pk)
    point_pk = inspection.point.pk
    if request.method == 'POST':
        inspection.delete()
        return redirect('roads:point_detail', pk=point_pk)
    return render(request, 'roads/inspection_confirm_delete.html', {'inspection': inspection})


# ==================== 风险预警模块 ====================

def alert_list(request):
    level_filter = request.GET.get('level')
    type_filter = request.GET.get('type')
    status_filter = request.GET.get('status')
    road_filter = request.GET.get('road')

    alerts = Alert.objects.select_related('point', 'point__road_section', 'related_inspection').all()

    if level_filter:
        alerts = alerts.filter(alert_level=level_filter)
    if type_filter:
        alerts = alerts.filter(alert_type=type_filter)
    if status_filter == 'unread':
        alerts = alerts.filter(is_read=False)
    elif status_filter == 'unresolved':
        alerts = alerts.filter(is_resolved=False)
    elif status_filter == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    if road_filter:
        alerts = alerts.filter(point__road_section_id=road_filter)

    alerts = alerts.order_by('-created_at')
    roads = RoadSection.objects.all()

    return render(request, 'roads/alert_list.html', {
        'alerts': alerts,
        'roads': roads,
        'level_filter': level_filter,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'road_filter': road_filter,
        'alert_level_choices': dict(ALERT_LEVEL_CHOICES),
        'alert_type_choices': dict(ALERT_TYPE_CHOICES),
    })


def alert_detail(request, pk):
    alert = get_object_or_404(
        Alert.objects.select_related('point', 'point__road_section', 'related_inspection'),
        pk=pk
    )
    if not alert.is_read:
        alert.is_read = True
        alert.save()
    return render(request, 'roads/alert_detail.html', {
        'alert': alert,
        'alert_level_choices': dict(ALERT_LEVEL_CHOICES),
        'alert_type_choices': dict(ALERT_TYPE_CHOICES),
    })


def alert_mark_read(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    alert.is_read = True
    alert.save()
    messages.success(request, '预警已标记为已读。')
    return redirect(request.META.get('HTTP_REFERER', 'roads:alert_list'))


def alert_resolve(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    alert.resolve()
    messages.success(request, '预警已处理完成。')
    return redirect(request.META.get('HTTP_REFERER', 'roads:alert_list'))


def alert_create(request):
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '预警创建成功。')
            return redirect('roads:alert_list')
    else:
        form = AlertForm()
    return render(request, 'roads/alert_form.html', {'form': form, 'mode': 'create'})


def alert_generate_auto(request):
    count = 0
    today = timezone.now().date()

    critical_inspections = InspectionRecord.objects.filter(
        wear_level=4, handled=False
    ).select_related('point')
    for insp in critical_inspections:
        existing = Alert.objects.filter(
            point=insp.point,
            alert_type='wear_critical',
            related_inspection=insp,
            is_resolved=False
        ).exists()
        if not existing:
            Alert.objects.create(
                point=insp.point,
                alert_type='wear_critical',
                alert_level='critical',
                message=f'点位[{insp.point.code}] {insp.point.name} 发现严重磨损（等级4），请立即处理。巡查日期：{insp.inspection_date}，巡查员：{insp.inspector}',
                related_inspection=insp,
            )
            count += 1

    points = Point.objects.all()
    for point in points:
        inspections = list(point.inspections.order_by('inspection_date'))
        if len(inspections) >= 2:
            latest = inspections[-1]
            prev = inspections[-2]
            if latest.wear_level > prev.wear_level and not latest.handled:
                existing = Alert.objects.filter(
                    point=point,
                    alert_type='wear_worsening',
                    related_inspection=latest,
                    is_resolved=False
                ).exists()
                if not existing:
                    Alert.objects.create(
                        point=point,
                        alert_type='wear_worsening',
                        alert_level='warning',
                        message=f'点位[{point.code}] {point.name} 磨损状况恶化：从{prev.get_wear_level_display()}升级为{latest.get_wear_level_display()}。巡查日期：{latest.inspection_date}',
                        related_inspection=latest,
                    )
                    count += 1

    overdue_tasks = TaskOrder.objects.exclude(status='closed').filter(deadline__lt=today)
    for task in overdue_tasks:
        existing = Alert.objects.filter(
            point=task.point,
            alert_type='task_overdue',
            is_resolved=False,
            created_at__date=today
        ).exists()
        if not existing:
            Alert.objects.create(
                point=task.point,
                alert_type='task_overdue',
                alert_level='warning',
                message=f'工单[{task.title}]已超期。指派人：{task.assigned_to or "未指派"}，截止日期：{task.deadline}，当前状态：{task.get_status_display()}',
            )
            count += 1

    thirty_days_ago = today - timedelta(days=30)
    long_unhandled = InspectionRecord.objects.filter(
        handled=False,
        wear_level__gte=3,
        inspection_date__lt=thirty_days_ago
    ).select_related('point')
    for insp in long_unhandled:
        existing = Alert.objects.filter(
            point=insp.point,
            alert_type='unhandled_long',
            related_inspection=insp,
            is_resolved=False
        ).exists()
        if not existing:
            Alert.objects.create(
                point=insp.point,
                alert_type='unhandled_long',
                alert_level='critical' if insp.wear_level == 4 else 'warning',
                message=f'点位[{insp.point.code}] {insp.point.name} 存在{insp.get_wear_level_display()}磨损超过30天未处理。巡查日期：{insp.inspection_date}',
                related_inspection=insp,
            )
            count += 1

    messages.success(request, f'自动生成预警完成，共生成 {count} 条预警。')
    return redirect('roads:alert_list')


# ==================== 整改闭环 / 工单模块 ====================

def task_list(request):
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    road_filter = request.GET.get('road')
    assigned_filter = request.GET.get('assigned')
    overdue_filter = request.GET.get('overdue')

    tasks = TaskOrder.objects.select_related('point', 'point__road_section', 'inspection').all()

    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if road_filter:
        tasks = tasks.filter(point__road_section_id=road_filter)
    if assigned_filter == 'yes':
        tasks = tasks.exclude(assigned_to='')
    elif assigned_filter == 'no':
        tasks = tasks.filter(assigned_to='')
    if overdue_filter == '1':
        today = timezone.now().date()
        tasks = tasks.exclude(status='closed').filter(deadline__lt=today)

    tasks = tasks.order_by('-created_at')
    roads = RoadSection.objects.all()

    stats = {
        'total': tasks.count(),
        'pending': tasks.filter(status='pending').count(),
        'dispatched': tasks.filter(status='dispatched').count(),
        'rectifying': tasks.filter(status='rectifying').count(),
        'pending_review': tasks.filter(status='pending_review').count(),
        'closed': tasks.filter(status='closed').count(),
    }

    return render(request, 'roads/task_list.html', {
        'tasks': tasks,
        'roads': roads,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'road_filter': road_filter,
        'assigned_filter': assigned_filter,
        'overdue_filter': overdue_filter,
        'task_status_choices': dict(TASK_STATUS_CHOICES),
        'stats': stats,
    })


def task_detail(request, pk):
    task = get_object_or_404(
        TaskOrder.objects.select_related('point', 'point__road_section', 'inspection'),
        pk=pk
    )
    photos = Photo.objects.filter(
        point=task.point,
        photo_type__in=['rectification', 'verification']
    ).order_by('-uploaded_at')
    return render(request, 'roads/task_detail.html', {
        'task': task,
        'photos': photos,
        'task_status_choices': dict(TASK_STATUS_CHOICES),
    })


def task_create(request, inspection_pk=None):
    initial = {}
    if inspection_pk:
        inspection = get_object_or_404(InspectionRecord, pk=inspection_pk)
        initial['inspection'] = inspection
        initial['point'] = inspection.point
        initial['title'] = f'{inspection.point.code} - {inspection.get_wear_level_display()}磨损整改'
        initial['description'] = inspection.maintenance_suggestion or inspection.wear_description
        if inspection.wear_level == 4:
            initial['priority'] = 'urgent'
        elif inspection.wear_level == 3:
            initial['priority'] = 'high'

    if request.method == 'POST':
        form = TaskOrderForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.status = 'pending'
            task.save()
            messages.success(request, '工单创建成功，等待派发。')
            return redirect('roads:task_detail', pk=task.pk)
    else:
        form = TaskOrderForm(initial=initial)
    return render(request, 'roads/task_form.html', {'form': form, 'mode': 'create'})


def task_dispatch(request, pk):
    task = get_object_or_404(TaskOrder, pk=pk)
    if task.status not in ['pending', 'rejected']:
        messages.error(request, '当前状态不允许派发。')
        return redirect('roads:task_detail', pk=pk)

    if request.method == 'POST':
        form = TaskDispatchForm(request.POST, instance=task)
        if form.is_valid():
            t = form.save(commit=False)
            t.status = 'dispatched'
            t.dispatched_at = timezone.now()
            t.save()
            messages.success(request, f'工单已派发给 {t.assigned_to or "相关人员"}。')
            return redirect('roads:task_detail', pk=task.pk)
    else:
        form = TaskDispatchForm(instance=task, initial={
            'deadline': task.deadline or (timezone.now().date() + timedelta(days=7)),
            'priority': task.priority,
        })
    return render(request, 'roads/task_dispatch.html', {'form': form, 'task': task})


def task_rectify(request, pk):
    task = get_object_or_404(TaskOrder, pk=pk)
    if task.status not in ['dispatched', 'rectifying']:
        messages.error(request, '当前状态不允许提交整改。')
        return redirect('roads:task_detail', pk=pk)

    if request.method == 'POST':
        form = TaskRectifyForm(request.POST, instance=task)
        if form.is_valid():
            t = form.save(commit=False)
            if t.status == 'dispatched':
                t.status = 'rectifying'
            if t.rectification_result and t.rectification_result.strip():
                t.status = 'pending_review'
                t.rectified_at = timezone.now()
            t.save()
            messages.success(request, '整改信息已提交。' if t.status == 'rectifying' else '整改结果已提交，等待复核。')
            return redirect('roads:task_detail', pk=task.pk)
    else:
        form = TaskRectifyForm(instance=task)
    return render(request, 'roads/task_rectify.html', {'form': form, 'task': task})


def task_review(request, pk):
    task = get_object_or_404(TaskOrder, pk=pk)
    if task.status != 'pending_review':
        messages.error(request, '当前状态不允许复核。')
        return redirect('roads:task_detail', pk=pk)

    if request.method == 'POST':
        form = TaskReviewForm(request.POST, instance=task)
        action = request.POST.get('action')
        if form.is_valid():
            t = form.save(commit=False)
            t.reviewed_at = timezone.now()
            if action == 'pass':
                t.status = 'closed'
                t.closed_at = timezone.now()
                if t.inspection and not t.inspection.handled:
                    t.inspection.handled = True
                    t.inspection.handled_date = timezone.now().date()
                    t.inspection.save()
                messages.success(request, '复核通过，工单已闭环。')
            else:
                t.status = 'rejected'
                messages.warning(request, '复核不通过，请重新整改。')
            t.save()
            return redirect('roads:task_detail', pk=task.pk)
    else:
        form = TaskReviewForm(instance=task)
    return render(request, 'roads/task_review.html', {'form': form, 'task': task})


def task_status_progress(request, pk):
    task = get_object_or_404(TaskOrder, pk=pk)
    new_status = request.POST.get('status')
    valid_transitions = {
        'dispatched': 'rectifying',
    }
    if new_status in valid_transitions.values() and task.status == 'dispatched':
        task.status = new_status
        task.save()
        messages.success(request, '工单状态已更新。')
    else:
        messages.error(request, '无效的状态转换。')
    return redirect('roads:task_detail', pk=pk)


# ==================== 照片档案模块 ====================

def photo_list(request):
    point_filter = request.GET.get('point')
    type_filter = request.GET.get('type')
    road_filter = request.GET.get('road')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    photos = Photo.objects.select_related('point', 'point__road_section', 'inspection').all()

    if point_filter:
        photos = photos.filter(point_id=point_filter)
    if type_filter:
        photos = photos.filter(photo_type=type_filter)
    if road_filter:
        photos = photos.filter(point__road_section_id=road_filter)
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            photos = photos.filter(uploaded_at__date__gte=d)
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            photos = photos.filter(uploaded_at__date__lte=d)
        except ValueError:
            pass

    photos = photos.order_by('-uploaded_at')
    roads = RoadSection.objects.all()
    points = Point.objects.all().order_by('code')

    return render(request, 'roads/photo_list.html', {
        'photos': photos,
        'roads': roads,
        'points': points,
        'point_filter': point_filter,
        'type_filter': type_filter,
        'road_filter': road_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


def photo_upload(request):
    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save()
            if not photo.taken_at:
                photo.taken_at = timezone.now().date()
                photo.save()
            messages.success(request, '照片上传成功。')
            return redirect('roads:photo_list')
    else:
        form = PhotoForm(initial={'taken_at': timezone.now().date()})
    return render(request, 'roads/photo_upload.html', {'form': form})


def photo_detail(request, pk):
    photo = get_object_or_404(
        Photo.objects.select_related('point', 'point__road_section', 'inspection'),
        pk=pk
    )
    related_photos = Photo.objects.filter(point=photo.point).exclude(pk=pk).order_by('-uploaded_at')[:6]
    return render(request, 'roads/photo_detail.html', {
        'photo': photo,
        'related_photos': related_photos,
    })


def photo_delete(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    if request.method == 'POST':
        photo.delete()
        messages.success(request, '照片已删除。')
        return redirect('roads:photo_list')
    return render(request, 'roads/photo_confirm_delete.html', {'photo': photo})


# ==================== 增强地图：时间轴磨损演变 ====================

def api_points_geo_timeline(request):
    date_str = request.GET.get('date')
    high_risk = request.GET.get('high_risk', '0') == '1'

    points = Point.objects.select_related('road_section').all()
    if high_risk:
        points = points.filter(
            inspections__wear_level__gte=3,
            inspections__handled=False
        ).distinct()

    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = None

    features = []
    for point in points:
        if target_date:
            inspections_before = point.inspections.filter(
                inspection_date__lte=target_date
            ).order_by('-inspection_date')
            latest_at_time = inspections_before.first()
            unhandled_at_time = inspections_before.filter(handled=False).order_by('-wear_level', '-inspection_date').first()
            wear_level = unhandled_at_time.wear_level if unhandled_at_time else None
            is_high = unhandled_at_time and unhandled_at_time.wear_level >= 3
            latest_wear = latest_at_time.wear_level if latest_at_time else None
            latest_wear_display = dict(WEAR_LEVEL_CHOICES).get(latest_wear, '无记录') if latest_at_time else '无记录'
            handled = unhandled_at_time is None
            wear_display = dict(WEAR_LEVEL_CHOICES).get(wear_level, '无未处理记录')
        else:
            worst = point.get_worst_unhandled_inspection()
            latest = point.get_latest_inspection()
            wear_level = worst.wear_level if worst else None
            is_high = point.is_high_risk()
            latest_wear = latest.wear_level if latest else None
            latest_wear_display = dict(WEAR_LEVEL_CHOICES).get(latest_wear, '无记录') if latest else '无记录'
            handled = worst is None
            wear_display = dict(WEAR_LEVEL_CHOICES).get(wear_level, '无未处理记录')

        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [point.longitude, point.latitude],
            },
            'properties': {
                'id': point.id,
                'code': point.code,
                'name': point.name,
                'point_type': point.point_type,
                'point_type_display': point.get_point_type_display(),
                'road_section': point.road_section.name,
                'road_section_id': point.road_section.id,
                'wear_level': wear_level,
                'wear_level_display': wear_display,
                'is_high_risk': is_high,
                'handled': handled,
                'has_latest': latest_wear is not None,
                'latest_wear_level': latest_wear,
                'latest_wear_display': latest_wear_display,
            }
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
    })


# ==================== 趋势分析：点位磨损演变追踪 ====================

def api_point_wear_history(request, point_pk):
    point = get_object_or_404(Point, pk=point_pk)
    inspections = point.inspections.order_by('inspection_date')

    labels = []
    wear_data = []
    inspections_detail = []
    for insp in inspections:
        labels.append(insp.inspection_date.strftime('%Y-%m-%d'))
        wear_data.append(insp.wear_level)
        inspections_detail.append({
            'id': insp.id,
            'inspection_date': insp.inspection_date.strftime('%Y-%m-%d'),
            'wear_level': insp.wear_level,
            'wear_level_display': dict(WEAR_LEVEL_CHOICES).get(insp.wear_level, '未知'),
            'inspector': insp.inspector,
            'handled': insp.handled,
        })

    return JsonResponse({
        'point': {
            'id': point.id,
            'code': point.code,
            'name': point.name,
            'road': point.road_section.name,
        },
        'labels': labels,
        'wear_data': wear_data,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
        'inspections': inspections_detail,
    })


# ==================== 维护优先级清单 ====================

def priority_list(request):
    unhandled = InspectionRecord.objects.filter(handled=False).select_related(
        'point', 'point__road_section'
    ).order_by('-wear_level', 'inspection_date')

    priority_items = []
    for insp in unhandled:
        days_pending = (timezone.now().date() - insp.inspection_date).days
        priority_score = insp.wear_level * 100 + days_pending

        if insp.wear_level == 4:
            priority = '紧急'
            priority_class = 'danger'
        elif insp.wear_level == 3:
            priority = '高'
            priority_class = 'warning'
        elif insp.wear_level == 2:
            priority = '中'
            priority_class = 'info'
        else:
            priority = '低'
            priority_class = 'secondary'

        has_task = TaskOrder.objects.filter(
            inspection=insp
        ).exclude(status='closed').exists()

        priority_items.append({
            'inspection': insp,
            'priority': priority,
            'priority_class': priority_class,
            'priority_score': priority_score,
            'days_pending': days_pending,
            'has_task': has_task,
        })

    priority_items.sort(key=lambda x: x['priority_score'], reverse=True)

    stats = {
        'urgent': sum(1 for p in priority_items if p['priority'] == '紧急'),
        'high': sum(1 for p in priority_items if p['priority'] == '高'),
        'medium': sum(1 for p in priority_items if p['priority'] == '中'),
        'low': sum(1 for p in priority_items if p['priority'] == '低'),
        'with_task': sum(1 for p in priority_items if p['has_task']),
        'total': len(priority_items),
    }
    stats['without_task'] = stats['total'] - stats['with_task']

    return render(request, 'roads/priority_list.html', {
        'priority_items': priority_items,
        'stats': stats,
    })


# ==================== 数据导出模块 ====================

def export_page(request):
    if request.method == 'POST':
        form = DataExportForm(request.POST)
        if form.is_valid():
            return _do_export(form)
    else:
        form = DataExportForm()
    return render(request, 'roads/export.html', {'form': form})


def _do_export(form):
    export_type = form.cleaned_data['export_type']
    export_format = form.cleaned_data['export_format']
    road_section = form.cleaned_data.get('road_section')
    date_from = form.cleaned_data.get('date_from')
    date_to = form.cleaned_data.get('date_to')

    if export_type == 'inspections':
        qs = InspectionRecord.objects.select_related('point', 'point__road_section').all()
        if road_section:
            qs = qs.filter(point__road_section=road_section)
        if date_from:
            qs = qs.filter(inspection_date__gte=date_from)
        if date_to:
            qs = qs.filter(inspection_date__lte=date_to)
        headers = ['路段', '点位编号', '点位名称', '巡查日期', '巡查人员', '磨损等级', '磨损描述', '维护建议', '是否已处理', '处理日期']
        rows = []
        for r in qs:
            rows.append([
                r.point.road_section.name,
                r.point.code,
                r.point.name,
                r.inspection_date.strftime('%Y-%m-%d'),
                r.inspector,
                r.get_wear_level_display(),
                r.wear_description or '',
                r.maintenance_suggestion or '',
                '是' if r.handled else '否',
                r.handled_date.strftime('%Y-%m-%d') if r.handled_date else '',
            ])
        filename = f'inspections_{timezone.now().strftime("%Y%m%d%H%M%S")}'

    elif export_type == 'points':
        qs = Point.objects.select_related('road_section').all()
        if road_section:
            qs = qs.filter(road_section=road_section)
        headers = ['路段', '点位编号', '点位名称', '类型', '纬度', '经度', '描述', '当前磨损等级', '是否高风险']
        rows = []
        for p in qs:
            wl = p.get_current_wear_level()
            rows.append([
                p.road_section.name,
                p.code,
                p.name,
                p.get_point_type_display(),
                p.latitude,
                p.longitude,
                p.description or '',
                dict(WEAR_LEVEL_CHOICES).get(wl, '无记录'),
                '是' if p.is_high_risk() else '否',
            ])
        filename = f'points_{timezone.now().strftime("%Y%m%d%H%M%S")}'

    elif export_type == 'tasks':
        qs = TaskOrder.objects.select_related('point', 'point__road_section', 'inspection').all()
        if road_section:
            qs = qs.filter(point__road_section=road_section)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        headers = ['工单标题', '路段', '点位', '状态', '优先级', '指派人员', '整改期限', '创建时间', '派发时间', '整改完成时间', '复核时间', '闭环时间', '是否超期']
        rows = []
        for t in qs:
            rows.append([
                t.title,
                t.point.road_section.name,
                t.point.code + ' ' + t.point.name,
                t.get_status_display(),
                t.get_priority_display(),
                t.assigned_to or '',
                t.deadline.strftime('%Y-%m-%d') if t.deadline else '',
                t.created_at.strftime('%Y-%m-%d %H:%M'),
                t.dispatched_at.strftime('%Y-%m-%d %H:%M') if t.dispatched_at else '',
                t.rectified_at.strftime('%Y-%m-%d %H:%M') if t.rectified_at else '',
                t.reviewed_at.strftime('%Y-%m-%d %H:%M') if t.reviewed_at else '',
                t.closed_at.strftime('%Y-%m-%d %H:%M') if t.closed_at else '',
                '是' if t.is_overdue() else '否',
            ])
        filename = f'tasks_{timezone.now().strftime("%Y%m%d%H%M%S")}'

    else:
        qs = Alert.objects.select_related('point', 'point__road_section').all()
        if road_section:
            qs = qs.filter(point__road_section=road_section)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        headers = ['预警类型', '预警等级', '路段', '点位', '预警信息', '是否已读', '是否已处理', '创建时间', '处理时间']
        rows = []
        for a in qs:
            rows.append([
                a.get_alert_type_display(),
                a.get_alert_level_display(),
                a.point.road_section.name,
                a.point.code + ' ' + a.point.name,
                a.message,
                '是' if a.is_read else '否',
                '是' if a.is_resolved else '否',
                a.created_at.strftime('%Y-%m-%d %H:%M'),
                a.resolved_at.strftime('%Y-%m-%d %H:%M') if a.resolved_at else '',
            ])
        filename = f'alerts_{timezone.now().strftime("%Y%m%d%H%M%S")}'

    if export_format == 'csv':
        return _export_csv(headers, rows, filename)
    else:
        return _export_xlsx(headers, rows, filename)


def _export_csv(headers, rows, filename):
    buffer = io.StringIO()
    buffer.write('\ufeff')
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    return response


def _export_xlsx(headers, rows, filename):
    wb = Workbook()
    ws = wb.active
    ws.title = '数据导出'

    header_fill = PatternFill(start_color='5c4033', end_color='5c4033', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(vertical='center')
            cell.border = thin_border

    for col_idx in range(1, len(headers) + 1):
        max_length = len(str(headers[col_idx - 1]))
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            for cell in row:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_length + 4, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return response
