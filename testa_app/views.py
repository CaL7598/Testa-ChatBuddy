import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from .forms import UserRegisterForm, PDFUploadForm
from .models import PDFDocument, QuestionAnswer, UserAnalytics, DailyActivity
from .utils import (
    get_file_text, get_text_chunks, get_vector_store, 
    load_vector_store, get_conversational_chain
)
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from datetime import datetime, date
from django.utils import timezone
from .bytez_client import BytezClient

load_dotenv()




import requests
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import PDFDocument, QuestionAnswer




import requests
from bs4 import BeautifulSoup
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import PDFDocument, QuestionAnswer
import requests
from bs4 import BeautifulSoup

def web_scrape_search(query):
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    snippet = None
    try:
        snippet = soup.find("span", {"class": "aCOpRe"})
        if snippet:
            return snippet.text
        else:
            snippet = soup.find("div", {"class": "BNeawe s3v9rd AP7Wnd"})
            if snippet:
                return snippet.text
    except AttributeError:
        pass

    return "Sorry, I couldn't find an answer to your question."




@login_required
def question_answer(request):
    start_time = timezone.now()
    
    if request.method == 'POST':
        try:
            user_question = request.POST.get('question')
            if not user_question:
                return JsonResponse({"error": "Question is required"}, status=400)
            
            print("Received question:", user_question)
            qa_list = QuestionAnswer.objects.filter(user=request.user).order_by('-created_at')[:10]
            
            # Load vector store and search
            answer = None
            try:
                vector_store = load_vector_store("faiss_index")
                if vector_store:
                    docs = vector_store.similarity_search(user_question, k=3)
                    # Combine context from similar documents
                    context = "\n\n".join([doc.page_content for doc in docs])
                    chain = get_conversational_chain()
                    answer = chain(context, user_question)
            except Exception as e:
                print(f"Error with vector store: {e}")
            
            # If no answer from vector store, try direct AI question
            if not answer:
                try:
                    from .bytez_client import BytezClient
                    client = BytezClient()
                    answer = client.answer_question(user_question)
                except ValueError as e2:
                    # API key missing
                    print(f"API Key Error: {e2}")
                    answer = "API configuration error. Please contact support."
                except Exception as e2:
                    print(f"Error with Bytez API: {e2}")
                    import traceback
                    traceback.print_exc()
                    # Try web scrape as fallback
                    try:
                        answer = web_scrape_search(user_question)
                        if not answer or "Sorry" in answer:
                            # Provide helpful error message
                            error_msg = str(e2)
                            if "timeout" in error_msg.lower():
                                answer = "The AI service is taking too long to respond. This might be due to high traffic. Please try again in a moment."
                            elif "connection" in error_msg.lower():
                                answer = "Unable to connect to the AI service. Please check your internet connection and try again."
                            elif "401" in error_msg or "403" in error_msg:
                                answer = "Authentication error with the AI service. Please contact support."
                            else:
                                answer = f"I'm having trouble connecting to the AI service right now. Error: {error_msg[:100]}. Please try again later or contact support if the issue persists."
                    except Exception as e3:
                        print(f"Web scrape also failed: {e3}")
                        answer = "I'm unable to process your question right now. The AI service and fallback options are unavailable. Please try again later."
            
            if answer == "The answer is not available in the context.":
                answer = web_scrape_search(user_question)
                if not answer:
                    answer = "Sorry, I couldn't find an answer to your question."
            
            # Calculate response time
            response_time = (timezone.now() - start_time).total_seconds()
            print("Response:", answer[:100] if answer else "Empty response")
            
            # Create Q&A entry
            qa_entry = QuestionAnswer.objects.create(
                user=request.user,
                question=user_question,
                answer=answer,
                response_time=response_time
            )
            
            # Update analytics
            try:
                _update_daily_activity(request.user)
                _update_user_analytics(request.user)
            except Exception as e:
                print(f"Error updating analytics: {e}")
            
            return JsonResponse({"response": answer})
            
        except Exception as e:
            print(f"Unexpected error in question_answer: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                "error": f"An error occurred: {str(e)}"
            }, status=500)

    qa_list = QuestionAnswer.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'testa_app/question_answer.html', {
        'qa_list': qa_list,
        'username': request.user.username 
    })


def _update_daily_activity(user):
    """Update daily activity for user"""
    today = date.today()
    activity, created = DailyActivity.objects.get_or_create(
        user=user,
        date=today,
        defaults={'questions_asked': 0}
    )
    activity.questions_asked += 1
    activity.save()


