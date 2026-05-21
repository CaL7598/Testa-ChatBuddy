"""
Analytics Dashboard Views for Testa studyBuddy
"""

from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import Coalesce, TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import (
    UserAnalytics,
    DailyActivity,
    TopicMastery,
    QuestionAnswer,
    QuizAttempt,
    Flashcard,
    StudySession,
)


def _inclusive_day_range(days: int):
    """Last N calendar days ending today (in the active timezone)."""
    days = max(1, min(int(days), 366))
    end_d = timezone.localdate()
    start_d = end_d - timedelta(days=days - 1)
    return start_d, end_d


def _normalize_calendar_day(value):
    """Coerce TruncDate / datetime / str to a date for dict keys."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return timezone.localtime(value).date()
    s = str(value)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _filled_series(start_d: date, end_d: date, by_day: dict):
    """Build aligned labels and counts for every day in [start_d, end_d]."""
    labels = []
    data = []
    span_days = (end_d - start_d).days
    show_year = span_days > 300 or start_d.year != end_d.year
    cur = start_d
    while cur <= end_d:
        if show_year:
            labels.append(cur.strftime('%b %d, %Y'))
        else:
            labels.append(cur.strftime('%b %d'))
        data.append(int(by_day.get(cur, 0)))
        cur += timedelta(days=1)
    total = sum(data)
    return {'labels': labels, 'data': data, 'has_activity': total > 0}


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    user = request.user
    date_range = request.GET.get('range', '30')  # 7, 30, 90 days
    try:
        days = int(date_range)
    except (TypeError, ValueError):
        days = 30
        date_range = '30'

    start_d, end_d = _inclusive_day_range(days)

    # Get or create user analytics
    analytics, _ = UserAnalytics.objects.get_or_create(user=user)

    qa_count = QuestionAnswer.objects.filter(user=user).count()
    satisfaction = _satisfaction_breakdown(user)

    # Overview statistics (question count from DB so it matches charts / Q&A list)
    stats = {
        'total_questions': qa_count,
        'total_quizzes': analytics.total_quizzes,
        'average_quiz_score': round(analytics.average_quiz_score, 1),
        'total_study_time': analytics.total_study_time,
        'current_streak': analytics.current_streak,
        'longest_streak': analytics.longest_streak,
        'total_flashcards': Flashcard.objects.filter(user=user).count(),
        'satisfaction_score': satisfaction['score'],
        'satisfaction_has_votes': satisfaction['has_votes'],
        'satisfaction_upvotes': satisfaction['upvotes'],
        'satisfaction_total_votes': satisfaction['total_votes'],
    }

    # Chart data: one point per calendar day in range (zeros filled)
    chart_data = {
        'questions_over_time': _get_questions_over_time(user, start_d, end_d),
        'study_minutes_over_time': _get_study_minutes_over_time(user, start_d, end_d),
        'quizzes_over_time': _get_quizzes_over_time(user, start_d, end_d),
    }
    
    # Topic mastery data
    topic_mastery = _get_topic_mastery_data(user)
    
    # Trending topics
    trending_topics = _get_trending_topics(user, start_d, end_d)

    # Study patterns
    study_patterns = _get_study_patterns(user)

    # Additional insights
    insights = _get_insights(user, days, stats)

    # Course breakdown
    course_breakdown = _get_course_breakdown(user, start_d, end_d)

    # Difficulty distribution
    difficulty_dist = _get_difficulty_distribution(user, start_d, end_d)
    
    # Weekly comparison
    weekly_comparison = _get_weekly_comparison(user)
    
    context = {
        'stats': stats,
        'chart_data': chart_data,
        'topic_mastery': topic_mastery,
        'trending_topics': trending_topics,
        'study_patterns': study_patterns,
        'insights': insights,
        'course_breakdown': course_breakdown,
        'difficulty_dist': difficulty_dist,
        'weekly_comparison': weekly_comparison,
        'date_range': str(date_range),
    }

    return render(request, 'testa_app/analytics_dashboard.html', context)


@login_required
def analytics_chart_data(request):
    """API endpoint for chart data (AJAX)"""
    user = request.user
    chart_type = request.GET.get('type', 'questions')
    try:
        date_range = int(request.GET.get('range', '30'))
    except (TypeError, ValueError):
        date_range = 30

    start_d, end_d = _inclusive_day_range(date_range)

    if chart_type == 'questions':
        data = _get_questions_over_time(user, start_d, end_d)
    elif chart_type == 'study_time':
        data = _get_study_minutes_over_time(user, start_d, end_d)
    elif chart_type == 'quizzes':
        data = _get_quizzes_over_time(user, start_d, end_d)
    else:
        data = {}

    return JsonResponse(data)


def _satisfaction_breakdown(user):
    """Upvote ratio when there are votes; otherwise no score (UI shows N/A)."""
    total_votes = 0
    upvotes = 0
    for row in QuestionAnswer.objects.filter(user=user).values('upvotes', 'downvotes'):
        total_votes += int(row['upvotes'] or 0) + int(row['downvotes'] or 0)
        upvotes += int(row['upvotes'] or 0)
    if total_votes == 0:
        return {
            'has_votes': False,
            'score': None,
            'upvotes': 0,
            'total_votes': 0,
        }
    return {
        'has_votes': True,
        'score': round((upvotes / total_votes) * 100, 1),
        'upvotes': upvotes,
        'total_votes': total_votes,
    }


def _get_questions_over_time(user, start_d, end_d):
    """Questions created per calendar day (matches Q&A totals in the selected window)."""
    tz = timezone.get_current_timezone()
    rows = (
        QuestionAnswer.objects.filter(
            user=user,
            created_at__date__gte=start_d,
            created_at__date__lte=end_d,
        )
        .annotate(day=TruncDate('created_at', tzinfo=tz))
        .values('day')
        .annotate(c=Count('id'))
    )
    by_day = {}
    for row in rows:
        d = _normalize_calendar_day(row['day'])
        if d:
            by_day[d] = by_day.get(d, 0) + int(row['c'])
    return _filled_series(start_d, end_d, by_day)


def _get_study_minutes_over_time(user, start_d, end_d):
    """Study minutes logged per day (DailyActivity), zeros filled for the range."""
    acts = DailyActivity.objects.filter(user=user, date__gte=start_d, date__lte=end_d)
    by_day = {a.date: int(a.study_minutes or 0) for a in acts}
    return _filled_series(start_d, end_d, by_day)


def _get_quizzes_over_time(user, start_d, end_d):
    """Quiz attempts per calendar day (completed time, or started time if not completed)."""
    tz = timezone.get_current_timezone()
    rows = (
        QuizAttempt.objects.filter(user=user)
        .annotate(evt=Coalesce('completed_at', 'started_at'))
        .filter(evt__date__gte=start_d, evt__date__lte=end_d)
        .annotate(day=TruncDate('evt', tzinfo=tz))
        .values('day')
        .annotate(c=Count('id'))
    )
    by_day = {}
    for row in rows:
        d = _normalize_calendar_day(row['day'])
        if d:
            by_day[d] = by_day.get(d, 0) + int(row['c'])
    return _filled_series(start_d, end_d, by_day)


def _get_topic_mastery_data(user):
    """Get topic mastery data for visualization"""
    masteries = TopicMastery.objects.filter(user=user).order_by('-mastery_level')
    
    top_mastered = masteries.filter(mastery_level__gte=70)[:5]
    weak_areas = masteries.filter(mastery_level__lt=60).order_by('mastery_level')[:5]
    
    return {
        'top_mastered': [
            {
                'course': m.course,
                'topic': m.topic,
                'mastery': round(m.mastery_level, 1),
                'accuracy': round(m.accuracy_rate, 1),
            }
            for m in top_mastered
        ],
        'weak_areas': [
            {
                'course': m.course,
                'topic': m.topic,
                'mastery': round(m.mastery_level, 1),
                'accuracy': round(m.accuracy_rate, 1),
            }
            for m in weak_areas
        ],
    }


def _get_trending_topics(user, start_d, end_d):
    """Get trending topics in the selected calendar window."""
    topics = (
        QuestionAnswer.objects.filter(
            user=user,
            created_at__date__gte=start_d,
            created_at__date__lte=end_d,
        )
        .exclude(topic='')
        .values('topic')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    return [{'topic': t['topic'], 'count': t['count']} for t in topics]


def _get_study_patterns(user):
    """Get study patterns (active times, favorite courses, etc.)"""
    # Most active study times (by hour)
    sessions = StudySession.objects.filter(user=user)
    hour_counts = {}
    for session in sessions:
        hour = session.started_at.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
    
    most_active_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
    
    # Favorite course
    try:
        analytics = UserAnalytics.objects.get(user=user)
        favorite_course = analytics.favorite_course
    except UserAnalytics.DoesNotExist:
        favorite_course = None
    
    if not favorite_course:
        # Calculate from questions
        course_counts = QuestionAnswer.objects.filter(
            user=user
        ).exclude(course='').values('course').annotate(
            count=Count('id')
        ).order_by('-count')[:1]
        
        if course_counts:
            favorite_course = course_counts[0]['course']
    
    return {
        'most_active_hour': most_active_hour,
        'favorite_course': favorite_course,
    }


def _get_insights(user, days, stats):
    """Generate insights and recommendations"""
    insights = []
    
    # Streak insight
    if stats['current_streak'] > 0:
        if stats['current_streak'] >= 7:
            insights.append({
                'type': 'success',
                'icon': '🔥',
                'title': 'Amazing Streak!',
                'message': f'You\'ve been studying for {stats["current_streak"]} days straight! Keep it up!'
            })
        else:
            insights.append({
                'type': 'info',
                'icon': '📅',
                'title': 'Building Momentum',
                'message': f'You\'re on a {stats["current_streak"]} day streak. Aim for 7 days!'
            })
    else:
        insights.append({
            'type': 'warning',
            'icon': '💪',
            'title': 'Start Your Streak',
            'message': 'Begin studying today to start your learning streak!'
        })
    
    # Questions insight
    if stats['total_questions'] == 0:
        insights.append({
            'type': 'info',
            'icon': '❓',
            'title': 'Get Started',
            'message': 'Ask your first question to begin tracking your progress!'
        })
    elif stats['total_questions'] < 5:
        insights.append({
            'type': 'info',
            'icon': '📚',
            'title': 'Keep Learning',
            'message': f'You\'ve asked {stats["total_questions"]} questions. Try to ask more to improve!'
        })
    
    # Quiz insight
    if stats['total_quizzes'] == 0:
        insights.append({
            'type': 'info',
            'icon': '📝',
            'title': 'Try Quizzes',
            'message': 'Take quizzes to test your knowledge and track improvement!'
        })
    elif stats['average_quiz_score'] < 70:
        insights.append({
            'type': 'warning',
            'icon': '📖',
            'title': 'Review Needed',
            'message': f'Your average score is {stats["average_quiz_score"]}%. Review weak areas!'
        })
    
    return insights[:3]  # Return top 3 insights


def _get_course_breakdown(user, start_d, end_d):
    """Get breakdown of questions by course in the selected calendar window."""
    courses = (
        QuestionAnswer.objects.filter(
            user=user,
            created_at__date__gte=start_d,
            created_at__date__lte=end_d,
        )
        .exclude(course='')
        .values('course')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    total = sum(c['count'] for c in courses)

    return [
        {
            'course': c['course'],
            'count': c['count'],
            'percentage': round((c['count'] / total * 100), 1) if total > 0 else 0,
        }
        for c in courses
    ]


def _get_difficulty_distribution(user, start_d, end_d):
    """Get distribution of questions by difficulty in the selected calendar window."""
    difficulties = (
        QuestionAnswer.objects.filter(
            user=user,
            created_at__date__gte=start_d,
            created_at__date__lte=end_d,
        )
        .exclude(difficulty_detected='')
        .values('difficulty_detected')
        .annotate(count=Count('id'))
    )

    total = sum(d['count'] for d in difficulties)

    dist = {
        'beginner': 0,
        'intermediate': 0,
        'advanced': 0,
    }

    for d in difficulties:
        if d['difficulty_detected'] in dist:
            dist[d['difficulty_detected']] = round((d['count'] / total * 100), 1) if total > 0 else 0

    return dist


def _get_weekly_comparison(user):
    """Compare this week vs last week"""
    now = timezone.now()
    this_week_start = now - timedelta(days=now.weekday() + 7)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start
    
    this_week_questions = QuestionAnswer.objects.filter(
        user=user,
        created_at__gte=this_week_start
    ).count()
    
    last_week_questions = QuestionAnswer.objects.filter(
        user=user,
        created_at__gte=last_week_start,
        created_at__lt=last_week_end
    ).count()
    
    if last_week_questions == 0:
        change_percent = 100 if this_week_questions > 0 else 0
    else:
        change_percent = round(((this_week_questions - last_week_questions) / last_week_questions) * 100, 1)
    
    return {
        'this_week': this_week_questions,
        'last_week': last_week_questions,
        'change_percent': change_percent,
        'is_increase': change_percent > 0
    }
