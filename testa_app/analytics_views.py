"""
Analytics Dashboard Views for Testa studyBuddy
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import (
    UserAnalytics, DailyActivity, TopicMastery, 
    QuestionAnswer, QuizAttempt, Flashcard, StudySession
)


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    user = request.user
    date_range = request.GET.get('range', '30')  # 7, 30, 90 days
    
    # Get or create user analytics
    analytics, _ = UserAnalytics.objects.get_or_create(user=user)
    
    # Calculate date range
    days = int(date_range)
    start_date = timezone.now() - timedelta(days=days)
    
    # Overview statistics
    stats = {
        'total_questions': analytics.total_questions,
        'total_quizzes': analytics.total_quizzes,
        'average_quiz_score': round(analytics.average_quiz_score, 1),
        'total_study_time': analytics.total_study_time,
        'current_streak': analytics.current_streak,
        'longest_streak': analytics.longest_streak,
        # Compute actual count of flashcards for the user so the tile stays accurate
        'total_flashcards': Flashcard.objects.filter(user=user).count(),
        'satisfaction_score': _calculate_satisfaction_score(user),
    }
    
    # Chart data
    chart_data = {
        'questions_over_time': _get_questions_over_time(user, start_date),
        'study_minutes_over_time': _get_study_minutes_over_time(user, start_date),
        'quizzes_over_time': _get_quizzes_over_time(user, start_date),
    }
    
    # Topic mastery data
    topic_mastery = _get_topic_mastery_data(user)
    
    # Trending topics
    trending_topics = _get_trending_topics(user, days)
    
    # Study patterns
    study_patterns = _get_study_patterns(user)
    
    # Additional insights
    insights = _get_insights(user, days, stats)
    
    # Course breakdown
    course_breakdown = _get_course_breakdown(user, days)
    
    # Difficulty distribution
    difficulty_dist = _get_difficulty_distribution(user, days)
    
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
        'date_range': date_range,
    }
    
    return render(request, 'testa_app/analytics_dashboard.html', context)


@login_required
def analytics_chart_data(request):
    """API endpoint for chart data (AJAX)"""
    user = request.user
    chart_type = request.GET.get('type', 'questions')
    date_range = int(request.GET.get('range', '30'))
    
    start_date = timezone.now() - timedelta(days=date_range)
    
    if chart_type == 'questions':
        data = _get_questions_over_time(user, start_date)
    elif chart_type == 'study_time':
        data = _get_study_minutes_over_time(user, start_date)
    elif chart_type == 'quizzes':
        data = _get_quizzes_over_time(user, start_date)
    else:
        data = {}
    
    return JsonResponse(data)


def _calculate_satisfaction_score(user):
    """Calculate satisfaction score based on votes"""
    qa_list = QuestionAnswer.objects.filter(user=user)
    total_votes = 0
    upvotes = 0
    
    for qa in qa_list:
        total_votes += qa.upvotes + qa.downvotes
        upvotes += qa.upvotes
    
    if total_votes == 0:
        return 0.0
    return round((upvotes / total_votes) * 100, 1)


def _get_questions_over_time(user, start_date):
    """Get questions asked over time for line chart"""
    activities = DailyActivity.objects.filter(
        user=user,
        date__gte=start_date.date()
    ).order_by('date')
    
    # Format dates nicely
    labels = []
    for act in activities:
        date_obj = act.date
        labels.append(date_obj.strftime('%b %d'))
    
    data = [act.questions_asked for act in activities]
    
    # If no data, create empty array with placeholder
    if not labels:
        labels = []
        data = []
    
    return {
        'labels': labels,
        'data': data,
    }


def _get_study_minutes_over_time(user, start_date):
    """Get study minutes per day for line chart"""
    activities = DailyActivity.objects.filter(
        user=user,
        date__gte=start_date.date()
    ).order_by('date')
    
    # Format dates nicely
    labels = []
    for act in activities:
        date_obj = act.date
        labels.append(date_obj.strftime('%b %d'))
    
    data = [act.study_minutes for act in activities]
    
    # If no data, create empty array
    if not labels:
        labels = []
        data = []
    
    return {
        'labels': labels,
        'data': data,
    }


def _get_quizzes_over_time(user, start_date):
    """Get quizzes completed over time"""
    attempts = QuizAttempt.objects.filter(
        user=user,
        started_at__gte=start_date
    ).extra(
        select={'date': 'DATE(started_at)'}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Format dates nicely
    labels = []
    for item in attempts:
        if item['date']:
            date_obj = datetime.strptime(str(item['date']), '%Y-%m-%d').date()
            labels.append(date_obj.strftime('%b %d'))
        else:
            labels.append('')
    
    data = [item['count'] for item in attempts]
    
    # If no data, create empty array
    if not labels:
        labels = []
        data = []
    
    return {
        'labels': labels,
        'data': data,
    }


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


def _get_trending_topics(user, days):
    """Get trending topics"""
    start_date = timezone.now() - timedelta(days=days)
    
    topics = QuestionAnswer.objects.filter(
        user=user,
        created_at__gte=start_date
    ).exclude(topic='').values('topic').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
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


def _get_course_breakdown(user, days):
    """Get breakdown of questions by course"""
    start_date = timezone.now() - timedelta(days=days)
    
    courses = QuestionAnswer.objects.filter(
        user=user,
        created_at__gte=start_date
    ).exclude(course='').values('course').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    total = sum(c['count'] for c in courses)
    
    return [
        {
            'course': c['course'],
            'count': c['count'],
            'percentage': round((c['count'] / total * 100), 1) if total > 0 else 0
        }
        for c in courses
    ]


def _get_difficulty_distribution(user, days):
    """Get distribution of questions by difficulty"""
    start_date = timezone.now() - timedelta(days=days)
    
    difficulties = QuestionAnswer.objects.filter(
        user=user,
        created_at__gte=start_date
    ).exclude(difficulty_detected='').values('difficulty_detected').annotate(
        count=Count('id')
    )
    
    total = sum(d['count'] for d in difficulties)
    
    dist = {
        'beginner': 0,
        'intermediate': 0,
        'advanced': 0
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
