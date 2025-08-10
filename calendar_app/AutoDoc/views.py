from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
import requests
from datetime import datetime, timedelta, date
import calendar
from django.urls import reverse
import logging
import json
from itertools import groupby
from operator import itemgetter


logger = logging.getLogger(__name__)
API_BASE_URL = "https://apiautodoc-production.up.railway.app"
# API_BASE_URL = "http://127.0.0.1:8080"

def get_api_data(endpoint, params=None):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API error ({endpoint}): {e.response.text if e.response else str(e)}")
        return []

def post_api_data(endpoint, data):
    try:
        data = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in data.items()}
        logger.info(f"Sending to {endpoint}: {data}")
        response = requests.post(f"{API_BASE_URL}/{endpoint}", json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API error ({endpoint}): {e.response.text if e.response else str(e)}")
        return None


from functools import lru_cache

@lru_cache(maxsize=1)
def get_cached_refs():
    """Кэшируем справочники, чтобы не грузить каждый раз."""
    return {
        'cars': get_api_data("cars"),
        'colors': get_api_data("colors"),
        'works': get_api_data("works"),
        'persons': get_api_data("persons"),
        'roles': get_api_data("roles"),
        'persons_status_true': get_api_data("persons-status")
    }



def calendar_view(request):
    try:
        current_date = datetime.now()
        year = int(request.GET.get('year', current_date.year))
        month = int(request.GET.get('month', current_date.month))

        assignments = get_api_data("work-assignments", {'year': year, 'month': month})
        logger.info(f"Assignments for {year}-{month}: {len(assignments)} records")

        cal = calendar.monthcalendar(year, month)
        days_with_assignments = {
            datetime.fromisoformat(a['date']).day
            for a in assignments if a.get('date')
        }

        calendar_data = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'day': 0})
                    continue
                week_data.append({
                    'day': day,
                    'has_assignment': day in days_with_assignments,
                    'is_current': (day == current_date.day and month == current_date.month and year == current_date.year)
                })
            calendar_data.append(week_data)

        prev_date = datetime(year, month, 1) - timedelta(days=1)
        next_date = datetime(year, month, 28) + timedelta(days=4)

        context = {
            'calendar_data': calendar_data,
            'month_name': calendar.month_name[month],
            'year': year,
            'month': month,
            'prev_year': prev_date.year,
            'prev_month': prev_date.month,
            'next_year': next_date.year,
            'next_month': next_date.month,
            'current_day': current_date.day,
            'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
            'years': list(range(year - 5, year + 6)),
        }
        return render(request, 'AutoDoc/calendar.html', context)

    except Exception as e:
        logger.error(f"Error in calendar_view: {e}")
        return JsonResponse({'error': str(e)}, status=500)


import locale
from django.conf import settings

def safe_set_locale():
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'ru_RU')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
            except locale.Error:
                locale.setlocale(locale.LC_TIME, '')
                if settings.DEBUG:
                    print("Русская локаль не найдена, используется системная по умолчанию")


    # Остальной код вашего view

def assignment_details_view(request, year, month, day):
    try:
        safe_set_locale()
        assignments = get_api_data("work-assignments", {'year': year, 'month': month, 'day': day})
        works_for_day = []

        if assignments:
            persons = get_cached_refs()['persons']
            works = get_cached_refs()['works']

            for assignment in assignments:
                wa_works = get_api_data(f"work-assignment-works?work_assignment_id={assignment['id']}")

                # Группируем работы по исполнителям
                works_by_executor = {}
                for w in wa_works:
                    executor_id = w['executor_id']
                    if executor_id not in works_by_executor:
                        works_by_executor[executor_id] = {
                            'employee_id': executor_id,
                            'employee_name': next((p['full_name'] for p in persons if p['id'] == executor_id), 'Не назначен'),
                            'works': []
                        }
                    works_by_executor[executor_id]['works'].append({
                        'work_id': w['work_id'],
                        'work_name': next((wrk['name'] for wrk in works if wrk['id'] == w['work_id']), 'Неизвестная работа'),
                        'status': w['status']
                    })

                works_for_day.append({
                    'id': assignment['id'],
                    'time': datetime.fromisoformat(assignment['date']).strftime('%H:%M'),
                    'vin': assignment.get('vin', ''),
                    'car_number': assignment.get('car_number', ''),
                    'car_name': assignment['car']['name'] if assignment.get('car') else 'Не указано',
                    'color_name': assignment['color']['name'] if assignment.get('color') else 'Не указано',
                    'person_name': assignment['person']['full_name'] if assignment.get('person') else 'Не указан',
                    'description': assignment.get('description', ''),
                    'works': list(works_by_executor.values())  # Здесь список с исполнителями и их работами
                })

        context = {
            'day': day,
            'month': month,
            'month_name': calendar.month_name[month],
            'year': year,
            'assignments': works_for_day,
            **get_cached_refs(),
            'hours': list(range(8, 20)),
            'minutes': list(range(0, 60, 5))
        }
        return render(request, 'AutoDoc/assignment_details.html', context)

    except Exception as e:
        logger.error(f"Error in assignment_details_view: {e}")
        return JsonResponse({'error': str(e)}, status=500)





