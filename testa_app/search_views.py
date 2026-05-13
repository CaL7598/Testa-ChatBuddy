"""
Search and Bookmark Views for Testa studyBuddy
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
import json
import csv
from .models import (
    QuestionAnswer, Bookmark, BookmarkFolder, 
    SavedSearch, SearchHistory, Tag, ExportHistory
)
from .search_engine import AdvancedSearchEngine, QuickFilterEngine
from .forms import BookmarkForm, BookmarkFolderForm


# Advanced Search Views
@login_required
def advanced_search(request):
    """Advanced search interface"""
    query = request.GET.get('q', '')
    filters = {}
    sort_by = request.GET.get('sort', 'relevance')
    page = int(request.GET.get('page', 1))
    
    # Parse filters from GET parameters
    if request.GET.get('courses'):
        filters['courses'] = request.GET.getlist('courses')
    if request.GET.get('topics'):
        filters['topics'] = request.GET.getlist('topics')
    if request.GET.get('difficulty'):
        filters['difficulty'] = request.GET.getlist('difficulty')
    if request.GET.get('date_from'):
        filters['date_from'] = datetime.fromisoformat(request.GET.get('date_from'))
    if request.GET.get('date_to'):
        filters['date_to'] = datetime.fromisoformat(request.GET.get('date_to'))
    if request.GET.get('min_upvotes'):
        filters['min_upvotes'] = int(request.GET.get('min_upvotes'))
    if request.GET.get('my_content_only') == 'true':
        filters['my_content_only'] = True
    if request.GET.get('bookmarked_only') == 'true':
        filters['bookmarked_only'] = True
    if request.GET.get('tags'):
        filters['tags'] = request.GET.getlist('tags')
    
    # Perform search
    search_engine = AdvancedSearchEngine(user=request.user)
    results = search_engine.search(query, filters, sort_by, page, per_page=20)
    
    # Get available filter options
    available_courses = QuestionAnswer.objects.exclude(course='').values_list('course', flat=True).distinct()
    available_topics = QuestionAnswer.objects.exclude(topic='').values_list('topic', flat=True).distinct()
    available_tags = Tag.objects.all()
    
    # Get user's saved searches
    saved_searches = SavedSearch.objects.filter(user=request.user).order_by('-last_used')[:10]
    
    # Get recent searches
    recent_searches = SearchHistory.objects.filter(user=request.user).order_by('-searched_at')[:10]
    
    context = {
        'query': query,
        'results': results['results'],
        'total_count': results['total_count'],
        'page': results['page'],
        'total_pages': results['total_pages'],
        'filters': filters,
        'sort_by': sort_by,
        'available_courses': available_courses,
        'available_topics': available_topics,
        'available_tags': available_tags,
        'saved_searches': saved_searches,
        'recent_searches': recent_searches,
    }
    
    return render(request, 'testa_app/advanced_search.html', context)


@login_required
def search_suggestions(request):
    """AJAX endpoint for search suggestions"""
    query = request.GET.get('q', '')
    search_engine = AdvancedSearchEngine(user=request.user)
    suggestions = search_engine.get_suggestions(query, limit=10)
    return JsonResponse({'suggestions': suggestions})


@login_required
def save_search(request):
    """Save a search query"""
    if request.method == 'POST':
        name = request.POST.get('name')
        query = request.POST.get('query')
        filters_json = request.POST.get('filters', '{}')
        
        try:
            filters = json.loads(filters_json)
            SavedSearch.objects.create(
                user=request.user,
                name=name,
                query=query,
                filters=filters
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False}, status=400)


@login_required
def saved_searches(request):
    """View all saved searches"""
    saved_searches_list = SavedSearch.objects.filter(user=request.user).order_by('-last_used')
    return render(request, 'testa_app/saved_searches.html', {
        'saved_searches': saved_searches_list
    })


@login_required
def load_saved_search(request, search_id):
    """Load a saved search"""
    saved_search = get_object_or_404(SavedSearch, id=search_id, user=request.user)
    
    # Update use count
    saved_search.use_count += 1
    saved_search.last_used = timezone.now()
    saved_search.save()
    
    # Build URL with query and filters
    from django.urls import reverse
    url = reverse('advanced_search')
    params = {'q': saved_search.query}
    
    for key, value in saved_search.filters.items():
        if isinstance(value, list):
            for v in value:
                params[f'{key}'] = v
        else:
            params[key] = value
    
    query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
    return redirect(f'{url}?{query_string}')


@login_required
def search_history(request):
    """View search history"""
    history = SearchHistory.objects.filter(user=request.user).order_by('-searched_at')
    paginator = Paginator(history, 20)
    page = request.GET.get('page', 1)
    history_page = paginator.get_page(page)
    
    return render(request, 'testa_app/search_history.html', {
        'history': history_page
    })


@login_required
def clear_search_history(request):
    """Clear search history"""
    if request.method == 'POST':
        SearchHistory.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


# Bookmark Views
@login_required
def bookmarks(request):
    """View all bookmarks"""
    folder_id = request.GET.get('folder')
    sort_by = request.GET.get('sort', 'recent')
    view_mode = request.GET.get('view', 'list')
    
    bookmarks_list = Bookmark.objects.filter(user=request.user)
    
    if folder_id:
        bookmarks_list = bookmarks_list.filter(folder_id=folder_id)
    
    if sort_by == 'title':
        bookmarks_list = bookmarks_list.order_by('title')
    elif sort_by == 'favorites':
        bookmarks_list = bookmarks_list.order_by('-is_favorite', '-created_at')
    else:  # recent
        bookmarks_list = bookmarks_list.order_by('-created_at')
    
    # Get folders
    folders = BookmarkFolder.objects.filter(user=request.user)
    
    return render(request, 'testa_app/bookmarks.html', {
        'bookmarks': bookmarks_list,
        'folders': folders,
        'current_folder': folder_id,
        'sort_by': sort_by,
        'view_mode': view_mode,
    })


@login_required
def create_bookmark(request):
    """Create a new bookmark"""
    if request.method == 'POST':
        qa_id = request.POST.get('qa_id')
        question_answer = get_object_or_404(QuestionAnswer, id=qa_id)
        
        # Check if already bookmarked
        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            question_answer=question_answer,
            defaults={
                'title': question_answer.question[:100]
            }
        )
        
        if not created:
            return JsonResponse({'success': False, 'message': 'Already bookmarked'})
        
        # Update bookmark with form data if provided
        title = request.POST.get('title', '')
        notes = request.POST.get('notes', '')
        folder_id = request.POST.get('folder', '')
        tags_str = request.POST.get('tags', '')
        
        if title:
            bookmark.title = title
        if notes:
            bookmark.notes = notes
        if folder_id:
            bookmark.folder_id = folder_id
        if tags_str:
            bookmark.tags = [tag.strip() for tag in tags_str.split(',')]
        
        bookmark.save()
        
        return JsonResponse({'success': True, 'bookmark_id': bookmark.id})
    
    # GET request - show form
    qa_id = request.GET.get('qa_id')
    question_answer = get_object_or_404(QuestionAnswer, id=qa_id) if qa_id else None
    folders = BookmarkFolder.objects.filter(user=request.user)
    
    return render(request, 'testa_app/create_bookmark.html', {
        'question_answer': question_answer,
        'folders': folders,
    })


@login_required
def toggle_favorite(request, bookmark_id):
    """Toggle favorite status of bookmark"""
    if request.method == 'POST':
        bookmark = get_object_or_404(Bookmark, id=bookmark_id, user=request.user)
        bookmark.is_favorite = not bookmark.is_favorite
        bookmark.save()
        return JsonResponse({'success': True, 'is_favorite': bookmark.is_favorite})
    return JsonResponse({'success': False}, status=400)


@login_required
def delete_bookmark(request, bookmark_id):
    """Delete a bookmark"""
    if request.method == 'POST':
        bookmark = get_object_or_404(Bookmark, id=bookmark_id, user=request.user)
        bookmark.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required
def bookmark_folders(request):
    """Manage bookmark folders"""
    folders = BookmarkFolder.objects.filter(user=request.user)
    return render(request, 'testa_app/bookmark_folders.html', {
        'folders': folders
    })


@login_required
def create_bookmark_folder(request):
    """Create a new bookmark folder"""
    if request.method == 'POST':
        form = BookmarkFolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.user = request.user
            folder.save()
            return redirect('bookmark_folders')
    else:
        form = BookmarkFolderForm()
    
    return render(request, 'testa_app/create_bookmark_folder.html', {
        'form': form
    })


# Export Views
@login_required
def export_search_results(request):
    """Export search results"""
    export_format = request.GET.get('format', 'json')
    query = request.GET.get('q', '')
    filters = {}
    
    # Rebuild filters from GET params (similar to advanced_search)
    # ... (similar filter parsing as in advanced_search)
    
    search_engine = AdvancedSearchEngine(user=request.user)
    results = search_engine.search(query, filters, 'relevance', 1, per_page=1000)
    
    # Create export
    export = ExportHistory.objects.create(
        user=request.user,
        export_type='chat',
        format=export_format,
        filters_applied=filters
    )
    
    if export_format == 'json':
        return _export_json(results['results'])
    elif export_format == 'csv':
        return _export_csv(results['results'])
    elif export_format == 'txt':
        return _export_txt(results['results'])
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)


@login_required
def export_bookmarks(request):
    """Export bookmarks"""
    export_format = request.GET.get('format', 'json')
    folder_id = request.GET.get('folder')
    
    bookmarks_list = Bookmark.objects.filter(user=request.user)
    if folder_id:
        bookmarks_list = bookmarks_list.filter(folder_id=folder_id)
    
    export = ExportHistory.objects.create(
        user=request.user,
        export_type='bookmarks',
        format=export_format,
        filters_applied={'folder': folder_id} if folder_id else {}
    )
    
    if export_format == 'json':
        return _export_bookmarks_json(bookmarks_list)
    elif export_format == 'csv':
        return _export_bookmarks_csv(bookmarks_list)
    elif export_format == 'txt':
        return _export_bookmarks_txt(bookmarks_list)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)


# Export helper functions
def _export_json(results):
    """Export results as JSON"""
    data = [{
        'question': qa.question,
        'answer': qa.answer,
        'course': qa.course,
        'topic': qa.topic,
        'created_at': qa.created_at.isoformat(),
    } for qa in results]
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="search_results.json"'
    return response


def _export_csv(results):
    """Export results as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="search_results.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Question', 'Answer', 'Course', 'Topic', 'Created At'])
    
    for qa in results:
        writer.writerow([qa.question, qa.answer, qa.course, qa.topic, qa.created_at])
    
    return response


