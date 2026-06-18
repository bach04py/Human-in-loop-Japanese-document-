Frontend (Next.js + TailwindCSS) - Notes

This repo contains a placeholder for the frontend. Suggested steps to bootstrap:

1. Create a Next.js app inside `frontend`:

```bash
cd frontend
npx create-next-app@latest .
# then install Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

2. Add `axios` or `httpx` client to connect to the FastAPI backend.
3. Build pages:
 - Upload page for PDF/image upload
 - OCR viewer page showing detected boxes and text
 - Extraction editor to correct fields
 - Dashboard with analytics (Chart.js)

4. Development

```bash
cd frontend
npm run dev
```

