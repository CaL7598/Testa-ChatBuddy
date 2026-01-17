# API Setup Guide for Testa ChatBuddy

## Required APIs

### 1. Bytez API (REQUIRED) ⚠️

The project uses **Bytez API** (free open-source models) for:
- AI-powered question answering
- Quiz generation
- Flashcard generation
- Study guide and summary generation

**Note:** Text embeddings use local sentence-transformers (no API needed)

#### How to Get Your API Key:

1. **Visit Bytez**
   - Go to: https://bytez.com
   - Sign up for a free account

2. **Get your API key**
   - Navigate to your account settings
   - Copy your Bytez API key

3. **Set up the API key in your project**

   **Option A: Using `.env` file (Recommended)**
   
   Create a `.env` file in the project root:
   ```env
   BYTEZ_API_KEY=your_bytez_api_key_here
   ```
   
   The project uses `python-dotenv` to load this automatically.

   **Option B: Environment Variable (Windows)**
   ```powershell
   $env:BYTEZ_API_KEY="your_bytez_api_key_here"
   ```

   **Option B: Environment Variable (Linux/Mac)**
   ```bash
   export BYTEZ_API_KEY="your_bytez_api_key_here"
   ```

#### API Usage & Limits:

- **Free Tier**: Bytez provides free access to open-source models
- **Rate Limits**: Check current limits at https://bytez.com
- **Models Used**:
  - `Qwen/Qwen2.5-7B-Instruct` - Default model for chat and content generation
  - Alternative models available: `Qwen/Qwen3-4B`, `Meta-Llama/Llama-3.1-8B-Instruct`

#### Cost Information:

- **FREE** - Bytez provides free access to open-source models
- No credit card required
- Perfect for educational use cases

---

## Optional APIs (Not Currently Used)

### Future Enhancements:

1. **Email Service API** (for password reset emails)
   - Could use: SendGrid, Mailgun, or AWS SES
   - Currently: Password reset functionality exists but may need email backend configuration

2. **File Storage API** (for production deployment)
   - Could use: AWS S3, Google Cloud Storage, or Azure Blob Storage
   - Currently: Files are stored locally

3. **Analytics API** (for advanced analytics)
   - Could use: Google Analytics, Mixpanel
   - Currently: Built-in analytics dashboard

---

## Current API Configuration

The API key is loaded in:
- `testa_app/bytez_client.py` - Bytez API client
- `testa_app/utils.py` - Main utility functions
- `testa_app/views.py` - View handlers

All use:
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("BYTEZ_API_KEY")
```

## Embeddings (No API Required)

Text embeddings use **sentence-transformers** library locally:
- Model: `all-MiniLM-L6-v2` (free, runs locally)
- No API calls needed
- Fast and efficient

---

## Testing Your API Key

After setting up your API key, test it by:

1. Starting the Django server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to the question/answer page
3. Try asking a question
4. If you see an error about API key, check:
   - `.env` file exists and has correct key
   - Environment variable is set correctly
   - API key is valid and not expired

---

## Security Best Practices

⚠️ **IMPORTANT**: Never commit your API key to Git!

- ✅ `.env` file is already in `.gitignore`
- ✅ Never share your API key publicly
- ✅ Rotate keys if accidentally exposed
- ✅ Use different keys for development and production

---

## Troubleshooting

### Error: "API key not found"
- Ensure `.env` file exists in project root
- Check that `BYTEZ_API_KEY` is spelled correctly
- Verify `python-dotenv` is installed: `pip install python-dotenv`

### Error: "Invalid API key"
- Verify the key is correct (no extra spaces)
- Check if the key is active in your Bytez account
- Ensure you have access to Bytez API

### Error: "Quota exceeded" or Rate Limiting
- Check your API usage in Bytez dashboard
- Wait for rate limit reset
- Consider using a different model if available

### Error: "sentence-transformers not installed"
- Install with: `pip install sentence-transformers`
- This is required for local embeddings (no API needed)

---

## Need Help?

- Bytez API Documentation: https://docs.bytez.com
- Bytez Chat Models: https://docs.bytez.com/http-reference/examples/open-source/chat/chat
- Sentence Transformers: https://www.sbert.net/
- Django Environment Variables: https://docs.djangoproject.com/en/stable/topics/settings/

## Model Selection

You can change the default model in `testa_app/bytez_client.py`:
- `Qwen/Qwen2.5-7B-Instruct` - Default (good balance)
- `Qwen/Qwen3-4B` - Faster, smaller
- `Meta-Llama/Llama-3.1-8B-Instruct` - Alternative option
- Check Bytez docs for latest available models
