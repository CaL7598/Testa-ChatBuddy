"""
Study Assistant Views - Quiz, Flashcards, Summaries
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import (
    Quiz, QuizQuestion, QuizAttempt, Flashcard, 
    PDFDocument, TopicMastery, DailyActivity, UserAnalytics
)
from .utils import QuizGenerator, FlashcardGenerator, SummaryGenerator


# Quiz Views
@login_required
def generate_quiz(request):
    """Generate quiz from document"""
    if request.method == 'POST':
        document_id = request.POST.get('document')
        topic = request.POST.get('topic', '')
        difficulty = request.POST.get('difficulty', 'medium')
        num_questions = int(request.POST.get('num_questions', 5))
        
        document = get_object_or_404(PDFDocument, id=document_id)
        
        # Extract text from document
        from .utils import get_file_text
        document_text = get_file_text(document.file)
        
        # Generate quiz using AI
        generator = QuizGenerator()
        quiz_data = generator.generate_quiz(
            document_text, 
            topic, 
            num_questions, 
            difficulty
        )
        
        if quiz_data:
            # Create quiz in database
            quiz = Quiz.objects.create(
                title=quiz_data.get('title', f'Quiz on {topic}'),
                course=document.course or '',
                topic=topic,
                difficulty=difficulty,
                source_document=document,
                created_by=request.user,
                time_limit=30
            )
            
            # Create quiz questions
            for idx, q_data in enumerate(quiz_data.get('questions', [])):
                QuizQuestion.objects.create(
                    quiz=quiz,
                    question_text=q_data.get('question', ''),
                    question_type=q_data.get('type', 'mcq'),
                    options=q_data.get('options', []),
                    correct_answer=q_data.get('correct_answer', ''),
                    explanation=q_data.get('explanation', ''),
                    points=1,
                    order=idx
                )
            
            return redirect('take_quiz', quiz_id=quiz.id)
        else:
            return render(request, 'testa_app/generate_quiz.html', {
                'error': 'Failed to generate quiz. Please try again.',
                'documents': PDFDocument.objects.filter(uploaded_by=request.user)
            })
    
    documents = PDFDocument.objects.filter(uploaded_by=request.user)
    return render(request, 'testa_app/generate_quiz.html', {
        'documents': documents
    })


@login_required
def take_quiz(request, quiz_id):
    """Take quiz interface"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    
    if request.method == 'POST':
        # Create quiz attempt
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            started_at=timezone.now()
        )
        
        # Process answers
        total_points = 0
        score = 0
        
        for question in questions:
            total_points += question.points
            user_answer = request.POST.get(f'question_{question.id}', '')
            
            if question.question_type == 'mcq':
                if user_answer.strip().lower() == question.correct_answer.strip().lower():
                    score += question.points
            elif question.question_type == 'true_false':
                if user_answer.lower() == question.correct_answer.lower():
                    score += question.points
            else:  # short_answer
                # Simple keyword matching (can be improved)
                if question.correct_answer.lower() in user_answer.lower():
                    score += question.points
        
        # Update attempt
        attempt.score = score
        attempt.total_points = total_points
        attempt.completed_at = timezone.now()
        attempt.time_taken = int((timezone.now() - attempt.started_at).total_seconds())
        attempt.save()
        
        # Update topic mastery
        _update_topic_mastery_from_quiz(request.user, quiz, score, total_points)
        
        # Update analytics (includes study time + streak)
        _update_quiz_analytics(request.user, score, total_points, attempt.time_taken)
        
        return redirect('quiz_results', attempt_id=attempt.id)
    
    return render(request, 'testa_app/take_quiz.html', {
        'quiz': quiz,
        'questions': questions
    })


