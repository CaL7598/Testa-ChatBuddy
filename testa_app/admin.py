from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Bookmark,
    BookmarkFolder,
    DailyActivity,
    ExportHistory,
    Flashcard,
    PDFDocument,
    QuestionAnswer,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    RecentSearch,
    Recommendation,
    SavedSearch,
    SearchHistory,
    StudySession,
    Tag,
    TopicMastery,
    UserAnalytics,
    UserProfile,
    Vote,
)


# --- Custom admin site branding ---
admin.site.site_header = "Testa StudyBuddy"
admin.site.site_title = "Testa Admin"
admin.site.index_title = "Platform management"


def get_admin_dashboard_stats():
    """Used by admin index template tag (no request needed)."""
    return {
        "users": User.objects.count(),
        "questions": QuestionAnswer.objects.count(),
        "documents": PDFDocument.objects.count(),
        "quizzes": Quiz.objects.count(),
        "flashcards": Flashcard.objects.count(),
        "quiz_attempts": QuizAttempt.objects.count(),
    }


admin.site.index_template = "admin/custom_index.html"


class TestaModelAdmin(admin.ModelAdmin):
    """Safer defaults for production Postgres + Render."""

    list_per_page = 25
    show_full_result_count = False


def _patch_admin_each_context():
    """Inject dashboard stats on index only; avoid broken bound-method monkey-patches."""
    if getattr(admin.site, "_testa_each_context_patched", False):
        return

    def each_context_with_stats(request):
        context = AdminSite.each_context(admin.site, request)
        path = request.path.rstrip("/")
        if path == "/admin":
            try:
                context["admin_stats"] = get_admin_dashboard_stats()
            except Exception:
                context["admin_stats"] = {}
        return context

    admin.site.each_context = each_context_with_stats
    admin.site._testa_each_context_patched = True


_patch_admin_each_context()


# --- Inlines ---
class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    fields = ("order", "question_type", "question_text", "correct_answer", "points")
    ordering = ("order",)


# --- Model admins ---
@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(TestaModelAdmin):
    list_display = (
        "id",
        "user",
        "question_preview",
        "course",
        "topic",
        "votes_display",
        "created_at",
        "is_archived",
    )
    list_filter = ("is_archived", "difficulty_detected", "course", "created_at")
    search_fields = ("question", "answer", "user__username", "course", "topic")
    readonly_fields = ("created_at", "response_time")
    raw_id_fields = ("user", "source_document")
    filter_horizontal = ("tags",)

    @admin.display(description="Question")
    def question_preview(self, obj):
        if not obj or not obj.question:
            return "—"
        text = obj.question[:80] + ("…" if len(obj.question) > 80 else "")
        return text

    @admin.display(description="Votes")
    def votes_display(self, obj):
        if not obj:
            return "—"
        return format_html(
            '<span style="color:#16a34a">↑{}</span> <span style="color:#dc2626">↓{}</span>',
            obj.upvotes or 0,
            obj.downvotes or 0,
        )


@admin.register(PDFDocument)
class PDFDocumentAdmin(TestaModelAdmin):
    list_display = ("id", "title", "course", "difficulty_level", "uploaded_by", "uploaded_at")
    list_filter = ("difficulty_level", "course", "uploaded_at")
    search_fields = ("title", "file", "course", "uploaded_by__username")
    readonly_fields = ("uploaded_at",)
    raw_id_fields = ("uploaded_by",)


@admin.register(UserAnalytics)
class UserAnalyticsAdmin(TestaModelAdmin):
    list_display = (
        "user",
        "total_questions",
        "total_study_time",
        "current_streak",
        "total_quizzes",
        "average_quiz_score",
        "last_active",
    )
    search_fields = ("user__username", "favorite_course")
    readonly_fields = ("last_active",)
    raw_id_fields = ("user",)


@admin.register(DailyActivity)
class DailyActivityAdmin(TestaModelAdmin):
    list_display = ("user", "date", "questions_asked", "study_minutes", "quizzes_completed")
    list_filter = ("date",)
    search_fields = ("user__username",)
    raw_id_fields = ("user",)


@admin.register(TopicMastery)
class TopicMasteryAdmin(TestaModelAdmin):
    list_display = ("user", "course", "topic", "mastery_level", "questions_answered", "last_practiced")
    list_filter = ("course",)
    search_fields = ("user__username", "course", "topic")
    raw_id_fields = ("user",)


@admin.register(StudySession)
class StudySessionAdmin(TestaModelAdmin):
    list_display = ("user", "course", "started_at", "duration", "questions_asked")
    list_filter = ("course", "started_at")
    search_fields = ("user__username", "course")
    raw_id_fields = ("user",)


