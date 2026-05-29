from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    """Extended user data — email verification for SendGrid onboarding."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'user profile'
        verbose_name_plural = 'user profiles'

    def __str__(self):
        return f'Profile: {self.user.username}'

    def mark_verified(self):
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=['email_verified', 'email_verified_at'])


# Core Chat Models
class QuestionAnswer(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    course = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=100, blank=True)
    difficulty_detected = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True)
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    source_document = models.ForeignKey('PDFDocument', on_delete=models.SET_NULL, null=True, blank=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField('Tag', blank=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'question')
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['course', 'topic']),
            models.Index(fields=['-upvotes']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} asked: {self.question[:50]}"
    
    @property
    def satisfaction_score(self):
        """Calculate satisfaction score based on votes"""
        total = self.upvotes + self.downvotes
        if total == 0:
            return 0.0
        return (self.upvotes / total) * 100


class PDFDocument(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=100, blank=True)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True)
    
    def __str__(self):
        return self.title or self.file.name


class Vote(models.Model):
    VOTE_TYPES = [
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question_answer = models.ForeignKey(QuestionAnswer, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_TYPES)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    
    class Meta:
        unique_together = ('user', 'question_answer')
    
    def __str__(self):
        return f"{self.user.username} {self.vote_type} on Q&A {self.question_answer.id}"


# Analytics Models
class UserAnalytics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_questions = models.IntegerField(default=0)
    total_study_time = models.IntegerField(default=0, help_text="Total study time in minutes")
    current_streak = models.IntegerField(default=0, help_text="Current streak in days")
    longest_streak = models.IntegerField(default=0)
    total_quizzes = models.IntegerField(default=0)
    average_quiz_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    total_flashcards = models.IntegerField(default=0)
    favorite_course = models.CharField(max_length=100, blank=True)
    last_active = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.user.username}"


class DailyActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    questions_asked = models.IntegerField(default=0)
    study_minutes = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    flashcards_reviewed = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'daily activity'
        verbose_name_plural = 'daily activities'
        unique_together = ('user', 'date')
        indexes = [
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class TopicMastery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    mastery_level = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    questions_answered = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    last_practiced = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'course', 'topic')
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['mastery_level']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.course} - {self.topic}"
    
    @property
    def accuracy_rate(self):
        """Calculate accuracy rate as percentage"""
        if self.questions_answered == 0:
            return 0.0
        return (self.correct_answers / self.questions_answered) * 100


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.CharField(max_length=100, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    questions_asked = models.IntegerField(default=0)
    flashcards_reviewed = models.IntegerField(default=0)
    quizzes_taken = models.IntegerField(default=0)
    topics_covered = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.started_at}"


class Recommendation(models.Model):
    RECOMMENDATION_TYPES = [
        ('topic', 'Topic'),
        ('document', 'Document'),
        ('quiz', 'Quiz'),
        ('flashcard', 'Flashcard'),
        ('weak_area', 'Weak Area'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    related_course = models.CharField(max_length=100, blank=True)
    related_topic = models.CharField(max_length=100, blank=True)
    priority = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


# Study Assistant Models
class Quiz(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    title = models.CharField(max_length=200)
    course = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    source_document = models.ForeignKey(PDFDocument, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    time_limit = models.IntegerField(default=30, help_text="Time limit in minutes")
    
    def __str__(self):
        return f"{self.title} - {self.course}"


class QuizQuestion(models.Model):
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    options = models.JSONField(default=list, blank=True, help_text="List of options for MCQ")
    correct_answer = models.TextField()
    explanation = models.TextField(blank=True)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order + 1}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField(default=0.0)
    total_points = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.IntegerField(default=0, help_text="Time taken in seconds")
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}%"
    
    @property
    def percentage_score(self):
        """Calculate percentage score"""
        if self.total_points == 0:
            return 0.0
        return (self.score / self.total_points) * 100


class Flashcard(models.Model):
    CONFIDENCE_LEVELS = [
        (0, 'Not Learned'),
        (1, 'Learning'),
        (2, 'Comfortable'),
        (3, 'Mastered'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    front = models.TextField(help_text="Question or term")
    back = models.TextField(help_text="Answer or definition")
    source_document = models.ForeignKey(PDFDocument, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    confidence_level = models.IntegerField(choices=CONFIDENCE_LEVELS, default=0)
    review_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.front[:50]}"


# Search & Bookmark Models
class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField()
    filters_applied = models.JSONField(default=dict, blank=True)
    results_count = models.IntegerField(default=0)
    clicked_result = models.ForeignKey(QuestionAnswer, on_delete=models.SET_NULL, null=True, blank=True)
    searched_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.query[:50]}"


class SavedSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    query = models.TextField()
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    use_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'name')
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, max_length=50)
    color = models.CharField(max_length=7, default='#667eea', help_text="Hex color code")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    use_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question_answer = models.ForeignKey(QuestionAnswer, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    folder = models.ForeignKey('BookmarkFolder', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'question_answer')
        indexes = [
            models.Index(fields=['user', 'is_favorite']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title or self.question_answer.question[:50]}"


class BookmarkFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#667eea', help_text="Hex color code")
    icon = models.CharField(max_length=10, default='📁', help_text="Emoji icon")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'name')
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class ExportHistory(models.Model):
    EXPORT_TYPES = [
        ('chat', 'Chat'),
        ('bookmarks', 'Bookmarks'),
        ('analytics', 'Analytics'),
        ('flashcards', 'Flashcards'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('txt', 'TXT'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    filters_applied = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'export history'
        verbose_name_plural = 'export history'

    def __str__(self):
        return f"{self.user.username} - {self.export_type} - {self.format}"


class RecentSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.CharField(max_length=200)
    result_count = models.IntegerField(default=0)
    last_searched = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'query')
    
    def __str__(self):
        return f"{self.user.username} - {self.query}"