@login_required
def quiz_results(request, attempt_id):
    """View quiz results"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    quiz = attempt.quiz
    questions = quiz.questions.all()
    
    # Get user answers (stored in session or recalculate)
    user_answers = {}
    for question in questions:
        # In a real implementation, store answers during quiz taking
        user_answers[question.id] = request.GET.get(f'answer_{question.id}', '')
    
    return render(request, 'testa_app/quiz_results.html', {
        'attempt': attempt,
        'quiz': quiz,
        'questions': questions,
        'user_answers': user_answers,
        'percentage': attempt.percentage_score
    })


def _update_study_time_and_streak(user, seconds):
    """Update total study time (minutes), daily activity, and streak from a duration in seconds."""
    if seconds is None:
        seconds = 0
    # Convert to at least 1 minute of study
    minutes = max(1, int(round(seconds / 60))) if seconds > 0 else 1

    analytics, _ = UserAnalytics.objects.get_or_create(user=user)
    analytics.total_study_time += minutes

    today = timezone.now().date()
    activity, _ = DailyActivity.objects.get_or_create(user=user, date=today)
    activity.study_minutes += minutes
    activity.save()

    # Recalculate streak: count consecutive days with any study_minutes starting from today
    streak = 0
    current_day = today
    while DailyActivity.objects.filter(user=user, date=current_day, study_minutes__gt=0).exists():
        streak += 1
        current_day -= timedelta(days=1)

    analytics.current_streak = streak
    if streak > analytics.longest_streak:
        analytics.longest_streak = streak

    analytics.save()


# Flashcard Views
@login_required
def generate_flashcards(request):
    """Generate flashcards from document"""
    if request.method == 'POST':
        document_id = request.POST.get('document')
        topic = request.POST.get('topic', '')
        num_cards = int(request.POST.get('num_cards', 10))
        
        document = get_object_or_404(PDFDocument, id=document_id)
        
        # Extract text
        from .utils import get_file_text
        document_text = get_file_text(document.file)
        
        # Generate flashcards
        generator = FlashcardGenerator()
        flashcard_data = generator.generate_flashcards(document_text, topic, num_cards)
        
        if flashcard_data:
            created_count = 0
            for card_data in flashcard_data.get('flashcards', []):
                Flashcard.objects.create(
                    user=request.user,
                    course=document.course or '',
                    topic=topic,
                    front=card_data.get('front', ''),
                    back=card_data.get('back', ''),
                    source_document=document
                )
                created_count += 1
            
            return render(request, 'testa_app/generate_flashcards.html', {
                'success': f'Successfully created {created_count} flashcards!',
                'documents': PDFDocument.objects.filter(uploaded_by=request.user)
            })
        else:
            return render(request, 'testa_app/generate_flashcards.html', {
                'error': 'Failed to generate flashcards. Please try again.',
                'documents': PDFDocument.objects.filter(uploaded_by=request.user)
            })
    
    documents = PDFDocument.objects.filter(uploaded_by=request.user)
    return render(request, 'testa_app/generate_flashcards.html', {
        'documents': documents
    })


@login_required
def study_flashcards(request):
    """Study flashcards interface"""
    import json
    course = request.GET.get('course', '')
    topic = request.GET.get('topic', '')
    confidence_filter = request.GET.get('confidence', '')
    
    flashcards = Flashcard.objects.filter(user=request.user)
    
    if course:
        flashcards = flashcards.filter(course=course)
    if topic:
        flashcards = flashcards.filter(topic=topic)
    if confidence_filter:
        flashcards = flashcards.filter(confidence_level__lt=int(confidence_filter))
    
    # Prioritize cards with low confidence or not reviewed recently
    flashcards = flashcards.order_by('confidence_level', 'last_reviewed')

    flashcards_data = list(flashcards.values('id', 'front', 'back'))
    
    return render(request, 'testa_app/study_flashcards.html', {
        'flashcards': flashcards,
        'flashcards_json': json.dumps(flashcards_data),
        'current_course': course,
        'current_topic': topic,
    })


@login_required
def update_flashcard_confidence(request, flashcard_id):
    """Update flashcard confidence level (AJAX)"""
    if request.method == 'POST':
        flashcard = get_object_or_404(Flashcard, id=flashcard_id, user=request.user)
        confidence = int(request.POST.get('confidence', 0))
        
        flashcard.confidence_level = confidence
        flashcard.last_reviewed = timezone.now()
        flashcard.review_count += 1
        flashcard.save()
        
        # Update daily activity
        today = timezone.now().date()
        activity, _ = DailyActivity.objects.get_or_create(
            user=request.user,
            date=today
        )
        activity.flashcards_reviewed += 1
        activity.save()

        # Approximate 1 minute of focused study per reviewed card
        _update_study_time_and_streak(request.user, 60)

        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)


# Summary Views
@login_required
def generate_summary(request):
    """Generate summary from document"""
    if request.method == 'POST':
        document_id = request.POST.get('document')
        summary_type = request.POST.get('summary_type', 'concise')
        
        document = get_object_or_404(PDFDocument, id=document_id)
        
        # Extract text
        from .utils import get_file_text
        document_text = get_file_text(document.file)
        
        # Generate summary
        generator = SummaryGenerator()
        summary = generator.generate_summary(document_text, summary_type)
        
        if summary:
            return render(request, 'testa_app/summary_result.html', {
                'summary': summary,
                'document': document,
                'summary_type': summary_type
            })
        else:
            return render(request, 'testa_app/generate_summary.html', {
                'error': 'Failed to generate summary. Please try again.',
                'documents': PDFDocument.objects.filter(uploaded_by=request.user)
            })
    
    documents = PDFDocument.objects.filter(uploaded_by=request.user)
    return render(request, 'testa_app/generate_summary.html', {
        'documents': documents
    })


@login_required
def generate_study_guide(request, doc_id):
    """Generate comprehensive study guide"""
    document = get_object_or_404(PDFDocument, id=doc_id)
    topic = request.GET.get('topic', document.topic or 'General')
    
    # Extract text
    from .utils import get_file_text
    document_text = get_file_text(document.file)
    
    # Generate study guide
    generator = SummaryGenerator()
    study_guide = generator.generate_study_guide(document_text, topic)
    
    return render(request, 'testa_app/study_guide.html', {
        'study_guide': study_guide,
        'document': document,
        'topic': topic
    })


# Helper functions
def _update_topic_mastery_from_quiz(user, quiz, score, total_points):
    """Update topic mastery based on quiz results"""
    mastery, created = TopicMastery.objects.get_or_create(
        user=user,
        course=quiz.course,
        topic=quiz.topic,
        defaults={
            'questions_answered': 0,
            'correct_answers': 0,
            'mastery_level': 0.0
        }
    )
    
    mastery.questions_answered += quiz.questions.count()
    mastery.correct_answers += int((score / total_points) * quiz.questions.count())
    mastery.mastery_level = (mastery.correct_answers / mastery.questions_answered) * 100
    mastery.last_practiced = timezone.now()
    mastery.save()


def _update_quiz_analytics(user, score, total_points, time_taken_seconds=None):
    """Update user analytics for quiz"""
    analytics, _ = UserAnalytics.objects.get_or_create(user=user)
    analytics.total_quizzes += 1
    
    # Update average score
    all_attempts = QuizAttempt.objects.filter(user=user)
    if all_attempts.exists():
        avg_score = all_attempts.aggregate(avg=Avg('score'))['avg']
        total_pts = all_attempts.aggregate(total=Sum('total_points'))['total']
        if total_pts:
            analytics.average_quiz_score = (avg_score / total_pts) * 100
    
    analytics.save()
    
    # Update daily activity (quizzes completed)
    today = timezone.now().date()
    activity, _ = DailyActivity.objects.get_or_create(
        user=user,
        date=today
    )
    activity.quizzes_completed += 1
    activity.save()

    # Also record study time & streak based on quiz duration
    _update_study_time_and_streak(user, time_taken_seconds)