def _export_txt(results):
    """Export results as TXT"""
    content = "Search Results\n" + "=" * 50 + "\n\n"
    for idx, qa in enumerate(results, 1):
        content += f"{idx}. Question: {qa.question}\n"
        content += f"   Answer: {qa.answer}\n"
        content += f"   Course: {qa.course}, Topic: {qa.topic}\n"
        content += f"   Date: {qa.created_at}\n\n"
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="search_results.txt"'
    return response


def _export_bookmarks_json(bookmarks):
    """Export bookmarks as JSON"""
    data = [{
        'title': b.title,
        'question': b.question_answer.question,
        'answer': b.question_answer.answer,
        'notes': b.notes,
        'tags': b.tags,
        'folder': b.folder.name if b.folder else None,
        'created_at': b.created_at.isoformat(),
    } for b in bookmarks]
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="bookmarks.json"'
    return response


def _export_bookmarks_csv(bookmarks):
    """Export bookmarks as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookmarks.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Question', 'Answer', 'Notes', 'Tags', 'Folder', 'Created At'])
    
    for b in bookmarks:
        writer.writerow([
            b.title, b.question_answer.question, b.question_answer.answer,
            b.notes, ', '.join(b.tags), b.folder.name if b.folder else '',
            b.created_at
        ])
    
    return response


def _export_bookmarks_txt(bookmarks):
    """Export bookmarks as TXT"""
    content = "Bookmarks\n" + "=" * 50 + "\n\n"
    for idx, b in enumerate(bookmarks, 1):
        content += f"{idx}. {b.title}\n"
        content += f"   Question: {b.question_answer.question}\n"
        content += f"   Answer: {b.question_answer.answer}\n"
        if b.notes:
            content += f"   Notes: {b.notes}\n"
        if b.tags:
            content += f"   Tags: {', '.join(b.tags)}\n"
        if b.folder:
            content += f"   Folder: {b.folder.name}\n"
        content += f"   Date: {b.created_at}\n\n"
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="bookmarks.txt"'
    return response
