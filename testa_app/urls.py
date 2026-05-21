from django.urls import path
from . import views
from . import analytics_views
from . import study_assistant_views
from . import search_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('password-reset/', views.forgot_password_view, name='password_reset'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='forgot_password.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    
    # Core Features
    path('health/', views.health, name='health'),
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('pdf_upload/', views.pdf_upload, name='pdf_upload'),
    path('question_answer/upload/', views.upload_document_ajax, name='upload_document_ajax'),
    path('question_answer/', views.question_answer, name='question_answer'),
    path('vote/', views.vote, name='vote'),
    path('question_answer/delete/<int:qa_id>/', views.delete_question_answer, name='delete_question_answer'),
    path('question_answer/delete-all/', views.delete_all_question_answers, name='delete_all_question_answers'),
    path('all-questions/', views.all_questions, name='all_questions'),
    
    # Analytics
    path('analytics/', analytics_views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/chart-data/', analytics_views.analytics_chart_data, name='analytics_chart_data'),
    
    # Study Assistant - Quiz
    path('quiz/generate/', study_assistant_views.generate_quiz, name='generate_quiz'),
    path('quiz/<int:quiz_id>/take/', study_assistant_views.take_quiz, name='take_quiz'),
    path('quiz/results/<int:attempt_id>/', study_assistant_views.quiz_results, name='quiz_results'),
    
    # Study Assistant - Flashcards
    path('flashcards/generate/', study_assistant_views.generate_flashcards, name='generate_flashcards'),
    path('flashcards/study/', study_assistant_views.study_flashcards, name='study_flashcards'),
    path('flashcards/<int:flashcard_id>/update-confidence/', study_assistant_views.update_flashcard_confidence, name='update_flashcard_confidence'),
    
    # Study Assistant - Summary
    path('summary/generate/', study_assistant_views.generate_summary, name='generate_summary'),
    path('study-guide/<int:doc_id>/', study_assistant_views.generate_study_guide, name='generate_study_guide'),
    
    # Search
    path('search/', search_views.advanced_search, name='advanced_search'),
    path('search/suggestions/', search_views.search_suggestions, name='search_suggestions'),
    path('search/save/', search_views.save_search, name='save_search'),
    path('search/saved/', search_views.saved_searches, name='saved_searches'),
    path('search/saved/<int:search_id>/load/', search_views.load_saved_search, name='load_saved_search'),
    path('search/history/', search_views.search_history, name='search_history'),
    path('search/history/clear/', search_views.clear_search_history, name='clear_search_history'),
    path('search/export/', search_views.export_search_results, name='export_search_results'),
    
    # Bookmarks
    path('bookmarks/', search_views.bookmarks, name='bookmarks'),
    path('bookmarks/create/', search_views.create_bookmark, name='create_bookmark'),
    path('bookmarks/<int:bookmark_id>/favorite/', search_views.toggle_favorite, name='toggle_favorite'),
    path('bookmarks/<int:bookmark_id>/delete/', search_views.delete_bookmark, name='delete_bookmark'),
    path('bookmarks/folders/', search_views.bookmark_folders, name='bookmark_folders'),
    path('bookmarks/folders/create/', search_views.create_bookmark_folder, name='create_bookmark_folder'),
    path('bookmarks/export/', search_views.export_bookmarks, name='export_bookmarks'),
    
    # Recommendations
    path('recommendations/', views.recommendations, name='recommendations'),
    path('recommendations/<int:rec_id>/complete/', views.complete_recommendation, name='complete_recommendation'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
]
