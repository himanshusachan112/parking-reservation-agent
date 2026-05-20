<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# ParkSmart Frontend

Next.js 16.2 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui (base-nova) + Zustand 5.

## Build and Run

```bash
npm install          # Install dependencies
npm run dev          # Dev server on port 3000 (requires backend on 8000)
npx next build       # Production build (catches TypeScript errors)
```

Backend must be running: `python -m uvicorn src.api.server:app --reload --port 8000` from project root.

## Structure

```
src/
  app/           # Next.js App Router pages (layout.tsx, page.tsx, chat/, admin/)
  components/    # UI components grouped by domain (chat/, admin/, shared/, providers/, ui/)
  store/         # Zustand stores (chatStore, adminStore, authStore, uiStore)
  services/      # API service wrappers (chatService, reservationService, adminService)
  lib/           # Utilities (api.ts, helpers.ts, validations.ts, utils.ts)
  hooks/         # Custom hooks (useAutoScroll, useMediaQuery)
  types/         # TypeScript interfaces (ChatMessage, Reservation, etc.)
```

## Critical Conventions

### shadcn/ui v4 Breaking Changes (from v3)
- `SheetTrigger` does **NOT** support `asChild` prop — use `onClick` handler instead
- `TooltipProvider` does **NOT** support `delayDuration` prop — omit it
- Zod v4 enums use `message` param, **NOT** `required_error`

### Zustand — Avoid Infinite Re-renders
**Never** call store methods that return new references inside selectors:
```tsx
// BAD — creates new array every render → infinite loop
const messages = useChatStore((s) => s.activeMessages());

// GOOD — select raw state, compute with useMemo
const sessions = useChatStore((s) => s.sessions);
const activeSessionId = useChatStore((s) => s.activeSessionId);
const messages = useMemo(
  () => sessions.find((s) => s.id === activeSessionId)?.messages || [],
  [sessions, activeSessionId]
);
```

### HTML Nesting
Never nest `<button>` inside `<button>` — use `<span role="button">` for inner interactive elements.

### Admin Auth
Admin portal is protected by `AdminLoginGate` component (`store/authStore.ts`). Demo credentials: `admin` / `admin123`. Auth state stored in `sessionStorage`.

## API Integration

- Base URL: `NEXT_PUBLIC_API_URL` from `.env.local` (default: `http://localhost:8000`)
- Chat: `POST /api/chat` → `{ message }` → `{ response, is_booking_flow, reservation_id }`
- Reservations: `GET/POST /api/reservations`
- Admin: `POST /admin/approve/{id}`, `POST /admin/reject/{id}`
- CORS configured for `localhost:3000` on the backend
