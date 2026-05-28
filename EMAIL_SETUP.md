# Email setup (SendGrid / Twilio)

Testa StudyBuddy sends:

- **Welcome + verify** email on registration
- **Password reset** emails (forgot password flow)
- **Resend verification** for unverified accounts

## 1. SendGrid configuration

1. Log in to [SendGrid](https://app.sendgrid.com/).
2. **Settings → API Keys** → Create API key with **Mail Send** permission.
3. **Settings → Sender Authentication** → verify a **Single Sender** or your domain.
4. Use that verified address as `DEFAULT_FROM_EMAIL`.

## 2. Environment variables

Add to `.env` (never commit real keys):

```env
SENDGRID_API_KEY=SG.your_key_here
DEFAULT_FROM_EMAIL=adubeasarah44@gmail.com
SITE_NAME=Testa StudyBuddy
SITE_URL=https://testa-chatbuddy.onrender.com
SUPPORT_EMAIL=adubeasarah44@gmail.com
```

For local development:

```env
SITE_URL=http://127.0.0.1:8000
```

Without `SENDGRID_API_KEY`, emails print to the **console** (runserver terminal).

## 3. Render

In the Render dashboard, add the same variables under **Environment**. Redeploy after saving.

## 4. Security

- Rotate any API key that was shared in chat or committed by mistake.
- SendGrid keys start with `SG.` — treat them like passwords.

## 5. Test checklist

1. Register a new user → welcome email with **Verify my email** button.
2. Click verify link → banner disappears after login.
3. **Forgot password** → reset email with styled link.
4. Open reset link → set new password → sign in.
