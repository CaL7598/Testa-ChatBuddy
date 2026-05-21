"""
Advanced Search Engine for Testa studyBuddy
"""
from django.db.models import Q, Count
from django.core.cache import cache
from .models import QuestionAnswer, SearchHistory, RecentSearch
from datetime import datetime, timedelta


class AdvancedSearchEngine:
    """Advanced search functionality with filtering and ranking"""
    
    def __init__(self, user=None):
        self.user = user
    
    def search(self, query, filters=None, sort_by='relevance', page=1, per_page=20):
        """
        Perform advanced search with filters and sorting
        
        Args:
            query: Search query string
            filters: Dictionary of filter parameters
            sort_by: Sort option (relevance, newest, oldest, popular, rated)
            page: Page number
            per_page: Results per page
        """
        # Build cache key
        cache_key = f"search_{hash(query)}_{hash(str(filters))}_{sort_by}_{page}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Start with base queryset
        queryset = QuestionAnswer.objects.filter(is_archived=False)
        
        # Apply search query
        if query:
            queryset = queryset.filter(
                Q(question__icontains=query) |
                Q(answer__icontains=query) |
                Q(course__icontains=query) |
                Q(topic__icontains=query)
            )
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Sort results
        queryset = self._sort_results(queryset, sort_by, query)
        
        # Calculate total count
        total_count = queryset.count()
        
        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        results = queryset[start:end]
        
        # Save search history
        if self.user:
            self._save_search_history(query, filters, total_count)
        
        result_data = {
            'results': results,
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result_data, 300)
        
        return result_data
    
    def _apply_filters(self, queryset, filters):
        """Apply advanced filters to queryset"""
        # Filter by course
        if filters.get('courses'):
            queryset = queryset.filter(course__in=filters['courses'])
        
        # Filter by topic
        if filters.get('topics'):
            queryset = queryset.filter(topic__in=filters['topics'])
        
        # Filter by difficulty
        if filters.get('difficulty'):
            queryset = queryset.filter(difficulty_detected__in=filters['difficulty'])
        
        # Filter by date range
        if filters.get('date_from'):
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        if filters.get('date_to'):
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        # Filter by vote threshold
        if filters.get('min_upvotes'):
            queryset = queryset.filter(upvotes__gte=filters['min_upvotes'])
        
        # Filter by user (my content only)
        if filters.get('my_content_only') and self.user:
            queryset = queryset.filter(user=self.user)
        
        # Filter by bookmarked
        if filters.get('bookmarked_only') and self.user:
            from .models import Bookmark
            bookmarked_ids = Bookmark.objects.filter(user=self.user).values_list('question_answer_id', flat=True)
            queryset = queryset.filter(id__in=bookmarked_ids)
        
        # Filter by tags
        if filters.get('tags'):
            queryset = queryset.filter(tags__name__in=filters['tags']).distinct()
        
        return queryset
    
    def _sort_results(self, queryset, sort_by, query=None):
        """Sort results based on sort option"""
        if sort_by == 'newest':
            return queryset.order_by('-created_at')
        elif sort_by == 'oldest':
            return queryset.order_by('created_at')
        elif sort_by == 'popular':
            return queryset.order_by('-upvotes')
        elif sort_by == 'rated':
            # Sort by upvote ratio
            return queryset.annotate(
                vote_ratio=Count('upvotes') / (Count('upvotes') + Count('downvotes'))
            ).order_by('-vote_ratio')
        else:  # relevance (default)
            # Prioritize question matches, then recency
            if query:
                from django.db import connection
                # PostgreSQL LIKE is case-sensitive; ILIKE matches SQLite-style search better
                like_op = 'ILIKE' if connection.vendor == 'postgresql' else 'LIKE'
                pattern = f'%{query}%'
                return queryset.extra(
                    select={
                        'relevance': f"""
                            CASE
                                WHEN question {like_op} %s THEN 3
                                WHEN answer {like_op} %s THEN 2
                                WHEN topic {like_op} %s THEN 1
                                ELSE 0
                            END
                        """
                    },
                    select_params=[pattern, pattern, pattern],
                ).order_by('-relevance', '-created_at')
            return queryset.order_by('-created_at')
    
    def _save_search_history(self, query, filters, result_count):
        """Save search to history"""
        SearchHistory.objects.create(
            user=self.user,
            query=query,
            filters_applied=filters or {},
            results_count=result_count
        )
        
        # Update recent searches
        recent_search, created = RecentSearch.objects.get_or_create(
            user=self.user,
            query=query,
            defaults={'result_count': result_count}
        )
        if not created:
            recent_search.result_count = result_count
            recent_search.save()
    
    def get_suggestions(self, partial_query, limit=10):
        """Get auto-complete suggestions"""
        if not partial_query:
            return []
        
        # Get from user's search history
        if self.user:
            suggestions = RecentSearch.objects.filter(
                user=self.user,
                query__icontains=partial_query
            ).order_by('-last_searched')[:limit]
            return [s.query for s in suggestions]
        
        # Get popular topics
        suggestions = QuestionAnswer.objects.filter(
            topic__icontains=partial_query
        ).values('topic').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        return [s['topic'] for s in suggestions if s['topic']]


class QuickFilterEngine:
    """Quick filter presets"""
    
    @staticmethod
    def get_today_filter():
        """Get filter for today's questions"""
        today = datetime.now().date()
        return {
            'date_from': datetime.combine(today, datetime.min.time()),
            'date_to': datetime.combine(today, datetime.max.time())
        }
    
    @staticmethod
    def get_this_week_filter():
        """Get filter for this week's questions"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        return {
            'date_from': datetime.combine(week_ago, datetime.min.time()),
            'date_to': datetime.combine(today, datetime.max.time())
        }
    
    @staticmethod
    def get_this_month_filter():
        """Get filter for this month's questions"""
        today = datetime.now().date()
        month_ago = today - timedelta(days=30)
        return {
            'date_from': datetime.combine(month_ago, datetime.min.time()),
            'date_to': datetime.combine(today, datetime.max.time())
        }