def _update_user_analytics(user):
    """Update user analytics"""
    analytics, created = UserAnalytics.objects.get_or_create(user=user)
    analytics.total_questions += 1
    analytics.last_active = timezone.now()
    analytics.save()



@login_required
def all_questions(request):
    all_qa_list = QuestionAnswer.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'testa_app/all_questions.html', {
        'all_qa_list': all_qa_list,
    })


from docx import Document
from pptx import Presentation
import os

def get_file_text(file):
    extension = file.name.split('.')[-1].lower()
    
    if extension == 'pdf':
        return extract_text_from_pdf(file)
    elif extension == 'docx':
        return extract_text_from_docx(file)
    elif extension == 'pptx':
        return extract_text_from_pptx(file)
    elif extension == 'txt':
        return extract_text_from_txt(file)
    elif extension == 'ppt':
        return extract_text_from_txt(file)
    else:
        raise ValueError('Unsupported file type')

def extract_text_from_pdf(file):
    text = ""
    pdf_reader = PdfReader(file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

def extract_text_from_pptx(file):
    presentation = Presentation(file)
    text = ""
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text
    return text

def extract_text_from_txt(file):
    return file.read().decode('utf-8')



@login_required
def pdf_upload(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_doc = form.save(commit=False)
            pdf_doc.uploaded_by = request.user
            if not pdf_doc.title:
                pdf_doc.title = request.FILES['file'].name
            pdf_doc.save()
            
            file = request.FILES['file']
            raw_text = get_file_text(file)
            text_chunks = get_text_chunks(raw_text)
            get_vector_store(text_chunks)
            return redirect('pdf_upload')
    else:
        form = PDFUploadForm()
    return render(request, 'testa_app/pdf_upload.html', {'form': form})





def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('question_answer')
    else:
        form = UserRegisterForm()
    return render(request, 'testa_app/register.html', {'form': form})




def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('question_answer')
    else:
        form = AuthenticationForm()
    return render(request, 'testa_app/login.html', {'form': form})



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import QuestionAnswer, Vote
import json
from django.views.decorators.http import require_http_methods

@require_http_methods(["PATCH"])
@login_required
def vote(request):
    try:
        data = json.loads(request.body)
        qa_id = data.get('qa_id')
        action = data.get('action')
        question_answer = QuestionAnswer.objects.get(id=qa_id)
        vote, created = Vote.objects.get_or_create(
            user=request.user, 
            question_answer=question_answer,
            defaults={'vote_type': action}
        )

        if not created: 
            if vote.vote_type == action:
                return JsonResponse({'error': 'You have already voted this way'}, status=400)
            else:
                vote.vote_type = action
                vote.save()

               
                if action == 'upvote':
                    question_answer.upvotes += 1
                    question_answer.downvotes -= 1
                else:
                    question_answer.upvotes -= 1
                    question_answer.downvotes += 1

        else:
            if action == 'upvote':
                question_answer.upvotes += 1
            elif action == 'downvote':
                question_answer.downvotes += 1

        question_answer.save()

        return JsonResponse({
            'upvotes': question_answer.upvotes,
            'downvotes': question_answer.downvotes
        })

    except QuestionAnswer.DoesNotExist:
        return JsonResponse({'error': 'QuestionAnswer not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings

User = get_user_model()

def forgot_password_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            associated_users = User.objects.filter(email=email)
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': request.META['HTTP_HOST'],
                        'site_name': 'Your Site',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    send_mail(subject, email, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()
    return render(request, 'forgot_password.html', {'form': form})

def about(request):
    return render(request, 'about.html')
from django.contrib.auth import logout




from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('login')



def index(request):
    return render(request, 'index.html')


@login_required
def recommendations(request):
    """Smart recommendations view"""
    from .recommendation_engine import RecommendationEngine
    
    # Generate recommendations
    engine = RecommendationEngine(request.user)
    recommendations_list = engine.generate_recommendations(limit=20)
    
    # Get daily focus (highest priority)
    daily_focus = engine.get_daily_focus()
    
    # Filter by type if requested
    rec_type = request.GET.get('type', '')
    if rec_type:
        recommendations_list = [r for r in recommendations_list if r.recommendation_type == rec_type]
    
    return render(request, 'testa_app/recommendations.html', {
        'recommendations': recommendations_list,
        'daily_focus': daily_focus,
        'filter_type': rec_type,
    })


@login_required
def complete_recommendation(request, rec_id):
    """Mark recommendation as complete"""
    if request.method == 'POST':
        from .models import Recommendation
        recommendation = get_object_or_404(Recommendation, id=rec_id, user=request.user)
        recommendation.is_completed = True
        recommendation.completed_at = timezone.now()
        recommendation.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

