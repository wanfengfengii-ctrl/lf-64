from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, date
from collections import defaultdict

from .models import RoadSection, Point, InspectionRecord, WEAR_LEVEL_CHOICES, POINT_TYPE_CHOICES
from .forms import RoadSectionForm, PointForm, InspectionRecordForm


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

    recent_inspections = InspectionRecord.objects.select_related('point', 'point__road_section').order_by('-inspection_date')[:10]

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

    return render(request, 'roads/dashboard.html', {
        'total_roads': total_roads,
        'total_points': total_points,
        'total_inspections': total_inspections,
        'high_risk_points': high_risk_points,
        'critical_points': critical_points,
        'recent_inspections': recent_inspections,
        'roads_with_issues': roads_with_issues,
        'wear_stats_list': wear_stats_list,
    })


def map_view(request):
    high_risk = request.GET.get('high_risk', '0') == '1'
    points = Point.objects.select_related('road_section').all()
    if high_risk:
        points = points.filter(
            inspections__wear_level__gte=3,
            inspections__handled=False
        ).distinct()

    return render(request, 'roads/map.html', {
        'points': points,
        'high_risk_filter': high_risk,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
        'point_type_choices': dict(POINT_TYPE_CHOICES),
    })


def charts_view(request):
    roads = RoadSection.objects.all()
    selected_road_id = request.GET.get('road_id')
    months_count = int(request.GET.get('months', '6'))

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
        'selected_road_id': int(selected_road_id) if selected_road_id else None,
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
        latest = point.get_latest_inspection()
        wear_level = latest.wear_level if latest else None
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
                'wear_level_display': dict(WEAR_LEVEL_CHOICES).get(wear_level, '无记录'),
                'is_high_risk': is_high,
                'handled': latest.handled if latest else True,
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
    points = road.points.annotate(
        has_critical=Count('inspections', filter=Q(
            inspections__wear_level=4,
            inspections__handled=False
        ))
    ).all()
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
            point = form.save()
            return redirect('roads:point_detail', pk=point.pk)
    else:
        form = PointForm()
    return render(request, 'roads/point_form.html', {'form': form, 'mode': 'create'})


def point_detail(request, pk):
    point = get_object_or_404(Point.objects.select_related('road_section').prefetch_related('inspections'), pk=pk)
    inspections = point.inspections.all().order_by('-inspection_date')
    return render(request, 'roads/point_detail.html', {
        'point': point,
        'inspections': inspections,
        'wear_level_choices': dict(WEAR_LEVEL_CHOICES),
    })


def point_edit(request, pk):
    point = get_object_or_404(Point, pk=pk)
    if request.method == 'POST':
        form = PointForm(request.POST, instance=point)
        if form.is_valid():
            form.save()
            return redirect('roads:point_detail', pk=point.pk)
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
            inspection = form.save()
            return redirect('roads:inspection_detail', pk=inspection.pk)
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
            form.save()
            return redirect('roads:inspection_detail', pk=inspection.pk)
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
