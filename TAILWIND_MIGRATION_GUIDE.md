# Tailwind CSS Migration Guide

## ✅ Base Template Updated

The `base.html` template has been updated to use Tailwind CSS instead of Bootstrap.

### What Changed:
- ✅ Replaced Bootstrap CDN with Tailwind CSS CDN
- ✅ Updated navigation with Tailwind classes
- ✅ Added custom Tailwind config for project colors
- ✅ Mobile-responsive menu with Tailwind
- ✅ Footer updated with Tailwind styling

### Tailwind Configuration:
The base template includes a custom Tailwind config with:
- **Primary Color**: `#667eea` (purple)
- **Secondary Color**: `#764ba2` (dark purple)
- **Accent Color**: `#f093fb` (pink)
- **Gradient Backgrounds**: Pre-configured for cards and sections

## 📋 Templates to Update (Optional)

The following templates still use Bootstrap classes. You can update them gradually:

1. **Analytics Dashboard** - Update cards, buttons, and charts container
2. **Quiz Templates** - Update forms and question cards
3. **Flashcard Templates** - Update card flip animations
4. **Search Templates** - Update filter panels and results
5. **Bookmark Templates** - Update card layouts
6. **Summary Templates** - Update content display

## 🎨 Common Tailwind Replacements

### Bootstrap → Tailwind:
- `.container` → `.max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- `.btn btn-primary` → `.bg-gradient-primary text-white px-4 py-2 rounded-lg hover:opacity-90`
- `.card` → `.bg-white rounded-lg shadow-md p-6`
- `.card-body` → `.p-6`
- `.card-header` → `.bg-gradient-primary text-white rounded-t-lg p-4`
- `.row` → `.flex flex-wrap -mx-4`
- `.col-md-6` → `.w-full md:w-1/2 px-4`
- `.btn-group` → `.inline-flex rounded-lg overflow-hidden`
- `.form-control` → `.w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent`
- `.badge badge-primary` → `.bg-primary text-white px-2 py-1 rounded-full text-xs`
- `.alert alert-info` → `.bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4`
- `.alert alert-success` → `.bg-green-100 border-l-4 border-green-500 text-green-700 p-4`
- `.alert alert-danger` → `.bg-red-100 border-l-4 border-red-500 text-red-700 p-4`
- `.text-center` → `.text-center` (same)
- `.mb-4` → `.mb-4` (same)
- `.mt-4` → `.mt-4` (same)

## 🔧 Custom Tailwind Classes Available

You can use these utility classes anywhere:
- `.bg-gradient-primary` - Purple gradient background
- `.bg-gradient-accent` - Pink gradient background
- `.bg-gradient-success` - Green gradient background
- `.text-primary` - Primary purple color
- `.text-secondary` - Secondary purple color

## 💡 Quick Start

To update a template:
1. Replace Bootstrap classes with Tailwind equivalents
2. Use the gradient utilities for cards and buttons
3. Maintain the same layout structure
4. Test responsiveness with Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`)

## 📝 Example: Converting a Card

**Bootstrap:**
```html
<div class="card">
    <div class="card-header">Title</div>
    <div class="card-body">Content</div>
</div>
```

**Tailwind:**
```html
<div class="bg-white rounded-lg shadow-md overflow-hidden">
    <div class="bg-gradient-primary text-white p-4">Title</div>
    <div class="p-6">Content</div>
</div>
```

## 🎯 Next Steps

1. Test the base template with Tailwind
2. Gradually update individual templates as needed
3. Customize Tailwind config if needed (edit `tailwind.config` in base.html)
4. Consider installing Tailwind CLI for production (optional)

---

**Note**: The current setup uses Tailwind CDN, which is perfect for development. For production, consider using Tailwind CLI for better performance and custom builds.
