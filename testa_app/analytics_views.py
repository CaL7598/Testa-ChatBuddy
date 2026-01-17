"""
Analytics Dashboard Views for Testa ChatBuddy
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
        'total_flashcards': analytics.total_flashcards,
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
    
    context = {
        'stats': stats,
        'chart_data': chart_data,
        'topic_mastery': topic_mastery,
        'trending_topics': trending_topics,
        'study_patterns': study_patterns,
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
    
    labels = [str(act.date) for act in activities]
    data = [act.questions_asked for act in activities]
    
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
    
    labels = [str(act.date) for act in activities]
    data = [act.study_minutes for act in activities]
    
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
    
    labels = [str(item['date']) for item in attempts]
    data = [item['count'] for item in attempts]
    
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
