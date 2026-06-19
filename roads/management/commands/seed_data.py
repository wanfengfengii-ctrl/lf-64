from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from roads.models import RoadSection, Point, InspectionRecord
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

        self.stdout.write(self.style.SUCCESS(f'成功创建 {len(roads)} 条路段、{len(points)} 个点位、{total} 条巡查记录'))
