# ============================================
# ParkSmart Frontend - Production Dockerfile
# ============================================
# Multi-stage build: install → build → serve with standalone output.
# Uses Node Alpine for minimal image size.
# ============================================

# --------------- Stage 1: Dependencies ---------------
FROM node:20-alpine AS deps

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json* ./

# Install dependencies (frozen lockfile for reproducibility)
RUN npm ci --ignore-scripts

# --------------- Stage 2: Builder ---------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build argument for API URL (set at build time)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the Next.js application (standalone output)
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --------------- Stage 3: Runner ---------------
FROM node:20-alpine AS runner

WORKDIR /app

# Security: run as non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Switch to non-root user
USER nextjs

# Start the Next.js server
CMD ["node", "server.js"]