@admin.register(Recommendation)
class RecommendationAdmin(TestaModelAdmin):
    list_display = ("title", "user", "recommendation_type", "priority", "is_completed", "created_at")
    list_filter = ("recommendation_type", "is_completed", "priority")
    search_fields = ("title", "user__username", "related_course", "related_topic")
    raw_id_fields = ("user",)


@admin.register(Quiz)
class QuizAdmin(TestaModelAdmin):
    list_display = ("title", "course", "topic", "difficulty", "created_by", "created_at")
    list_filter = ("difficulty", "course")
    search_fields = ("title", "course", "topic", "created_by__username")
    inlines = [QuizQuestionInline]
    raw_id_fields = ("created_by", "source_document")


@admin.register(QuizQuestion)
class QuizQuestionAdmin(TestaModelAdmin):
    list_display = ("quiz", "order", "question_type", "question_preview", "points")
    list_filter = ("question_type",)
    search_fields = ("question_text", "quiz__title")
    raw_id_fields = ("quiz",)

    @admin.display(description="Question")
    def question_preview(self, obj):
        return obj.question_text[:60] + ("…" if len(obj.question_text) > 60 else "")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(TestaModelAdmin):
    list_display = ("user", "quiz", "score", "total_points", "started_at", "completed_at")
    list_filter = ("started_at",)
    search_fields = ("user__username", "quiz__title")
    raw_id_fields = ("user", "quiz")


@admin.register(Flashcard)
class FlashcardAdmin(TestaModelAdmin):
    list_display = ("user", "course", "topic", "front_preview", "confidence_level", "review_count")
    list_filter = ("confidence_level", "course")
    search_fields = ("front", "back", "user__username", "course", "topic")
    raw_id_fields = ("user", "source_document")

    @admin.display(description="Front")
    def front_preview(self, obj):
        return obj.front[:50] + ("…" if len(obj.front) > 50 else "")


@admin.register(Vote)
class VoteAdmin(TestaModelAdmin):
    list_display = ("user", "question_answer", "vote_type", "created_at")
    list_filter = ("vote_type",)
    raw_id_fields = ("user", "question_answer")


@admin.register(Tag)
class TagAdmin(TestaModelAdmin):
    list_display = ("name", "slug", "color_display", "use_count", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Color")
    def color_display(self, obj):
        return format_html(
            '<span style="display:inline-block;width:14px;height:14px;border-radius:4px;'
            'background:{};vertical-align:middle;margin-right:6px"></span> {}',
            obj.color,
            obj.color,
        )


@admin.register(Bookmark)
class BookmarkAdmin(TestaModelAdmin):
    list_display = ("user", "title", "is_favorite", "folder", "created_at")
    list_filter = ("is_favorite",)
    search_fields = ("title", "user__username", "notes")
    raw_id_fields = ("user", "question_answer", "folder")


@admin.register(BookmarkFolder)
class BookmarkFolderAdmin(TestaModelAdmin):
    list_display = ("name", "user", "icon", "parent", "created_at")
    search_fields = ("name", "user__username")
    raw_id_fields = ("user", "parent")


@admin.register(SearchHistory)
class SearchHistoryAdmin(TestaModelAdmin):
    list_display = ("user", "query_preview", "results_count", "searched_at")
    search_fields = ("query", "user__username")
    raw_id_fields = ("user", "clicked_result")

    @admin.display(description="Query")
    def query_preview(self, obj):
        return obj.query[:60] + ("…" if len(obj.query) > 60 else "")


@admin.register(SavedSearch)
class SavedSearchAdmin(TestaModelAdmin):
    list_display = ("name", "user", "use_count", "last_used")
    search_fields = ("name", "query", "user__username")
    raw_id_fields = ("user",)


@admin.register(RecentSearch)
class RecentSearchAdmin(TestaModelAdmin):
    list_display = ("user", "query", "result_count", "last_searched")
    search_fields = ("query", "user__username")
    raw_id_fields = ("user",)


@admin.register(ExportHistory)
class ExportHistoryAdmin(TestaModelAdmin):
    list_display = ("user", "export_type", "format", "created_at")
    list_filter = ("export_type", "format")
    raw_id_fields = ("user",)


# --- Auth user: slightly nicer list ---
admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ('email_verified', 'email_verified_at')


@admin.register(UserProfile)
class UserProfileAdmin(TestaModelAdmin):
    list_display = ('user', 'email_verified', 'email_verified_at')
    list_filter = ('email_verified',)
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "date_joined", "qa_count")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_qa_count=Count('questionanswer'))

    @admin.display(description="Q&A count")
    def qa_count(self, obj):
        return getattr(obj, '_qa_count', 0)