def get_assignment(request, assignment_id):
    try:
        response = requests.get(
            f"{API_BASE_URL}/get-assignment/{assignment_id}",  # Исправленный URL
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse(
                {'error': f"API error: {response.json().get('detail', 'Unknown error')}"},
                status=response.status_code
            )

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# def update_assignment(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Method not allowed'}, status=405)
#
#     try:
#         data = json.loads(request.body)
#         assignment_id = data.get('id')
#
#         if not assignment_id:
#             return JsonResponse({'error': 'Missing assignment ID'}, status=400)
#
#         # Подготовка данных для API
#         payload = {
#             "date": data.get('date'),
#             "vin": data.get('vin'),
#             "car_number": data.get('car_number'),
#             "color_id": data.get('color_id'),
#             "person_id": data.get('person_id'),
#             "car_id": data.get('car_id'),
#             "description": data.get('description'),
#             "works": data.get('works', [])
#         }
#
#         # Удаляем None значения и пустые works
#         payload = {k: v for k, v in payload.items() if v is not None and (k != 'works' or v)}
#         if not payload.get('works'):
#             payload['works'] = []
#
#         print(f"Sending payload to API: {payload}")  # Отладочный вывод
#
#         response = requests.put(
#             f"{API_BASE_URL}/work-assignments/{assignment_id}",
#             json=payload,
#             headers={"Content-Type": "application/json"}
#         )
#
#         if response.status_code == 200:
#             return JsonResponse({'success': True, 'data': response.json()})
#         else:
#             error_detail = response.json().get('detail', 'Unknown error')
#             return JsonResponse(
#                 {'error': f"API error: {error_detail}"},
#                 status=response.status_code
#             )
#
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON data'}, status=400)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
@csrf_exempt 
def update_assignment(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        assignment_id = data.get('id')

        if not assignment_id:
            return JsonResponse({'error': 'Missing assignment ID'}, status=400)

        # Подготовка данных для API
        payload = {
            "date": data.get('date'),
            "vin": data.get('vin'),
            "car_number": data.get('car_number'),
            "color_id": data.get('color_id'),
            "person_id": data.get('person_id'),
            "car_id": data.get('car_id'),
            "description": data.get('description'),
            "works": []
        }

        # Добавляем работы с их статусами
        if 'works' in data:
            for work in data['works']:
                payload['works'].append({
                    'work_id': work.get('work_id'),
                    'executor_id': work.get('executor_id'),
                    'status': work.get('status', False)  # Сохраняем статус
                })

        print(f"Sending payload to API: {payload}")  # Отладочный вывод

        response = requests.put(
            f"{API_BASE_URL}/work-assignments/{assignment_id}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            return JsonResponse({'success': True, 'data': response.json()})
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return JsonResponse(
                {'error': f"API error: {error_detail}"},
                status=response.status_code
            )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt 
def delete_assignment(request, assignment_id):
    try:
        response = requests.delete(
            f"{API_BASE_URL}/work-assignments/{assignment_id}",
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 204:
            return JsonResponse({'success': True})
        else:
            return JsonResponse(
                {'error': f"API error: {response.json().get('detail', 'Unknown error')}"},
                status=response.status_code
            )

    except Exception as e:
        logger.error(f"Error deleting assignment: {e}")
        return JsonResponse({'error': str(e)}, status=500)
#
# @csrf_exempt
# def create_assignment(request, year, month, day):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
#             logger.info(f"Received data: {data}")
#
#             hour = int(data.get('hour', 12))
#             minute = int(data.get('minute', 0))
#             assignment_date = datetime(year, month, day, hour, minute)
#
#             assignment_data = {
#                 'date': assignment_date,
#                 'vin': data.get('vin', ''),
#                 'car_number': data.get('car_number', ''),
#                 'car_id': data.get('car_id') if data.get('car_id') else None,
#                 'color_id': int(data.get('color_id')),
#                 'person_id': int(data.get('person_id')),
#                 'is_active': True,
#                 'description': data.get('description', '')
#             }
#
#             assignment = post_api_data("work-assignments", assignment_data)
#             if not assignment:
#                 raise Exception("Не удалось создать назначение. Проверьте логи API.")
#
#             work_ids = [int(wid) for wid in data.get('work_ids', []) if wid]
#             for work_id in work_ids:
#                 post_api_data("work-assignment-works", {'work_assignment_id': assignment['id'], 'work_id': work_id})
#
#             return JsonResponse({
#                 'success': True,
#                 'redirect_url': reverse('AutoDoc:assignment_details', kwargs={'year': year, 'month': month, 'day': day})
#             })
#         except Exception as e:
#             logger.error(f"Error creating assignment: {e}")
#             return JsonResponse({'error': str(e)}, status=400)
#     return JsonResponse({'error': 'Метод не разрешен'}, status=405)
@csrf_exempt
def create_assignment(request, year, month, day):
    if request.method == 'POST':
        try:
            # Логируем входящий запрос
            logger.info(f"Incoming request headers: {request.headers}")
            logger.info(f"Content type: {request.content_type}")

            # Парсим данные запроса
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    data = request.POST.dict()
                    data['work_ids'] = request.POST.getlist('work_ids[]')
                    data['work_employees'] = request.POST.getlist('work_employees[]')
            except Exception as e:
                logger.error(f"Error parsing request data: {str(e)}")
                return JsonResponse({'error': 'Invalid request data format'}, status=400)

            logger.info(f"Parsed request data: {data}")

            # Валидация обязательных полей
            required_fields = ['color_id', 'person_id']
            for field in required_fields:
                if field not in data or not data[field]:
                    error_msg = f"Missing required field: {field}"
                    logger.error(error_msg)
                    return JsonResponse({'error': error_msg}, status=400)

            # Подготовка данных для API
            assignment_data = {
                'date': datetime(
                    year=year,
                    month=month,
                    day=day,
                    hour=int(data.get('hour', 12)),
                    minute=int(data.get('minute', 0))
                ).isoformat(),
                'vin': data.get('vin', ''),
                'car_number': data.get('car_number', ''),
                'car_id': data.get('car_id'),
                'color_id': int(data['color_id']),
                'person_id': int(data['person_id']),
                'description': data.get('description', ''),
                'works': []
            }

            # Обработка работ
            if 'works' in data:
                for work in data['works']:
                    if 'work_id' in work and work['work_id']:
                        assignment_data['works'].append({
                            'work_id': int(work['work_id']),
                            'executor_id': int(work['executor_id']) if work.get('executor_id') else None
                        })

            logger.info(f"Prepared API request data: {assignment_data}")

            # Отправка запроса к API
            try:
                response = requests.post(
                    f"{API_BASE_URL}/work-assignments",
                    json=assignment_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                logger.info(f"API response status: {response.status_code}")
                logger.info(f"API response content: {response.text}")

                # Обработка ответа
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if not response_data:
                            logger.warning("API returned empty response")
                            return JsonResponse({
                                'success': True,
                                'redirect_url': reverse('AutoDoc:assignment_details',
                                                        kwargs={'year': year, 'month': month, 'day': day})
                            })
                        return JsonResponse(response_data)
                    except ValueError:
                        logger.warning("API returned non-JSON response")
                        return JsonResponse({
                            'success': True,
                            'redirect_url': reverse('AutoDoc:assignment_details',
                                                    kwargs={'year': year, 'month': month, 'day': day})
                        })
                else:
                    error_msg = f"API returned status {response.status_code}"
                    try:
                        error_detail = response.json().get('detail', response.text)
                        error_msg += f": {error_detail}"
                    except ValueError:
                        error_msg += f": {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                raise Exception(f"Ошибка соединения с API: {str(e)}")

        except Exception as e:
            logger.error(f"Error in create_assignment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@csrf_exempt
def update_work_status(request, assignment_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            updates = data.get('updates', [])
            response = post_api_data(f"work-assignment-works/update-status/", {"assignment_id": assignment_id, "updates": updates})
            if response and 'success' in response:
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Не удалось обновить статусы'}, status=400)
        except Exception as e:
            logger.error(f"Error updating work status: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)
