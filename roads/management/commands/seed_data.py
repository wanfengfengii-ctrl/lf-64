from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from roads.models import (
    RoadSection, Point, InspectionRecord,
    Hazard, HazardDisposal, RoadPassageStatus,
    HAZARD_LOCATION_TYPE_CHOICES, HAZARD_TYPE_CHOICES,
    HAZARD_LEVEL_CHOICES, HAZARD_STATUS_CHOICES,
    CONTROL_SUGGESTION_CHOICES, PASSAGE_STATUS_CHOICES,
    DISPOSAL_TYPE_CHOICES,
)
import random


class Command(BaseCommand):
    help = '生成示例数据用于演示'

    def handle(self, *args, **options):
        self.stdout.write('开始生成示例数据...')

        RoadSection.objects.all().delete()

        roads_data = [
            {
                'name': '梅关古道',
                'code': 'MG-001',
                'start_location': '广东省南雄市珠玑镇',
                'end_location': '江西省大余县梅关镇',
                'length_km': 8.5,
                'historical_info': '梅关古道是古代连接中原与岭南的重要通道，始建于秦朝，唐开元年间张九龄奉诏开凿扩建，是保存最完整的古驿道之一。',
                'status': 'warning'
            },
            {
                'name': '西京古道',
                'code': 'XJ-001',
                'start_location': '广东省乳源瑶族自治县大桥镇',
                'end_location': '湖南省宜章县',
                'length_km': 15.2,
                'historical_info': '西京古道始建于汉武帝时期，是岭南通往古都长安的重要通道，距今已有2000多年历史。',
                'status': 'critical'
            },
            {
                'name': '潮惠古道',
                'code': 'CH-001',
                'start_location': '广东省潮州市',
                'end_location': '广东省惠州市',
                'length_km': 22.8,
                'historical_info': '潮惠古道是古代连接潮州与惠州的商贸通道，沿途保存有大量明清时期的石阶和路碑。',
                'status': 'good'
            },
        ]

        points_data = [
            {'road_idx': 0, 'code': 'MG-SS-001', 'name': '关楼前石阶', 'type': 'stone_step', 'lat': 25.4123, 'lon': 114.3256, 'desc': '梅关关楼北侧主要石阶，人流量大。'},
            {'road_idx': 0, 'code': 'MG-LB-001', 'name': '梅关碑刻', 'type': 'road_stele', 'lat': 25.4118, 'lon': 114.3262, 'desc': '明代万历年间所立路碑。'},
            {'road_idx': 0, 'code': 'MG-PS-002', 'name': '半山石阶段', 'type': 'stone_step', 'lat': 25.4095, 'lon': 114.3278, 'desc': '坡度较陡，约500米。'},
            {'road_idx': 0, 'code': 'MG-PS-003', 'name': '古道南段石阶', 'type': 'stone_step', 'lat': 25.4068, 'lon': 114.3301, 'desc': ''},
            {'road_idx': 0, 'code': 'MG-PS-004', 'name': '接岭桥排水沟', 'type': 'drainage', 'lat': 25.4082, 'lon': 114.3289, 'desc': '桥旁排水设施，雨季易堵塞。'},
            {'road_idx': 0, 'code': 'MG-LB-002', 'name': '重修古道碑', 'type': 'road_stele', 'lat': 25.4105, 'lon': 114.3270, 'desc': '清代乾隆年间重修纪念碑。'},

            {'road_idx': 1, 'code': 'XJ-SS-001', 'name': '大桥镇入口石阶', 'type': 'stone_step', 'lat': 24.8856, 'lon': 113.2567, 'desc': '西京古道乳源段起点。'},
            {'road_idx': 1, 'code': 'XJ-SS-002', 'name': '猴子岭石阶', 'type': 'stone_step', 'lat': 24.8923, 'lon': 113.2489, 'desc': '坡度约30度，部分石阶断裂。'},
            {'road_idx': 1, 'code': 'XJ-PS-003', 'name': '心韩亭附近石阶', 'type': 'stone_step', 'lat': 24.8978, 'lon': 113.2412, 'desc': ''},
            {'road_idx': 1, 'code': 'XJ-LB-001', 'name': '古道里程碑', 'type': 'road_stele', 'lat': 24.8901, 'lon': 113.2534, 'desc': '刻有"西京古道"字样。'},
            {'road_idx': 1, 'code': 'XJ-PS-004', 'name': '红豆杉公园段', 'type': 'stone_step', 'lat': 24.9012, 'lon': 113.2356, 'desc': ''},
            {'road_idx': 1, 'code': 'XJ-PS-005', 'name': '梯云岭石阶', 'type': 'stone_step', 'lat': 24.9056, 'lon': 113.2289, 'desc': '最险峻的一段，部分塌陷。'},
            {'road_idx': 1, 'code': 'XJ-PS-006', 'name': '凉轿石段排水沟', 'type': 'drainage', 'lat': 24.8945, 'lon': 113.2456, 'desc': ''},

            {'road_idx': 2, 'code': 'CH-SS-001', 'name': '潮州古城起点', 'type': 'stone_step', 'lat': 23.6612, 'lon': 116.6223, 'desc': '位于潮州市老城区。'},
            {'road_idx': 2, 'code': 'CH-SS-002', 'name': '意溪镇石阶', 'type': 'stone_step', 'lat': 23.6845, 'lon': 116.6534, 'desc': ''},
            {'road_idx': 2, 'code': 'CH-LB-001', 'name': '分水关路碑', 'type': 'road_stele', 'lat': 23.5890, 'lon': 116.4567, 'desc': '古潮州府与惠州府分界碑。'},
            {'road_idx': 2, 'code': 'CH-PS-003', 'name': '三寮村段', 'type': 'stone_step', 'lat': 23.5234, 'lon': 116.3890, 'desc': ''},
            {'road_idx': 2, 'code': 'CH-PS-004', 'name': '高潭镇石阶', 'type': 'stone_step', 'lat': 23.4567, 'lon': 116.2345, 'desc': ''},
            {'road_idx': 2, 'code': 'CH-PS-005', 'name': '多祝镇排水沟', 'type': 'drainage', 'lat': 23.3890, 'lon': 116.1234, 'desc': ''},
            {'road_idx': 2, 'code': 'CH-LB-002', 'name': '惠州府界碑', 'type': 'road_stele', 'lat': 23.1234, 'lon': 114.6789, 'desc': ''},
        ]

        today = timezone.now().date()
        inspectors = ['张三', '李四', '王五', '赵六', '陈七']
        wear_descriptions = {
            1: ['表面轻微磨损，整体状况良好。', '边缘略有磨损，不影响使用。'],
            2: ['表面出现明显磨损痕迹，部分区域凹陷。', '局部有裂纹，但结构尚稳定。'],
            3: ['磨损较为严重，多处出现断裂。', '凹陷深度超过2厘米，需要尽快修复。', '排水沟部分堵塞，排水不畅。'],
            4: ['严重破损，存在安全隐患，需立即处理。', '大面积断裂塌陷，无法正常通行。', '路碑严重风化，字迹模糊不清。']
        }
        maintenance_suggestions = {
            3: ['建议在3个月内安排局部修补。', '建议加强排水设施清理。'],
            4: ['需立即封闭该段并进行全面修缮。', '建议立项进行整体改造，预计工期2周。', '应立即设置警示标志，并安排专业队伍评估。']
        }

        roads = []
        for r_data in roads_data:
            road = RoadSection.objects.create(**r_data)
            roads.append(road)
            self.stdout.write(f'  创建路段: {road.code} - {road.name}')

        points = []
        for p_data in points_data:
            point = Point.objects.create(
                road_section=roads[p_data['road_idx']],
                code=p_data['code'],
                name=p_data['name'],
                point_type=p_data['type'],
                latitude=p_data['lat'],
                longitude=p_data['lon'],
                description=p_data['desc']
            )
            points.append(point)
            self.stdout.write(f'  创建点位: {point.code} - {point.name}')

        total = 0
        for point in points:
            inspection_count = random.randint(2, 6)
            used_dates = set()

            for i in range(inspection_count):
                days_ago = random.randint(0, 300)
                insp_date = today - timedelta(days=days_ago)

                date_key = insp_date.isoformat()
                if date_key in used_dates:
                    continue
                used_dates.add(date_key)

                wear_level = random.choices([1, 2, 3, 4], weights=[0.35, 0.30, 0.22, 0.13])[0]
                handled = random.random() < 0.55 if wear_level >= 3 else random.random() < 0.8

                insp = InspectionRecord(
                    point=point,
                    inspection_date=insp_date,
                    inspector=random.choice(inspectors),
                    wear_level=wear_level,
                    wear_description=random.choice(wear_descriptions[wear_level]),
                    handled=handled,
                    handled_date=insp_date + timedelta(days=random.randint(3, 30)) if handled else None
                )

                if wear_level >= 3:
                    insp.maintenance_suggestion = random.choice(maintenance_suggestions[wear_level])

                insp.save()
                total += 1

        for road in roads:
            try:
                road.full_clean()
                road.save()
            except Exception:
                pass

        self.stdout.write('  正在生成灾害隐患示例数据...')

        hazard_templates = [
            {
                'title': '边坡塌方隐患',
                'location_type': 'slope',
                'hazard_type': 'landslide',
                'description': '梅关古道北侧边坡出现土壤松动，近期降雨频繁，有小型塌方风险。',
                'level': 'severe',
                'status': 'disposing',
                'control': 'single_lane',
                'passage': 'restricted',
                'affected_length': 35,
            },
            {
                'title': '排水沟堵塞积水',
                'location_type': 'drainage',
                'hazard_type': 'waterlogging',
                'description': '接岭桥排水沟因落叶和泥沙淤积导致排水不畅，雨天路面积水严重。',
                'level': 'warning',
                'status': 'pending_disposal',
                'control': 'caution',
                'passage': 'caution',
                'affected_length': 20,
            },
            {
                'title': '石阶断裂沉降',
                'location_type': 'stone_step',
                'hazard_type': 'subsidence',
                'description': '猴子岭石阶中段约5米范围出现地基沉降，石阶断裂错位，存在安全隐患。',
                'level': 'critical',
                'status': 'assessing',
                'control': 'full_closure',
                'passage': 'closed',
                'affected_length': 15,
            },
            {
                'title': '桥涵底部冲刷',
                'location_type': 'bridge_culvert',
                'hazard_type': 'erosion',
                'description': '接岭桥桥墩底部受水流冲刷，基础部分裸露，需加固处理。',
                'level': 'severe',
                'status': 'monitoring',
                'control': 'speed_limit',
                'passage': 'restricted',
                'affected_length': 10,
            },
            {
                'title': '落石风险区',
                'location_type': 'slope',
                'hazard_type': 'rockfall',
                'description': '梯云岭路段东侧边坡岩石风化严重，时有小石块滚落，威胁行人安全。',
                'level': 'warning',
                'status': 'reported',
                'control': 'caution',
                'passage': 'caution',
                'affected_length': 50,
            },
            {
                'title': '挡土墙变形',
                'location_type': 'retaining_wall',
                'hazard_type': 'deformation',
                'description': '红豆杉公园段挡土墙出现轻微倾斜和裂缝，需持续监测。',
                'level': 'warning',
                'status': 'monitoring',
                'control': 'caution',
                'passage': 'caution',
                'affected_length': 25,
            },
            {
                'title': '涵洞堵塞',
                'location_type': 'tunnel',
                'hazard_type': 'blockage',
                'description': '三寮村段涵洞被淤泥和杂物堵塞，排水能力下降。',
                'level': 'info',
                'status': 'resolved',
                'control': 'none',
                'passage': 'normal',
                'affected_length': 8,
            },
            {
                'title': '路面湿滑',
                'location_type': 'road_surface',
                'hazard_type': 'slippery',
                'description': '潮州古城起点附近路段因苔藓生长，雨天路面异常湿滑。',
                'level': 'warning',
                'status': 'pending_disposal',
                'control': 'caution',
                'passage': 'caution',
                'affected_length': 30,
            },
            {
                'title': '边坡开裂',
                'location_type': 'slope',
                'hazard_type': 'fracture',
                'description': '高潭镇北侧边坡出现多条纵向裂缝，宽度约2-5厘米，有滑坡风险。',
                'level': 'critical',
                'status': 'disposing',
                'control': 'detour',
                'passage': 'detour',
                'affected_length': 40,
            },
            {
                'title': '路面沉降',
                'location_type': 'road_surface',
                'hazard_type': 'subsidence',
                'description': '多祝镇段路面出现不均匀沉降，形成约15厘米的落差。',
                'level': 'severe',
                'status': 'reported',
                'control': 'speed_limit',
                'passage': 'restricted',
                'affected_length': 12,
            },
        ]

        road_point_map = {
            0: [0, 4],
            1: [1, 4, 6, 10],
            2: [0, 4, 7],
        }

        hazard_count = 0
        disposal_count = 0
        reporters = ['巡查队王队', '养护组李工', '安全监察张工', '村民报告', '游客反馈']

        for idx, tmpl in enumerate(hazard_templates):
            road_idx = idx % 3
            road = roads[road_idx]
            
            point_indices = road_point_map.get(road_idx, [0])
            point = points[point_indices[idx % len(point_indices)]] if point_indices else None

            days_ago = random.randint(1, 60)
            reported_date = today - timedelta(days=days_ago)
            reported_at = timezone.make_aware(
                timezone.datetime.combine(reported_date, timezone.datetime.min.time())
            ) + timedelta(hours=random.randint(6, 18))

            try:
                hazard = Hazard.objects.create(
                    road_section=road,
                    point=point,
                    title=tmpl['title'],
                    location_type=tmpl['location_type'],
                    hazard_type=tmpl['hazard_type'],
                    hazard_level=tmpl['level'],
                    status=tmpl['status'],
                    description=tmpl['description'],
                    latitude=point.latitude if point else (road.points.first().latitude if road.points.exists() else None),
                    longitude=point.longitude if point else (road.points.first().longitude if road.points.exists() else None),
                    location_desc=f'{road.name} {point.name if point else ""}附近',
                    reported_by=random.choice(reporters),
                    reported_at=reported_at,
                    reported_date=reported_date,
                    control_suggestion=tmpl['control'],
                    passage_status=tmpl['passage'],
                    assess_note='经现场勘查，该隐患符合上述等级评定标准。' if tmpl['status'] not in ['reported'] else '',
                    assessed_by='评估组' if tmpl['status'] not in ['reported'] else '',
                    assessed_at=reported_at + timedelta(hours=random.randint(2, 24)) if tmpl['status'] not in ['reported'] else None,
                    disposal_deadline=reported_date + timedelta(days=random.randint(3, 30)) if tmpl['status'] not in ['resolved', 'closed'] else None,
                    affected_length_m=tmpl['affected_length'],
                )
                hazard_count += 1

                if tmpl['status'] != 'reported':
                    HazardDisposal.objects.create(
                        hazard=hazard,
                        disposal_type='reported',
                        status_before='reported',
                        status_after=tmpl['status'],
                        level_before='info',
                        level_after=tmpl['level'],
                        passage_before='normal',
                        passage_after=tmpl['passage'],
                        description=f'隐患已上报，描述：{tmpl["description"]}',
                        disposed_by=random.choice(reporters),
                        disposed_at=reported_at,
                        is_active=True,
                    )
                    disposal_count += 1

                if tmpl['status'] in ['assessing', 'pending_disposal', 'disposing', 'monitoring', 'resolved', 'closed']:
                    assess_time = reported_at + timedelta(hours=random.randint(3, 48))
                    HazardDisposal.objects.create(
                        hazard=hazard,
                        disposal_type='assessed',
                        status_before='reported',
                        status_after='pending_disposal',
                        level_before='info',
                        level_after=tmpl['level'],
                        passage_before='normal',
                        passage_after=tmpl['passage'],
                        description=f'完成隐患等级评估，评定为{dict(HAZARD_LEVEL_CHOICES).get(tmpl["level"], "")}。',
                        disposed_by='评估组',
                        disposed_at=assess_time,
                        disposal_result=f'封控建议：{dict(CONTROL_SUGGESTION_CHOICES).get(tmpl["control"], "")}',
                        next_step='按处置方案开展处置工作',
                        is_active=True,
                    )
                    disposal_count += 1

                if tmpl['status'] in ['disposing', 'monitoring', 'resolved', 'closed']:
                    dispose_time = assess_time + timedelta(days=random.randint(1, 10))
                    HazardDisposal.objects.create(
                        hazard=hazard,
                        disposal_type='onsite',
                        status_before='pending_disposal',
                        status_after='disposing',
                        level_before=tmpl['level'],
                        level_after=tmpl['level'],
                        passage_before=tmpl['passage'],
                        passage_after=tmpl['passage'],
                        description='现场处置队伍已进场，开展应急处置工作。',
                        disposed_by='应急处置组',
                        disposed_at=dispose_time,
                        disposal_result='设置警示标志，疏散周边人员',
                        next_step='继续实施加固/清理工作',
                        is_active=True,
                    )
                    disposal_count += 1

                if tmpl['status'] in ['resolved', 'closed']:
                    resolve_time = dispose_time + timedelta(days=random.randint(3, 15))
                    HazardDisposal.objects.create(
                        hazard=hazard,
                        disposal_type='inspected',
                        status_before='disposing',
                        status_after='resolved',
                        level_before=tmpl['level'],
                        level_after='safe',
                        passage_before=tmpl['passage'],
                        passage_after='normal',
                        description='隐患已消除，经复核验收合格。',
                        disposed_by='复核验收组',
                        disposed_at=resolve_time,
                        disposal_result='隐患消除，恢复正常通行',
                        next_step='纳入日常巡查监测',
                        is_active=True,
                    )
                    disposal_count += 1
                    hazard.resolved_at = resolve_time
                    hazard.save()

                if tmpl['status'] == 'closed':
                    close_time = resolve_time + timedelta(days=random.randint(1, 3))
                    HazardDisposal.objects.create(
                        hazard=hazard,
                        disposal_type='closed',
                        status_before='resolved',
                        status_after='closed',
                        level_before='safe',
                        level_after='safe',
                        passage_before='normal',
                        passage_after='normal',
                        description='完成闭环归档。',
                        disposed_by='系统管理员',
                        disposed_at=close_time,
                        disposal_result='闭环归档完成',
                        is_active=True,
                    )
                    disposal_count += 1
                    hazard.closed_at = close_time
                    hazard.closed_by = '系统管理员'
                    hazard.save()

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  创建隐患失败: {e}'))
                continue

        self.stdout.write('  正在初始化路段通行状态...')
        for road in roads:
            RoadPassageStatus.objects.get_or_create(road_section=road)

        for ps in RoadPassageStatus.objects.all():
            ps.recalculate_from_hazards()

        self.stdout.write(self.style.SUCCESS(
            f'成功创建 {len(roads)} 条路段、{len(points)} 个点位、{total} 条巡查记录、'
            f'{hazard_count} 条灾害隐患、{disposal_count} 条处置记录'
        ))
